"""Four CPU fixtures; no CUDA, process launch or live network observation."""
from safety import decide, start_decision

def run() -> None:
    assert decide([],0,0,set(),True,80,0)=='COMPLETE'
    assert decide([],1,0,set(),False,80,0)=='QUEUE_BUSY'
    assert decide([],0,0,{99},False,80,0)=='UNKNOWN_GPU_PID'
    assert decide(['queue observation failed'],0,0,set(),False,80,0)=='OBSERVATION_FAILED'
    assert decide([],1,0,set(),True,80,0)=='QUEUE_BUSY'
    assert start_decision('CLEAR',71.99,100)=='START_HEADROOM_NOT_MET'
    assert start_decision('CLEAR',80,59)=='DEADLINE'
    assert start_decision('CLEAR',72,100)=='CLEAR'
    print('{"status":"PASS","fixtures":8,"GPU_operations":0}')
if __name__=='__main__':run()
