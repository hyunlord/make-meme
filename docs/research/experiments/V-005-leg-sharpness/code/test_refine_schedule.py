"""CPU contract tests: schedule selection never invents timesteps."""
from pathlib import Path
import importlib.util
import sys

MODULE = Path(__file__).with_name('refine_schedule.py')


def load():
    assert MODULE.exists(), 'R1 schedule implementation absent'
    spec = importlib.util.spec_from_file_location('refine_schedule', MODULE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_actual_two_stage_grid_maps_both_requested_strengths_to_same_step():
    # Given: the frozen official model schedules.
    module = load()
    grids = [[1., .99375, .9875, .98125, .975, .909375, .725, .421875, 0.], [.909375, .725, .421875, 0.]]
    # When: select the closest nonterminal sigma for both requested strengths.
    results = [[module.select_schedule(grid, request) for grid in grids] for request in [.35, .55]]
    # Then: no new timestep is inserted; each stage runs exactly one step.
    assert all(result.sigmas == (.421875, 0.) for pair in results for result in pair)
    assert [[r.start_index for r in pair] for pair in results] == [[7, 2], [7, 2]]


def test_reject_non_descending_grid():
    import pytest
    module = load()
    with pytest.raises(ValueError):
        module.select_schedule([1., .2, .5, 0.], .35)


def test_terminal_zero_is_not_a_denoising_start():
    module = load()
    assert module.select_schedule([1., .4, 0.], .01).sigmas == (.4, 0.)


def test_runtime_hook_preserves_stage_two_chain_and_restores_module(monkeypatch):
    # Given: real adapter with a small fake official chunk boundary (no model imports).
    import types
    schedule = load()
    runtime_spec = importlib.util.spec_from_file_location('refine_runtime', MODULE.with_name('refine_runtime.py'))
    runtime = importlib.util.module_from_spec(runtime_spec)
    runtime_spec.loader.exec_module(runtime)
    package = types.ModuleType('ltx_pipelines')
    official = types.ModuleType('ltx_pipelines.ic_lora')
    calls = []

    class Grid(list):
        def detach(self): return self
        def cpu(self): return self
        def tolist(self): return list(self)

    def original(chunks, stage, **kwargs):
        calls.append((stage, list(chunks), list(kwargs['sigmas']), kwargs['noiser']))
        return iter(['refined-'+stage])

    official.denoise_chunks = original
    package.ic_lora = official
    monkeypatch.setitem(sys.modules, 'ltx_pipelines', package)
    monkeypatch.setitem(sys.modules, 'ltx_pipelines.ic_lora', official)
    monkeypatch.setattr(runtime, 'seeded_chunks', lambda chunks, pipeline, source: iter(['source-latent']))
    observed = []
    noiser = object()
    # When: both stages use the adapter; the second receives upsampled first output.
    with runtime.refinement(object(), Path('source.mp4'), .35, observed):
        first = official.denoise_chunks(iter(['empty']), 'one', Grid([1., .421875, 0.]), noiser, 24)
        second = official.denoise_chunks(iter(['upsampled-'+next(first)]), 'two', Grid([.909375,.421875,0.]), noiser,24)
        assert list(second) == ['refined-two']
    # Then: only first latent is replaced; same noiser survives and monkeypatch is removed.
    assert calls == [('one',['source-latent'],[.421875,0.],noiser),('two',['upsampled-refined-one'],[.421875,0.],noiser)]
    assert official.denoise_chunks is original
    assert [s.steps for s in observed] == [1, 1]


def test_entry_imports_siblings_when_guard_uses_runpy_from_other_cwd(tmp_path):
    # Given: a fresh interpreter outside the script folder, like the guarded worker.
    import subprocess
    entry = MODULE.with_name('refine_entry.py')
    program = 'import runpy,sys;runpy.run_path(sys.argv[1]);assert "torch" not in sys.modules;print("RUNPY_IMPORT_PASS")'
    # When: runpy executes the entry without automatically prepending its directory.
    result = subprocess.run([sys.executable, '-c', program, str(entry)], cwd=tmp_path,
                            text=True, capture_output=True, check=False)
    # Then: sibling modules resolve without importing the model runtime.
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == 'RUNPY_IMPORT_PASS'
