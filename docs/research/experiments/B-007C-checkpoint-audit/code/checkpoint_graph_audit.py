"""Read-only ZIP headers, bounded data.pkl graph and before/after SHA proof."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import struct
import sys
import time
import zipfile
from pickle_graph import AuditBlocked, parse, summarize

EXPECTED='d6c73e94c57eb36e6351c800d1228e41ed7e45db1ccf410dd875bcfdd2945e7f'
EXPECTED_SIZE=65582563395


def digest(path: Path) -> str:
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(8*1024**2),b''): value.update(block)
    return value.hexdigest()


def audit(checkpoint: Path, report: Path, download_ledger: Path) -> None:
    started=time.monotonic()
    prior=[json.loads(line) for line in download_ledger.read_text().splitlines()]
    if not any(row.get('sha256')==EXPECTED and row.get('status')=='VERIFIED' for row in prior):
        raise AuditBlocked('Prior verified download evidence missing')
    before=checkpoint.stat()
    if before.st_size!=EXPECTED_SIZE or digest(checkpoint)!=EXPECTED:
        raise AuditBlocked('Checkpoint provenance hash mismatch')
    result: dict={'checkpoint_sha256_before':EXPECTED,'checkpoint_bytes':before.st_size,'status':'STARTED','read_only':True,'unpickled':False}
    try:
        with zipfile.ZipFile(checkpoint) as archive, checkpoint.open('rb') as raw:
            members=[]
            for item in archive.infolist():
                raw.seek(item.header_offset); header=raw.read(30)
                if len(header)!=30 or header[:4]!=b'PK\x03\x04': raise AuditBlocked('Invalid local ZIP header')
                name_len,extra_len=struct.unpack_from('<HH',header,26)
                members.append({'name':item.filename,'bytes':item.file_size,'compressed_bytes':item.compress_size,'compression':item.compress_type,'crc32':item.CRC,'header_offset':item.header_offset,'payload_offset':item.header_offset+30+name_len+extra_len,'flag_bits':item.flag_bits})
            entries=[item for item in archive.infolist() if item.filename.endswith('/data.pkl')]
            if len(entries)!=1 or entries[0].file_size>32*1024**2: raise AuditBlocked('Ambiguous/oversized data.pkl')
            payload=archive.read(entries[0])
            result['zip_members']=members
            result['format_metadata']={item.filename:archive.read(item).decode('utf-8') for item in archive.infolist() if item.filename.endswith(('/version','/byteorder')) and item.file_size<128}
            graph=parse(payload)
            result['graph']=summarize(graph)
            result['pickle_bytes']=len(payload)
            result['graph_nodes']=[{'kind':n.kind,'value':n.value,'edges':n.edges,'entries':n.entries,'offset':n.offset} for n in graph.nodes]
            result['memo']=graph.memo
            result['storage_zip_total_bytes']=sum(row['bytes'] for row in members if '/data/' in row['name'])
            result['status']='STATIC_GRAPH_COMPLETED'
    except (AuditBlocked,ValueError,KeyError,IndexError,zipfile.BadZipFile) as error:
        result['status']='BLOCKED'; result['error']=repr(error)
    finally:
        after=checkpoint.stat()
        result['checkpoint_sha256_after']=digest(checkpoint)
        result['original_unchanged']=result['checkpoint_sha256_after']==EXPECTED and (before.st_size,before.st_mtime_ns,before.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino)
        result['seconds']=time.monotonic()-started
        report.parent.mkdir(parents=True,exist_ok=True)
        with report.open('x') as handle: json.dump(result,handle,indent=2)
    if result['status']!='STATIC_GRAPH_COMPLETED' or not result['original_unchanged']:
        raise AuditBlocked('See persisted audit report')


if __name__=='__main__': audit(*(Path(value) for value in sys.argv[1:4]))
