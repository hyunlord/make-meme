"""Isolated canonical-module install and scalar-only position observations."""
from collections.abc import Callable
from dataclasses import dataclass, field
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType
from typing import TypedDict


class Shifts(TypedDict):
    ref: int
    additional_ref: int
    pose: int
    video: int


class PositionRow(TypedDict):
    model_call: int
    step_index: int
    branch: str
    block: int
    T: Shifts
    H: Shifts
    W: Shifts
    ref_tokens: int
    video_tokens: int
    pose_tokens: int
    grid: list[int]


def install(root: Path) -> ModuleType:
    """Replace only the canonical module cache with the hash-checked private copy."""
    package=importlib.import_module('wan.modules')
    path=root/'patched/model_scail2.py'
    name='wan.modules.model_scail2'
    spec=importlib.util.spec_from_file_location(name,path)
    assert spec is not None and spec.loader is not None
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    spec.loader.exec_module(module)
    setattr(package,'model_scail2',module)
    return module


@dataclass(slots=True)
class PositionTrace:
    root: Path
    model_call: Callable[[], int]
    counts: list[int] = field(default_factory=lambda:[0]*40)

    def observe(self, block: int, t: Shifts, h: Shifts, w: Shifts,
                ref_tokens: int, video_tokens: int, pose_tokens: int,
                height: int, width: int, frames: int) -> None:
        """Check every block/call, writing only first and last step CFG branches."""
        call=self.model_call()
        assert 1<=call<=80 and 0<=block<40
        assert t=={'additional_ref':0,'ref':0,'pose':1,'video':1}
        assert h=={'ref':120,'additional_ref':0,'pose':0,'video':0}
        assert w=={'ref':0,'additional_ref':0,'pose':120,'video':0}
        assert (height,width,frames)==(56,32,5)
        assert (ref_tokens,video_tokens,pose_tokens)==(1792,8960,2240)
        self.counts[block]+=1
        if call in (1,2,79,80):
            row: PositionRow={'model_call':call,'step_index':(call-1)//2,'branch':'c_orig' if call%2 else 'u_orig','block':block,'T':t,'H':h,'W':w,'ref_tokens':ref_tokens,'video_tokens':video_tokens,'pose_tokens':pose_tokens,'grid':[frames,height,width]}
            with (self.root/'reports/rope_positions.jsonl').open('a') as stream:
                _ = stream.write(json.dumps(row)+'\n')

    def finish(self) -> str:
        assert self.counts==[80]*40
        path=self.root/'reports/rope_positions.jsonl'
        assert len(path.read_text().splitlines())==160
        return hashlib.sha256(path.read_bytes()).hexdigest()
