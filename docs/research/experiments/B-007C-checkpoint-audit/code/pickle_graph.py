"""Nonexecuting protocol-2 stack/memo graph audit, never an unpickler."""
from __future__ import annotations
from dataclasses import dataclass, field
import pickletools


class AuditBlocked(ValueError):
    """Observed stream exceeds this deliberately narrow interpreter."""


@dataclass
class Node:
    kind: str
    value: object = None
    edges: list[int] = field(default_factory=list)
    entries: list[tuple[int, int]] = field(default_factory=list)
    offset: int = 0


@dataclass
class Graph:
    nodes: list[Node]
    root: int
    memo: dict[int, int]
    opcodes: dict[str, int]

    def reachable(self, start: int) -> set[int]:
        seen: set[int] = set()
        pending = [start]
        while pending:
            node_id = pending.pop()
            if node_id not in seen:
                seen.add(node_id)
                pending.extend(self.nodes[node_id].edges)
        return seen

    def scalar(self, node_id: int) -> object:
        node = self.nodes[node_id]
        if node.kind != 'scalar':
            raise AuditBlocked('Expected literal scalar')
        return node.value


def parse(payload: bytes) -> Graph:
    nodes: list[Node] = []
    stack: list[int | None] = []
    memo: dict[int, int] = {}
    counts: dict[str, int] = {}
    offset = 0
    def add(kind: str, value: object = None, edges: list[int] | None = None) -> int:
        nodes.append(Node(kind, value, edges or [], offset=offset))
        return len(nodes)-1
    def pop() -> int:
        if not stack or stack[-1] is None:
            raise AuditBlocked('Invalid stack pop')
        return stack.pop()  # type: ignore[return-value]
    def marked() -> list[int]:
        values: list[int] = []
        while stack and stack[-1] is not None:
            values.append(pop())
        if not stack:
            raise AuditBlocked('Missing MARK')
        stack.pop()
        return list(reversed(values))
    def dictionary(target: int, pairs: list[int]) -> None:
        node = nodes[target]
        ordered = node.kind == 'reduce' and nodes[node.edges[0]].kind == 'global' and nodes[node.edges[0]].value == 'collections OrderedDict'
        if node.kind != 'dict' and not ordered:
            raise AuditBlocked('Unsupported SETITEM target')
        if len(pairs) % 2:
            raise AuditBlocked('Odd dictionary pairs')
        node.entries.extend(zip(pairs[::2], pairs[1::2]))
        node.edges.extend(pairs)
    for index, (opcode, arg, offset) in enumerate(pickletools.genops(payload)):
        if index >= 500000:
            raise AuditBlocked('Opcode budget')
        op = opcode.name
        if index == 0 and op != 'PROTO':
            raise AuditBlocked('Missing initial protocol declaration')
        counts[op] = counts.get(op, 0)+1
        if op == 'PROTO':
            if index != 0 or arg != 2:
                raise AuditBlocked('Only observed protocol 2 supported')
        elif op == 'MARK':
            stack.append(None)
        elif op in ('BINUNICODE','BININT','BININT1','BININT2','LONG1','LONG4','BINFLOAT'):
            stack.append(add('scalar', arg))
        elif op in ('NONE','NEWTRUE','NEWFALSE'):
            stack.append(add('scalar', {'NONE':None,'NEWTRUE':True,'NEWFALSE':False}[op]))
        elif op == 'GLOBAL':
            stack.append(add('global', arg))
        elif op in ('EMPTY_DICT','EMPTY_LIST','EMPTY_TUPLE'):
            stack.append(add({'EMPTY_DICT':'dict','EMPTY_LIST':'list','EMPTY_TUPLE':'tuple'}[op]))
        elif op == 'TUPLE':
            stack.append(add('tuple', edges=marked()))
        elif op in ('TUPLE1','TUPLE2','TUPLE3'):
            values = [pop() for _ in range(int(op[-1]))]
            stack.append(add('tuple', edges=list(reversed(values))))
        elif op in ('BINPUT','LONG_BINPUT'):
            if arg in memo or not stack or stack[-1] is None:
                raise AuditBlocked('Memo overwrite or empty memo insertion')
            memo[arg] = stack[-1]  # type: ignore[assignment]
        elif op in ('BINGET','LONG_BINGET'):
            if arg not in memo:
                raise AuditBlocked('Unknown memo reference')
            stack.append(memo[arg])
        elif op == 'REDUCE':
            args, function = pop(), pop()
            if nodes[args].kind != 'tuple':
                raise AuditBlocked('REDUCE arguments not tuple')
            stack.append(add('reduce', edges=[function,args]))
        elif op == 'BUILD':
            state = pop()
            if not stack or stack[-1] is None:
                raise AuditBlocked('BUILD without instance')
            if nodes[stack[-1]].kind != 'reduce':
                raise AuditBlocked('BUILD target is not observed reduce instance')
            nodes[stack[-1]].edges.append(state)
        elif op == 'BINPERSID':
            stack.append(add('persistent', edges=[pop()]))
        elif op == 'SETITEM':
            value, key = pop(), pop()
            if not stack or stack[-1] is None:
                raise AuditBlocked('SETITEM missing target')
            dictionary(stack[-1], [key,value])
        elif op == 'SETITEMS':
            pairs = marked()
            if not stack or stack[-1] is None:
                raise AuditBlocked('SETITEMS missing target')
            dictionary(stack[-1],pairs)
        elif op in ('APPEND','APPENDS'):
            values = [pop()] if op == 'APPEND' else marked()
            if not stack or stack[-1] is None or nodes[stack[-1]].kind != 'list':
                raise AuditBlocked('Unsupported APPEND target')
            nodes[stack[-1]].edges.extend(values)
        elif op == 'STOP':
            if len(stack) != 1 or stack[0] is None or offset != len(payload)-1:
                raise AuditBlocked('Invalid terminal stack/trailing bytes')
            return Graph(nodes, stack[0], memo, counts)
        else:
            raise AuditBlocked(f'Unsupported opcode {op} at {offset}')
    raise AuditBlocked('Missing STOP')


