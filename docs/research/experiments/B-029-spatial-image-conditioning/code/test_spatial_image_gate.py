# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
# Run with pinned Python, CUDA_VISIBLE_DEVICES='', SCAIL_MODEL_SOURCE=<pinned file>.
"""Six CPU contracts; CPU attention fixture does not certify FA2 or 14B parity."""
from pathlib import Path
from types import SimpleNamespace
import ast
import hashlib
import json
import os
import tempfile
from safetensors.torch import save_file
import torch
from torch import nn
import spatial_image_gate as gate
from build_support_maps import support_map


def official_fixture():
    path = Path(os.environ['SCAIL_MODEL_SOURCE'])
    source = path.read_text()
    assert hashlib.sha256(path.read_bytes()).hexdigest() == gate.SOURCE_SHA256
    tree = ast.parse(source)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'WanI2VCrossAttention')
    fn = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'forward')
    module = ast.Module(body=[fn], type_ignores=[])
    def attention(q, k, v, k_lens=None):
        assert k_lens is None
        return torch.einsum('bhqk,bkhd->bqhd', (torch.einsum('bqhd,bkhd->bhqk', q, k) / q.shape[-1]**.5).softmax(-1), v)
    namespace = {'flash_attention': attention, 'T5_CONTEXT_TOKEN_NUMBER': 2}
    exec(compile(module, str(path), 'exec'), namespace)
    layer = SimpleNamespace(num_heads=2, head_dim=2)
    for name in ('q', 'k', 'v', 'k_img', 'v_img', 'o'):
        setattr(layer, name, nn.Linear(4, 4))
    layer.norm_q = layer.norm_k = layer.norm_k_img = nn.Identity()
    return namespace['forward'], layer


def test_off_and_zero_preserve_official_path():
    # Given: exact official function and a deterministic tiny numerical fixture.
    torch.manual_seed(71)
    original, layer = official_fixture()
    x, context = torch.randn(1, 8, 4), torch.randn(1, 5, 4)
    # When: image output receives an identity gate.
    patched = gate.compile_forward(original, lambda image: image)
    # Then: the entire output is exactly preserved; zero-strength gate is identity.
    assert torch.equal(original(layer, x, context, None), patched(layer, x, context, None))
    assert torch.equal(gate.coefficients(torch.rand(1, 2, 2), gate.GateMode.METHOD, 0), torch.ones(1, 2, 2))
    class TinyBlock(nn.Module):
        def __init__(self):
            super().__init__()
            self.cross_attn = type('WanI2VCrossAttention', (nn.Module,), {'forward':original})()
            for name, value in vars(layer).items(): setattr(self.cross_attn, name, value)
        def forward(self, hidden, **kwargs):
            return self.cross_attn(hidden, context, None)
    model = nn.Module(); model.blocks = nn.ModuleList([TinyBlock() for _ in range(40)])
    before = [block.cross_attn.forward.__func__ for block in model.blocks]
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)/'support.safetensors'
        save_file({'E':torch.tensor([[[1.,0.],[0.,1.]]])},str(path))
        disabled = gate.install(model,path,gate.GateConfig(gate.GateMode.OFF))
        zero = gate.install(model,path,gate.GateConfig(gate.GateMode.METHOD,0))
        assert [block.cross_attn.forward.__func__ for block in model.blocks] == before
        disabled.remove(); zero.remove()
        active = gate.install(model,path,gate.GateConfig(gate.GateMode.METHOD))
        kwargs = {'grid_sizes':torch.tensor([[1,2,2]]),'ref_length':2,'additional_ref_length':0,'seq_length':4,'pose_length':2}
        for block in model.blocks: block(x,**kwargs)
        active.assert_complete(expected_calls=1,expected_blocks=40)
        active.remove()
        assert [block.cross_attn.forward.__func__ for block in model.blocks] == before


def test_only_generated_range_changes():
    # Given: explicit nonzero prefix and suffix around generated queries.
    image = torch.arange(32, dtype=torch.float32).reshape(1, 8, 4)
    layout = gate.TokenLayout(2, 4, 2, (1, 2, 2))
    weights = torch.tensor([[[.8, 1.2], [.9, 1.1]]])
    # When: the image feature is gated.
    result = gate.apply_generated(image, weights, layout)
    # Then: ref/driving are exact, generated differs, and input remains exact.
    assert torch.equal(result[:, :2], image[:, :2]) and torch.equal(result[:, 6:], image[:, 6:])
    assert not torch.equal(result[:, 2:6], image[:, 2:6])
    assert torch.equal(image, torch.arange(32, dtype=torch.float32).reshape(1, 8, 4))


