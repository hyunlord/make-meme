"""Derive public-safe structural facts from a private nonexecuting graph report."""
from collections import Counter
import json
from pathlib import Path
import sys


def summarize(report: dict) -> dict:
    graph=report['graph']; nodes=report['graph_nodes']
    def literal(index: int) -> object:
        node=nodes[index]
        if node['kind']=='scalar': return node['value']
        if node['kind']=='tuple': return [literal(i) for i in node['edges']]
        raise ValueError('Not a literal scalar/tuple')
    def reduce_node(symbol: str) -> dict:
        found=[node for node in nodes if node['kind']=='reduce' and nodes[node['edges'][0]]['kind']=='global' and nodes[node['edges'][0]]['value']==symbol]
        assert len(found)==1, 'Expected one observed NumPy construction'
        return found[0]
    top_candidates=[node for node in nodes if node['kind']=='dict' and {literal(k) for k,v in node['entries']}==set(graph['top_roots'])]
    assert len(top_candidates)==1
    module_root=next(v for k,v in top_candidates[0]['entries'] if literal(k)=='module')
    seen=set();pending=[module_root]
    while pending:
        index=pending.pop()
        if index not in seen: seen.add(index);pending.extend(nodes[index]['edges'])
    shapes=Counter()
    for index in seen:
        node=nodes[index]
        if node['kind']=='reduce' and nodes[node['edges'][0]]['kind']=='global' and nodes[node['edges'][0]]['value']=='torch._utils _rebuild_tensor_v2':
            args=nodes[node['edges'][1]]['edges'];shapes[tuple(literal(args[2]))]+=1
    module=[row for row in graph['persistent_storage_references'] if row['roots']==['module']]
    assert all(row['storage_type']=='torch FloatStorage' for row in module)
    array=reduce_node('numpy.core.multiarray _reconstruct')
    dtype=reduce_node('numpy dtype')
    args=nodes[array['edges'][1]]['edges']; state=nodes[array['edges'][2]]['edges']
    assert len(args)==3 and len(state)==5
    assert nodes[args[0]]['kind']=='global'
    raw_reduce=nodes[state[4]]
    assert raw_reduce['kind']=='reduce' and nodes[raw_reduce['edges'][0]]['value']=='_codecs encode'
    raw_args=literal(raw_reduce['edges'][1]); assert raw_args[1]=='latin1'
    raw=raw_args[0];assert isinstance(raw,str)
    np_root=next(v for k,v in top_candidates[0]['entries'] if literal(k)=='np_rng_state')
    np_items=nodes[np_root]['edges'];assert len(np_items)==5
    data={
        'status':report['status'],'claim_scope':graph['claim_scope'],
        'checkpoint_sha256_before':report['checkpoint_sha256_before'],'checkpoint_sha256_after':report['checkpoint_sha256_after'],
        'original_unchanged':report['original_unchanged'],'elapsed_seconds':report['seconds'],
        'checkpoint_bytes':report['checkpoint_bytes'],'pickle_bytes':report['pickle_bytes'],
        'zip_members':len(report['zip_members']),'zip_compression_counts':dict(Counter(row['compression'] for row in report['zip_members'])),
        'format_metadata':{key.rsplit('/',1)[-1]:value.strip() for key,value in report['format_metadata'].items()},
        'storage_zip_total_bytes':report['storage_zip_total_bytes'],
        'crc_scope':'Header CRC/offset metadata recorded; individual storage CRC not recomputed. Whole-file SHA checked; tensor contents not loaded.',
        'top_roots':graph['top_roots'],'numpy_globals':graph['numpy_globals'],
        'cross_root_shared_nonliteral_count':len(graph['shared_nonliteral_nodes']),
        'storage_cross_root_shared_keys':graph['storage_shared_across_roots'],
        'storage_reference_count':len(graph['persistent_storage_references']),
        'module_declared_float_storage_count':len(module),
        'module_declared_float_storage_numel':sum(row['numel'] for row in module),
        'module_declared_float_storage_bytes':sum(row['numel'] for row in module)*4,
        'storage_count_scope':'Declared serialized FloatStorage elements, NOT measured model parameter count.',
        'module_declared_tensor_shape_histogram':[{'shape':list(key),'count':count} for key,count in sorted(shapes.items())],
        'numpy_structure':{
            'root':'np_rng_state','rng_name':literal(np_items[0]),
            'subtype_symbol':nodes[args[0]]['value'],'reconstruct_initial_shape':literal(args[1]),
            'reconstruct_third_arg_symbolic_encode_args':literal(nodes[args[2]]['edges'][1]),
            'array_BUILD_state_version':literal(state[0]),'array_shape':literal(state[1]),
            'dtype_REDUCE_args':literal(dtype['edges'][1]),'dtype_BUILD_state':literal(dtype['edges'][2]),
            'fortran_order':literal(state[3]),'raw_data_expression':'symbolic _codecs.encode(unicode_scalar, latin1)',
            'raw_unicode_length':len(raw),'raw_all_codepoints_latin1':all(ord(c)<=255 for c in raw),
            'derived_raw_byte_length_if_latin1':len(raw) if all(ord(c)<=255 for c in raw) else None,
            'rng_position':literal(np_items[2]),'has_gauss':literal(np_items[3]),'cached_gaussian':literal(np_items[4]),
            'persistent_storage_references':sum('np_rng_state' in row['roots'] for row in graph['persistent_storage_references']),
            'runtime_numpy_array_constructed':False,
            'dtype_interpretation':'u4/little-endian flags0 is static uint32 interpretation; NumPy was not invoked.'},
        'actual_checkpoint_deserializations':0,'model_loads':0,'diffusion_calls':0,'full_conversion':'NOT_RUN'}
    return data


if __name__=='__main__':
    source,output=map(Path,sys.argv[1:3])
    output.write_text(json.dumps(summarize(json.loads(source.read_text())),indent=2)+'\n')
