"""CPU fixture checks; run with the existing Python, no third-party packages."""
import json
import tempfile
from pathlib import Path
import summarize


def test_summary_contract() -> None:
    assert summarize.parse_memory('RssAnon: 123 kB') == 123 * 1024
    assert summarize.parse_memory('MemAvailable: 72 GiB') == 72 * 1024**3
    assert summarize.parse_memory('123') == 123
    with tempfile.TemporaryDirectory() as folder:
        stage = Path(folder)
        assert summarize.summarize_stage(stage)['status'] == 'NOT_RUN'
        reports = stage / 'reports'
        reports.mkdir()
        (reports/'watchdog-launch.json').write_text('{"command":["/private/secret"]}')
        result = summarize.summarize_stage(stage)
        assert result['status'] == 'PRE_WORKER_LAUNCH_ONLY'
        assert result['worker_attempts'] == 0
        (reports/'launch-failure-001.json').write_text('{}')
        archive = reports/'pre-worker-failure-001'
        archive.mkdir()
        (archive/'classification.json').write_text('{"actual_probe_attempts":0,"sampler_attempts":0}')
        assert summarize.summarize_stage(stage)['pre_worker_errors'] == 2
        (reports/'attempt.json').write_text('{"attempt":1}')
        assert summarize.summarize_stage(stage)['status'] == 'RUNNING'
        phase = {'phase':'step_completed_1','epoch':10,'mem_available':'MemAvailable: 100 kB',
                 'process_memory':['VmRSS: 4 kB','RssAnon: 3 kB','RssFile: 1 kB'],
                 'swap_used':0,'cuda_allocated':7,'cuda_reserved':9,'cuda_peak_allocated':8,
                 'cgroup':{'memory.current':'20','memory.peak':'21','memory.stat':'anon 11\nfile 5\n','memory.events':'oom 0\nhigh 2\n'}}
        (reports/'phases.jsonl').write_text(json.dumps(phase)+'\n{"partial":')
        summary = summarize.summarize_stage(stage)
        assert summary['memory_bytes']['rss_peak'] == 4096
        assert summary['memory_bytes']['cgroup_anon_peak'] == 11
        assert summary['memory_bytes']['mem_available_min'] == 102400
        assert summary['memory_bytes']['cuda_reserved_peak'] == 9
        assert summary['incomplete_log_rows'] == 1
        assert '/private' not in json.dumps(summary)
        (reports/'result.json').write_text('{"status":"FAILED","traceback":"/private/secret"}')
        assert summarize.summarize_stage(stage)['status'] == 'FAILED'
    print('PASS: memory units, stage states, accounting, partial JSONL, path exclusion')


if __name__ == '__main__':
    test_summary_contract()
