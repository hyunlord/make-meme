# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Imported by train/generate using the existing frozen research environment."""
from dataclasses import dataclass
from contextlib import nullcontext
import torch
from torch import Tensor, nn
from torch.utils.checkpoint import checkpoint
from point_adapter import PointAnchorAdapter
from point_features import PointCondition


@dataclass(frozen=True, slots=True)
class ForwardInput:
    latents: Tensor
    timestep: Tensor
    context: Tensor
    vace_context: Tensor
    sigma: Tensor


def adapted_forward(models: tuple[nn.Module, nn.Module], inputs: ForwardInput,
                    adapter_state: tuple[PointAnchorAdapter, PointCondition] | None,
                    training: bool = False) -> Tensor:
    """Native Wan 1.3B minimal path; VACE hints precede the unmodified block ordering.

    Four arguments intentionally distinguish models, immutable inputs, optional
    adapter state and autograd policy. No optional architecture branch is enabled.
    """
    from diffsynth.models.wan_video_dit import sinusoidal_embedding_1d
    dit, vace = models
    assert len(dit.blocks) == 30 and dit.dim == 1536
    # require_vae_embedding defaults True even for this text-only backbone;
    # native code activates it only when y is provided. This path has y=None.
    assert not dit.seperated_timestep
    with torch.no_grad():
        t = dit.time_embedding(sinusoidal_embedding_1d(dit.freq_dim, inputs.timestep))
        modulation = dit.time_projection(t).unflatten(1, (6, dit.dim))
        context = dit.text_embedding(inputs.context)
        patches = dit.patchify(inputs.latents, None)
        frames, height, width = patches.shape[2:]
        assert (frames, height, width) == (9, 15, 26)
        hidden = patches.flatten(2).transpose(1, 2).contiguous()
        freqs = torch.cat([
            dit.freqs[0][:frames].view(frames, 1, 1, -1).expand(frames, height, width, -1),
            dit.freqs[1][:height].view(1, height, 1, -1).expand(frames, height, width, -1),
            dit.freqs[2][:width].view(1, 1, width, -1).expand(frames, height, width, -1),
        ], dim=-1).reshape(frames * height * width, 1, -1).to(hidden.device)
        hints = vace(hidden, inputs.vace_context, context, modulation, freqs,
                     use_gradient_checkpointing=False,
                     use_gradient_checkpointing_offload=False)
        for index in range(26):
            hidden = dit.blocks[index](hidden, context, modulation, freqs)
            if index in vace.vace_layers_mapping:
                hidden = hidden + hints[vace.vace_layers_mapping[index]]
    # Frozen modules still transmit derivatives to the inserted adapter residual.
    grad_context = torch.enable_grad() if training else nullcontext()
    with grad_context:
        motion = None
        if adapter_state is not None:
            adapter, condition = adapter_state
            motion = adapter(condition, inputs.sigma)
        for index in range(26, 30):
            if adapter_state is not None:
                hidden = adapter.residual(motion, index - 26, hidden)
            if training:
                hidden = checkpoint(dit.blocks[index], hidden, context, modulation,
                                    freqs, use_reentrant=False)
            else:
                hidden = dit.blocks[index](hidden, context, modulation, freqs)
            if index in vace.vace_layers_mapping:
                hidden = hidden + hints[vace.vace_layers_mapping[index]]
        prediction = dit.head(hidden, t)
        return dit.unpatchify(prediction, (frames, height, width))
