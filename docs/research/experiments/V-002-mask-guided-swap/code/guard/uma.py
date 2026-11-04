# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
# How to run: imported by the V002 scoped supervisor; CPU tests: python -m unittest test_v002
"""V002-only cache invocation and fresh kernel-event observations, without model imports."""
from dataclasses import dataclass
from pathlib import Path
from typing import Final, TypedDict
import json
import math
import subprocess
import time

CACHE_HELPER: Final = Path('/usr/local/sbin/drop-caches')
ALLOCATOR: Final = 'expandable_segments:True'

class CacheReceipt(TypedDict):
    status: str
    started: float
    finished: float
    returncode: int | None
    detail: str

class KernelReceipt(TypedDict):
    status: str
    cursor: str | None
    observed_at: float
    nvrm_hit: bool
    messages: list[str]
    detail: str


def peak_decision(value: float | None, basis: str) -> str:
    """Require a finite, explicit estimate before admitting any heavy load."""
    if type(value) not in (int, float) or value is None or not math.isfinite(value) or value <= 0:
        return 'START_PEAK_ESTIMATE_INVALID'
    if not isinstance(basis, str) or not basis.strip():
        return 'START_PEAK_ESTIMATE_INVALID'
    return 'START_PEAK_ESTIMATE_EXCEEDED' if value > 100 else 'CLEAR'


def drop_caches() -> CacheReceipt:
    """Invoke only the preinstalled authorized command, never create or repair it."""
    receipt: CacheReceipt = {'status':'ABSENT_CONTINUE','started':time.time(),'finished':0.0,'returncode':None,'detail':''}
    if CACHE_HELPER.is_file():
        try:
            result = subprocess.run(['sudo','-n',str(CACHE_HELPER)],capture_output=True,text=True,timeout=30,check=False)
            receipt.update(status='APPLIED' if result.returncode == 0 else 'REFUSED_CONTINUE',
                           returncode=result.returncode,detail=(result.stdout+result.stderr)[-4096:])
        except (OSError, subprocess.SubprocessError) as error:
            receipt.update(status='UNAVAILABLE_CONTINUE',detail=type(error).__name__+':'+str(error))
    receipt['finished'] = time.time()
    return receipt


@dataclass(slots=True)
class KernelWatch:
    """Mutable cursor ledger: reads only events after the pre-launch cursor."""
    cursor: str | None
    status: str
    detail: str = ''

    @classmethod
    def start(cls) -> 'KernelWatch':
        watch = cls(None, 'AVAILABLE')
        watch._read(initial=True)
        return watch

    def _read(self, *, initial: bool) -> KernelReceipt:
        receipt: KernelReceipt = {'status':self.status,'cursor':self.cursor,'observed_at':time.time(),
                                  'nvrm_hit':False,'messages':[],'detail':self.detail}
        if self.status != 'AVAILABLE':
            return receipt
        command = ['journalctl','-k','--no-pager','-o','json','--show-cursor']
        command += ['-n','1'] if initial else ['--after-cursor='+str(self.cursor)]
        try:
            result = subprocess.run(command,capture_output=True,text=True,timeout=3,check=False)
            if result.returncode:
                unreadable=any(marker in result.stderr.lower() for marker in ('permission','not permitted','no journal files','not found','unrecognized option'))
                self.status='UNAVAILABLE_CONTINUE' if initial and unreadable else 'OBSERVATION_FAILED'
                self.detail=result.stderr[-4096:]
            else:
                for line in result.stdout.splitlines():
                    if line.startswith('-- cursor: '):
                        self.cursor=line.removeprefix('-- cursor: ').strip()
                    elif line.startswith('{'):
                        entry=json.loads(line)
                        if entry.get('__CURSOR'):
                            self.cursor=str(entry['__CURSOR'])
                        message=entry.get('MESSAGE','')
                        if not isinstance(message,str):
                            message=json.dumps(message)
                        if not initial and 'NV_ERR_NO_MEMORY' in message:
                            receipt['messages'].append(message)
                if not self.cursor:
                    self.status='UNAVAILABLE_CONTINUE' if initial else 'OBSERVATION_FAILED'
                    self.detail='No readable kernel cursor: '+result.stderr[-4096:]
        except (FileNotFoundError, PermissionError) as error:
            self.status='UNAVAILABLE_CONTINUE' if initial else 'OBSERVATION_FAILED'
            self.detail=type(error).__name__+':'+str(error)
        except (OSError, subprocess.SubprocessError, ValueError, KeyError) as error:
            self.status='OBSERVATION_FAILED'
            self.detail=type(error).__name__+':'+str(error)
        receipt.update(status=self.status,cursor=self.cursor,nvrm_hit=bool(receipt['messages']),detail=self.detail)
        return receipt

    def poll(self) -> KernelReceipt:
        return self._read(initial=False)
