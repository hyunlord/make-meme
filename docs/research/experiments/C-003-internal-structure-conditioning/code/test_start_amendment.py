"""Targeted CPU policy amendment tests; real archived replay is not a historical PASS."""
from pathlib import Path
import hashlib
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/'guard'))
import memory
from memory import MemoryBudget,GIB,MIB
from safety import decide,lifecycle_decision


def system(t=0,**changes):
    row={'monotonic':float(t),'page_size':4096,'available':100*GIB,'swap_total':1024*MIB,
         'swap_free':1024*MIB-256*1024,'swap':256*1024,'pswpin':0,'pswpout':0,'psi_full_total':0,'errors':[]}
    row.update(changes)
    row['swap_free']=row['swap_total']-row['swap']
    return row


def pair(**changes):
    budget=MemoryBudget();budget.inspect(system(),None,'BEFORE_CREATED',start=True)
    return budget.inspect(system(10,**changes),None,'BEFORE_CREATED',start=True)


def run(samples: Path):
    results={}
    def check(name,actual,expected):
        assert actual['decision']==expected,(name,actual)
        results[name]=actual['decision']
    small=pair(pswpout=1,swap=512*1024)
    check('synthetic_small_swapout',small,'CLEAR');assert 'GLOBAL_SWAP_WARNING' in small['warnings']
    check('synthetic_window_incomplete',MemoryBudget().inspect(system(),None,'BEFORE_CREATED',start=True),'START_OBSERVATION_INCOMPLETE')
    check('synthetic_growth',pair(swap=256*1024+64*MIB),'START_SWAP_BUDGET')
    b=MemoryBudget();b.inspect(system(),None,'BEFORE_CREATED');check('synthetic_runtime_growth',b.inspect(system(10,swap=256*1024+64*MIB),None,'BEFORE_CREATED'),'GLOBAL_SWAP_GROWTH')
    check('synthetic_swapout',pair(pswpout=64*MIB//4096),'SWAPOUT_PRESSURE')
    check('synthetic_psi',pair(psi_full_total=1000000),'SYSTEM_PSI_FULL_PRESSURE')
    check('synthetic_headroom',pair(available=71*GIB),'START_HEADROOM_NOT_MET')
    check('synthetic_observation',pair(errors=['explicit fixture read failure']),'OBSERVATION_FAILED')
    b=MemoryBudget();b.inspect(system(pswpout=2),None,'BEFORE_CREATED');check('synthetic_counter_regression',b.inspect(system(1,pswpout=1),None,'BEFORE_CREATED'),'OBSERVATION_FAILED')
    cg={'path':'fixture','current':1,'high':62*GIB,'max':64*GIB,'events':{'oom':0,'oom_kill':0,'high':0},'swap_current':1,'swap_max':0,'swap_events':{'high':0,'max':0,'fail':0},'errors':[]}
    check('synthetic_worker_swap',MemoryBudget().inspect(system(),cg,'ACTIVE'),'WORKER_SWAP_CONTRACT')
    cg['swap_current']=0;cg['events']['oom']=1
    check('synthetic_worker_oom',MemoryBudget().inspect(system(),cg,'ACTIVE'),'WORKER_OOM')
    cg['events']['oom']=0;cg['swap_max']=1
    check('synthetic_worker_contract',MemoryBudget().inspect(system(),cg,'ACTIVE'),'WORKER_SWAP_CONTRACT')
    assert decide([],0,0,{123},False,100,0,{'decision':'CLEAR'})=='UNKNOWN_GPU_PID'
    row={'errors':[],'queue_counts':{'running':0,'pending':0},'memory_verdict':{'decision':'CLEAR'},'unclassified_pids':[123]}
    assert lifecycle_decision(row,{}, {},False,None)=='UNKNOWN_GPU_PID';results['synthetic_external_gpu_both_paths']='UNKNOWN_GPU_PID'
    archived=json.loads(samples.read_text());b=MemoryBudget();replay=[]
    for row in archived:replay.append(b.inspect(row['system_memory'],None,'BEFORE_CREATED',start=True))
    assert replay[-1]['decision']=='CLEAR' and 'GLOBAL_SWAP_WARNING' in replay[-1]['warnings']
    assert all(v['decision']=='START_OBSERVATION_INCOMPLETE' for v in replay[:-1])
    out={'status':'PASS','synthetic':results,'private_archived_replay':{'samples':len(archived),'source_sha256':hashlib.sha256(samples.read_bytes()).hexdigest(),'old_recorded_decision':archived[-1]['decision'],'new_policy_replay':replay[-1],'historical_reclassification':False},'memory_module_sha256':hashlib.sha256(Path(memory.__file__).read_bytes()).hexdigest()}
    print(json.dumps(out,indent=2))


if __name__=='__main__':run(Path(sys.argv[1]))
