"""Nonexecuting tensor contract from preregistered protocol2 graph and ZIP headers."""
from __future__ import annotations

import hashlib
import struct
import sys
import zipfile
from pathlib import Path

from pydantic import BaseModel, ConfigDict, model_validator

GRAPH_SHA = "0189400e95975845035f1d29b626595a80f62a9be1b8b27912080e4eda0e0548"


class TensorContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    shape: tuple[int, ...]
    stride: tuple[int, ...]
    storage_offset: int
    storage_bytes: int
    checkpoint_offset: int
    storage_key: str
    dtype: str

    @model_validator(mode="after")
    def valid_range(self) -> TensorContract:
        if len(self.shape) != len(self.stride) or self.storage_offset < 0 or any(s < 0 for s in self.stride):
            raise ValueError("Invalid tensor dimensions/stride/offset")
        last = self.storage_offset + sum((size-1)*stride for size, stride in zip(self.shape, self.stride))
        if any(size <= 0 for size in self.shape) or (last+1)*4 > self.storage_bytes:
            raise ValueError("Tensor range exceeds storage")
        return self


def insert_contract(result: dict[str, TensorContract], name: str, item: TensorContract) -> None:
    if name in result:
        raise ValueError("Duplicate module tensor key")
    result[name] = item


def check_key_set(actual: set[str], expected: set[str], count: int = 987) -> None:
    if len(expected) != count or actual != expected:
        raise ValueError("Exact module key set/count mismatch")


def expected_tensors(checkpoint: Path, graph_code: Path) -> dict[str, TensorContract]:
    """No unpickling, storage decompression, GLOBAL/REDUCE/BUILD execution."""
    if hashlib.sha256((graph_code / "pickle_graph.py").read_bytes()).hexdigest() != GRAPH_SHA:
        raise ValueError("Static graph parser SHA mismatch")
    sys.path.insert(0, str(graph_code))
    from pickle_graph import parse
    with zipfile.ZipFile(checkpoint) as archive:
        pickles = [i for i in archive.infolist() if i.filename.endswith("/data.pkl")]
        if len(pickles) != 1 or pickles[0].file_size != 163821:
            raise ValueError("Fixed checkpoint pickle metadata differs")
        payload = archive.read(pickles[0])
        if hashlib.sha256(payload).hexdigest() != "833b3306eb0b1aacf836b145332a22355fd2fa39736567dd18b770f4e6673d27":
            raise ValueError("Fixed data.pkl digest differs from B007C source")
        graph = parse(payload)
        globals_seen = {node.value for node in graph.nodes if node.kind == "global"}
        expected_globals = {"numpy.core.multiarray _reconstruct", "numpy ndarray", "_codecs encode", "numpy dtype",
                            "torch._utils _rebuild_tensor_v2", "torch ByteStorage", "collections OrderedDict", "torch FloatStorage"}
        if globals_seen != expected_globals:
            raise ValueError("Full static globals differ, including ambient-safe symbols")
        prefix = pickles[0].filename.rsplit("/", 1)[0]
        roots = {graph.scalar(key): value for key, value in graph.nodes[graph.root].entries}
        result: dict[str, TensorContract] = {}
        for key_node, value_node in graph.nodes[roots["module"]].entries:
            name = graph.scalar(key_node)
            node = graph.nodes[value_node]
            if node.kind != "reduce" or graph.nodes[node.edges[0]].value != "torch._utils _rebuild_tensor_v2":
                raise ValueError("Unexpected module tensor reconstruction")
            args = graph.nodes[node.edges[1]].edges
            if len(args) != 6:
                raise ValueError("Unexpected tensor arguments")
            persistent = graph.nodes[args[0]]
            if persistent.kind != "persistent":
                raise ValueError("Missing persistent storage")
            pid = graph.nodes[persistent.edges[0]].edges
            if len(pid) != 5 or graph.scalar(pid[0]) != "storage" or graph.nodes[pid[1]].value != "torch FloatStorage":
                raise ValueError("Expected FloatStorage module tensor")
            storage_key = graph.scalar(pid[2])
            member = archive.getinfo(f"{prefix}/data/{storage_key}")
            if member.compress_type != zipfile.ZIP_STORED or member.file_size != graph.scalar(pid[4])*4:
                raise ValueError("ZIP storage length/compression mismatch")
            with checkpoint.open("rb") as handle:
                handle.seek(member.header_offset)
                header = handle.read(30)
            if header[:4] != b"PK\x03\x04":
                raise ValueError("Invalid local ZIP storage header")
            name_length, extra_length = struct.unpack_from("<HH", header, 26)
            item = TensorContract(shape=tuple(graph.scalar(i) for i in graph.nodes[args[2]].edges),
                                  stride=tuple(graph.scalar(i) for i in graph.nodes[args[3]].edges),
                                  storage_offset=graph.scalar(args[1]), storage_bytes=member.file_size,
                                  checkpoint_offset=member.header_offset+30+name_length+extra_length,
                                  storage_key=storage_key, dtype="torch.float32")
            insert_contract(result, name, item)
    check_key_set(set(result), set(result))
    return result