def summarize(graph: Graph) -> dict:
    top = graph.nodes[graph.root]
    if top.kind != 'dict':
        raise AuditBlocked('Top level must be plain dict')
    roots: dict[str, int] = {}
    for key,value in top.entries:
        name = graph.scalar(key)
        if not isinstance(name,str) or name in roots:
            raise AuditBlocked('Non-string/duplicate top root')
        roots[name] = value
    reach = {key:graph.reachable(value) for key,value in roots.items()}
    memberships = {i:[key for key,items in reach.items() if i in items] for i in range(len(graph.nodes))}
    globals_used = [{'node':i,'name':n.value,'offset':n.offset,'roots':memberships[i]} for i,n in enumerate(graph.nodes) if n.kind=='global']
    shared = [{'node':i,'kind':n.kind,'roots':memberships[i]} for i,n in enumerate(graph.nodes) if len(memberships[i])>1 and n.kind not in ('scalar','global')]
    storage = []
    for i,n in enumerate(graph.nodes):
        if n.kind != 'persistent':
            continue
        pid = graph.nodes[n.edges[0]]
        if pid.kind != 'tuple' or len(pid.edges)!=5 or graph.scalar(pid.edges[0])!='storage':
            raise AuditBlocked('Unsupported persistent ID layout')
        stype = graph.nodes[pid.edges[1]]
        if stype.kind!='global':
            raise AuditBlocked('Storage type is not global symbol')
        storage.append({'node':i,'storage_type':stype.value,'key':graph.scalar(pid.edges[2]),'location':graph.scalar(pid.edges[3]),'numel':graph.scalar(pid.edges[4]),'roots':memberships[i]})
    storage_roots: dict[str,set[str]] = {}
    for row in storage:
        storage_roots.setdefault(str(row['key']),set()).update(row['roots'])
    return {'top_roots':list(roots),'node_count':len(graph.nodes),'memo_count':len(graph.memo),'opcode_counts':graph.opcodes,'globals':globals_used,'numpy_globals':[r for r in globals_used if str(r['name']).startswith('numpy')],'shared_nonliteral_nodes':shared,'persistent_storage_references':storage,'storage_shared_across_roots':{key:sorted(value) for key,value in storage_roots.items() if len(value)>1},'claim_scope':'Syntactic pickle graph reachability only; reducer/build code never invoked; arbitrary callable semantics not modeled.'}
