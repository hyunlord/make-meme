"""CPU fakes verify control flow only; they do not establish model execution."""
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import e2_entry


class Grid:
    def __init__(self, size):
        self.size = size

    def detach(self):
        return self

    def cpu(self):
        return self

    def tolist(self):
        return list(range(self.size))


class Scheduler:
    timesteps = Grid(40)
    sigmas = Grid(41)

    def step(self):
        return 123


class Model:
    def __init__(self):
        self.scheduler = Scheduler()

    def shared_step(self):
        return 42

    def sample(self):
        for _ in range(40):
            for _ in range(4):
                self.shared_step()
            self.scheduler.step()


class EntryTests(unittest.TestCase):
    def test_import_has_no_torch(self):
        self.assertNotIn("torch", sys.modules)

    def test_cpu_validation_does_not_import_models(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "infer_single_gpu.py").touch()
            (root / "config.json").write_text('{"model_type":"bernini_renderer"}')
            for name in ("source.mp4", "anchor.png"):
                (root / name).touch()
            case = {"task_type": "rv2v", "guidance_mode": "rv2v",
                    "prompt": e2_entry.PROMPT, "video": str(root / "source.mp4"),
                    "images": [str(root / "anchor.png")], "output": str(root / "out.mp4")}
            (root / "case.json").write_text(json.dumps(case))
            config = {"python": sys.executable, "engine_root": directory,
                      "model_root": directory, "case": str(root / "case.json"),
                      "output": case["output"], "receipt": str(root / "receipt.json"),
                      "ffprobe": sys.executable, "mode": "probe", "seed": 20261103,
                      "num_frames": 73}
            config_path = root / "private.json"
            config_path.write_text(json.dumps(config))
            info = {"width": 832, "height": 480, "nb_read_frames": "73", "r_frame_rate": "24/1"}
            with patch.object(e2_entry, "media_info", return_value=info), \
                 patch.object(sys, "argv", ["entry", "--config", str(config_path), "--cpu-only"]), \
                 patch.object(e2_entry, "run_heavy") as heavy:
                e2_entry.main()
                heavy.assert_not_called()
            self.assertNotIn("torch", sys.modules)
            self.assertFalse((root / "receipt.json").exists())

    def execute(self, mode):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "out.mp4"
            receipt = root / "receipt.json"
            decoded = []
            cuda = types.SimpleNamespace(synchronize=lambda: None,
                                         max_memory_allocated=lambda: 10,
                                         max_memory_reserved=lambda: 20)
            fake_torch = types.SimpleNamespace(cuda=cuda)
            fake_model = types.SimpleNamespace(GEN_Wanx22=Model)

            def official_entry(*args, **kwargs):
                Model().sample()
                decoded.append(True)
                output.write_bytes(b"fake-control-flow-only")

            modules = {"torch": fake_torch, "bernini": types.ModuleType("bernini"),
                       "bernini.models": types.ModuleType("bernini.models"),
                       "bernini.models.wan_diffusion": fake_model}
            config = {"mode": mode, "seed": 20261103, "num_frames": 73,
                      "engine_root": directory, "receipt": str(receipt), "output": str(output)}
            with patch.dict(sys.modules, modules), patch.object(e2_entry.runpy, "run_path", official_entry):
                e2_entry.run_heavy(config, ["fake-official.py"])
            return json.loads(receipt.read_text()), decoded

    def test_probe_stops_after_one_full_step_and_before_decode(self):
        receipt, decoded = self.execute("probe")
        self.assertEqual(receipt["scheduler_steps"], 1)
        self.assertEqual(receipt["dit_forward_calls"], 4)
        self.assertEqual(len(receipt["timesteps"]), 40)
        self.assertEqual(receipt["status"], "PROBE_COMPLETE_NO_DECODE")
        self.assertEqual(decoded, [])

    def test_generation_keeps_all_steps_and_decode(self):
        receipt, decoded = self.execute("generate")
        self.assertEqual(receipt["scheduler_steps"], 40)
        self.assertEqual(receipt["dit_forward_calls"], 160)
        self.assertEqual(decoded, [True])
        self.assertEqual(receipt["status"], "GENERATION_COMPLETE")


if __name__ == "__main__":
    unittest.main()