def test_text_and_projection_bias_are_not_scaled():
    # Given: distinct text, image, projection and bias values.
    text = torch.full((1, 4, 2), 3.0)
    image = torch.ones_like(text)
    layout = gate.TokenLayout(0, 4, 0, (1, 2, 2))
    weights = torch.tensor([[[.75, 1.25], [.75, 1.25]]])
    projection = nn.Linear(2, 2)
    with torch.no_grad():
        projection.weight.copy_(torch.eye(2)); projection.bias.fill_(7)
    # When: only image features are changed before projection.
    result = projection(text + gate.apply_generated(image, weights, layout))
    # Then: exact three-term expression differs from whole-output scaling.
    assert torch.equal(result, text + image * weights.reshape(1, 4, 1) + 7)
    assert not torch.equal(result, projection(text + image) * weights.reshape(1, 4, 1))


def test_temporal_map_and_coordinates_are_finite():
    # Given: frame0 occupies left, frame1..4 right; later frames blank.
    masks = torch.zeros(17, 32, 48, dtype=torch.bool)
    masks[0, 8:12, 6:10] = True; masks[1:5, 8:12, 34:38] = True
    # When: fixed temporal union/dilation/smoothing/area mapping is applied.
    result, metadata = support_map(masks, (5, 8, 12))
    # Then: time and spatial placement survive the explicit approximation.
    assert result.shape == (5, 8, 12) and bool(torch.isfinite(result).all())
    assert 0 <= float(result.min()) <= float(result.max()) <= 1
    assert result[0, :, :6].sum() > result[0, :, 6:].sum()
    assert result[1, :, 6:].sum() > result[1, :, :6].sum()
    assert not bool(result[2:].any()) and metadata['dilation_radius'] == 4


def test_inputs_weights_and_rng_are_unchanged():
    # Given: actual source-derived tiny forward with frozen fixture weights.
    torch.manual_seed(91)
    original, layer = official_fixture()
    x, context = torch.randn(1, 8, 4), torch.randn(1, 5, 4)
    values = [x, context, *[p for name in ('q','k','v','k_img','v_img','o') for p in getattr(layer, name).parameters()]]
    copies = [v.clone() for v in values]; rng = torch.get_rng_state().clone()
    layout = gate.TokenLayout(2, 4, 2, (1, 2, 2))
    weights = gate.coefficients(torch.tensor([[[1.,0.],[0.,1.]]]), gate.GateMode.METHOD, .5)
    # When: the patched numerical fixture runs.
    patched = gate.compile_forward(original, lambda image: gate.apply_generated(image, weights, layout))
    output = patched(layer, x, context, None)
    # Then: no source tensor, weight or RNG mutation occurs.
    assert bool(torch.isfinite(output).all())
    assert all(torch.equal(a, b) for a, b in zip(values, copies, strict=True))
    assert torch.equal(rng, torch.get_rng_state())


def test_control_statistics_and_spatial_difference():
    # Given: asymmetric support and fixed lambda.
    support = torch.zeros(5, 4, 6); support[:, :2, :2] = 1
    # When: METHOD and predeclared cyclic shift CONTROL are computed.
    method = gate.coefficients(support, gate.GateMode.METHOD, .5)
    control = gate.coefficients(support, gate.GateMode.CONTROL, .5)
    # Then: identical histograms/means but different locations.
    assert torch.equal(method.flatten(1).sort().values, control.flatten(1).sort().values)
    assert torch.allclose(method.mean((1,2)), torch.ones(5), atol=1e-6, rtol=0)
    assert not torch.equal(method, control)


if __name__ == '__main__':
    tests = [value for name, value in globals().copy().items() if name.startswith('test_')]
    for test in tests: test()
    print(json.dumps({'status':'PASS','CPU_contracts':len(tests),'GPU':0,'full_model':0,'FA2_parity':'NOT_RUN'}))
