import json
from pathlib import Path

from collect_run_evidence import collect_run, hardware


def put(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


def fixture(tmp_path: Path) -> tuple[Path, Path]:
    reports = tmp_path / 'stages/v003-k1-s1-heavy/reports'
    put(tmp_path / 'outputs/K1-s1/receipt.json', {
        'status': 'GENERATED', 'elapsed_seconds': 10, 'scheduler_steps_completed': 11,
        'denoiser_calls': 11, 'peak_rss_kib': 1024, 'command': ['/secret/private'],
    })
    (tmp_path / 'outputs/K1-s1/output.mp4').write_bytes(b'fixture')
    put(reports / 'supervisor-result.json', {
        'status': 'COMPLETE', 'guard_reason': 'COMPLETE', 'normal_exit_recorded': True,
        'started': 0, 'finished': 10, 'nvrm_events': 0,
        'concurrent_external_gpu': False, 'kernel_watch_status': 'AVAILABLE', 'pid': 123,
    })
    row = {'started': 1, 'finished': 2, 'cgroup': {'memory.peak': '5000\n'},
           'worker_memory': {'events': {'high': 3}},
           'system_memory': {'available': 10000, 'psi_full_avg10': 2},
           'worker_rss_highwater_bytes': 4000, 'pid': 999, 'private': '/secret/abc'}
    (reports / 'observations.jsonl').write_text(json.dumps(row) + '\n')
    hw = tmp_path / 'hw.csv'
    hw.write_text('1970-01-01T00:00:05+00:00,50,100,1000,40000,41000,42000,43000,44000,45000,46000,12000\n')
    out = tmp_path / 'public'
    out.mkdir()
    return hw, out


def test_completed_whitelist_and_units(tmp_path):
    hw, out = fixture(tmp_path)
    result = collect_run(tmp_path, {'name': 'K1-s1'}, hw, 'UTC', out)
    assert result['status'] == 'COMPLETE'
    assert result['peak_rss_bytes_receipt'] == 1048576
    assert result['cgroup_peak_bytes_sampled'] == 5000
    assert result['cgroup_high_events_sampled'] == 3
    assert result['psi_full_avg10_max_sampled'] == 2
    assert result['hardware']['max_thermal_zone6_millidegc'] == 46000
    assert result['hardware']['samples'] == 1
    assert '/secret' not in json.dumps(result)
    assert 'pid' not in json.dumps(result).lower()


def test_missing_is_unknown_not_zero(tmp_path):
    out = tmp_path / 'public'
    out.mkdir()
    result = collect_run(tmp_path, {'name': 'K2-s1'}, tmp_path / 'absent', 'UTC', out)
    assert result['status'] == 'UNKNOWN'
    assert result['scheduler_steps_completed'] is None
    assert result['nvrm_events'] is None
    assert result['concurrent_external_gpu'] is None
    assert result['hardware']['status'] == 'UNKNOWN'


def test_generated_without_supervisor_or_output_is_unknown(tmp_path):
    hw, out = fixture(tmp_path)
    (tmp_path / 'stages/v003-k1-s1-heavy/reports/supervisor-result.json').unlink()
    report = tmp_path / 'stages/v003-k1-s1-heavy/reports/observations.jsonl'
    with report.open('a') as stream:
        stream.write('{partial')
    result = collect_run(tmp_path, {'name': 'K1-s1'}, hw, 'UTC', out)
    assert result['status'] == 'UNKNOWN'
    assert result['measurement_scope'] == 'PARTIAL_OR_UNAVAILABLE'
    assert 'OBSERVATION_ROW_INVALID_OR_INCOMPLETE' in result['evidence_issues']


def test_hardware_filters_timezone_and_preserves_missing(tmp_path):
    path = tmp_path / 'hw.csv'
    path.write_text('1970-01-01T09:00:05,50,100,1000,40000,41000,42000,43000,44000,45000,46000,\n'
                    '1970-01-01T09:00:15,99,100,1000,40000,41000,42000,43000,44000,45000,46000,1\n')
    result = hardware(path, 0, 10, 'Asia/Seoul', tmp_path / 'excerpt.csv')
    assert result['samples'] == 1
    assert result['max_gpu_temperature_c'] == 50
    assert result['min_mem_available_mib'] is None
    assert result['missing_sensor_values'] == 1


def test_incomplete_kernel_hit_is_not_lost(tmp_path):
    hw, out = fixture(tmp_path)
    reports = tmp_path / 'stages/v003-k1-s1-heavy/reports'
    (reports / 'supervisor-result.json').unlink()
    (reports / 'kernel-events.jsonl').write_text(json.dumps({'nvrm_hit': True, 'messages': ['/private/host']}) + '\n')
    result = collect_run(tmp_path, {'name': 'K1-s1'}, hw, 'UTC', out)
    assert result['status'] == 'UNKNOWN'
    assert result['nvrm_events'] is None
    assert result['nvrm_hit_observed'] is True
    assert '/private/host' not in json.dumps(result)


def test_positive_supervisor_nvrm_count_without_kernel_row(tmp_path):
    hw, out = fixture(tmp_path)
    supervisor_path = tmp_path / 'stages/v003-k1-s1-heavy/reports/supervisor-result.json'
    supervisor = json.loads(supervisor_path.read_text())
    supervisor.update(status='FAILED', guard_reason='ENGINE_STOPPED_NVRM',
                      normal_exit_recorded=False, nvrm_events=1)
    put(supervisor_path, supervisor)
    result = collect_run(tmp_path, {'name': 'K1-s1'}, hw, 'UTC', out)
    assert result['status'] == 'UNKNOWN'
    assert result['guard_reason'] == 'ENGINE_STOPPED_NVRM'
    assert result['nvrm_events'] == 1
    assert result['nvrm_hit_observed'] is True
