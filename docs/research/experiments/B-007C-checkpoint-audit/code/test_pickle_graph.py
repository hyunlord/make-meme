"""Small nonexecuting graph semantics fixtures; no Torch/model dependency."""
import pickle
import struct
from pathlib import Path
import tempfile
import unittest
from pickle_graph import AuditBlocked, parse, summarize


def text(value: str) -> bytes:
    raw=value.encode(); return b'X'+struct.pack('<I',len(raw))+raw


class GraphTests(unittest.TestCase):
    def test_alias_across_roots(self) -> None:
        shared=[]; data={'np_rng_state':shared,'module':{'alias':shared}}
        result=summarize(parse(pickle.dumps(data,protocol=2)))
        self.assertTrue(any(set(n['roots'])=={'np_rng_state','module'} and n['kind']=='list' for n in result['shared_nonliteral_nodes']))

    def test_reduce_never_executes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            marker=Path(directory)/'must-not-exist'
            data=b'\x80\x02}'+text('np_rng_state')+b'cos\nsystem\n'+text('touch '+str(marker))+b'\x85Rq\x01s'+text('module')+b'h\x01s.'
            result=summarize(parse(data))
            self.assertFalse(marker.exists())
            self.assertEqual(result['globals'][0]['roots'],['np_rng_state','module'])

    def test_build_alias_future_mutation(self) -> None:
        # Same symbolic object receives BUILD state after memo registration.
        data=b'\x80\x02}'+text('np_rng_state')+b'cnumpy\ndtype\n'+text('u4')+b'\x85Rq\x01)bs'+text('module')+b'h\x01s.'
        result=summarize(parse(data))
        self.assertEqual(result['numpy_globals'][0]['roots'],['np_rng_state','module'])

    def test_unknown_and_trailing_fail_closed(self) -> None:
        for data in (b'}.', b'\x80\x02}}b.', b'\x80\x04}.', b'\x80\x02}0.', b'\x80\x02}.garbage'):
            with self.assertRaises(AuditBlocked): parse(data)


if __name__=='__main__': unittest.main()
