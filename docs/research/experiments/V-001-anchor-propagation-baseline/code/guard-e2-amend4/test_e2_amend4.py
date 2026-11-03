"""Check the actual systemd command properties without launching systemd."""
import ast
import hashlib
import json
from pathlib import Path
import unittest
from supervisor import worker_memory_cap

class E2Amendment4(unittest.TestCase):
    def test_actual_command_high_equals_max_100_gib(self):
        tree=ast.parse((Path(__file__).parent/'supervisor.py').read_text())
        command=next(node.value for node in ast.walk(tree) if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='command' for t in node.targets) and isinstance(node.value,ast.List) and any(isinstance(e,ast.Constant) and e.value=='systemd-run' for e in node.value.elts))
        expressions=[e for e in command.elts if isinstance(e,ast.JoinedStr) and any(isinstance(v,ast.Constant) and v.value in ('MemoryMax=','MemoryHigh=') for v in e.values)]
        cap=worker_memory_cap(112*2**30)
        properties=[eval(compile(ast.Expression(e),'<trusted command expression>','eval'),{'__builtins__':{}},{'cap':cap}) for e in expressions]
        self.assertEqual(set(properties),{'MemoryMax=107374182400','MemoryHigh=107374182400'})

    def test_amendment3_runtime_files_unchanged(self):
        here=Path(__file__).resolve().parent
        for row in json.loads((here/'AMENDMENT3_HASHES.json').read_text()):
            self.assertEqual(hashlib.sha256((here.parent/'guard-e2-amend3'/row['file']).read_bytes()).hexdigest(),row['sha256'])

    def test_all_other_runtime_code_byte_identical(self):
        here=Path(__file__).resolve().parent;old=here.parent/'guard-e2-amend3'
        for name in ('memory.py','policy.py','safety.py'):
            self.assertEqual((here/name).read_bytes(),(old/name).read_bytes())
        expected=(old/'supervisor.py').read_text().replace('MemoryHigh={cap-2*2**30}','MemoryHigh={cap}')
        self.assertEqual((here/'supervisor.py').read_text(),expected)

if __name__=='__main__': unittest.main()
