# C-005 결과 — 14B 첫 적재 안전 중단, 품질 비교 미완료

**새14B 영상은0개이며, 1.3B 대비 외형·동작·장면 이득은 평가하지 못했다. quality=INCONCLUSIVE / execution=BLOCKED_RESOURCE(PSI 안전 중단)다.** 차량 첫 모델 적재 시 기존 시스템 memory PSI full 기준을 넘었다. 사용자 계약에 따라 개 실행·예비 재시도·offload 튜닝을 하지 않고 종료했다. 더 큰 모델의 품질 FAIL이나 이번 정책에서의 영구적인 실행 불가능을 뜻하지 않는다.

## 질문에 대한 답

1. **14B가 결합 품질을 개선했는가?** 미평가다. 첫 forward 전 중단되어 실제 비교 영상이 없다. 기존1.3B 두 결과만 재사용하며 새 결과로 대체하지 않는다.
2. **외형·동작 중 무엇이 좋아졌는가?** 확인 가능한 개선이 없다. 각 품질 축은 UNCERTAIN/NOT_EVALUATED이며 다운로드·CPU 검사를 품질 성과로 세지 않는다.
3. **보호 장면이나 형태에 어떤 손해가 생겼는가?** 새 출력이 없어 미평가다. 기존 C-002 차량 TRADE_OFF, 개 COARSE_CONTROL_ONLY와 종료 앵커 충돌은 그대로 보존한다.
4. **같은 입력 비교였는가?** 두 사례 X/G33장·텍스트는 실제 CPU에서 C-002와 같음을 확인했다. native memory path가 달라 사전 설계는 QUALIFIED였지만, 실제14B noise/context/mask64/scheduler는 NOT_OBSERVED/NOT_REACHED다. 같은 seed만으로 runtime 동일성을 주장하지 않는다.
5. **추가 비용은?** 공식7shards63,252,305,152bytes를862.251초에 다운로드·완료 해시 검증했다. 작은 metadata205,316bytes와 별도 bounded header probe가 추가됐다. Heavy1회가 적재 시작으로 소진됐고 sampler/forward/step/decode/영상은 모두0이다. supervisor worker 구간6.844초, systemd runtime6.758초이며 성공한 적재/추론 시간은 아니다. [COSTS](COSTS.json).
6. **다음 개발 모델은?** 14B 품질을 근거로 전환할 증거가 없어 선택을 보류한다. 기존1.3B를 이미 실행 가능한 비교 기준선으로 유지하되 최고 품질 모델로 선정하지 않는다. 이번 이후 자동 재개·새 모델/양자화/가드 연구는 없다.

## 실제 중단 근거와 분류

기존 fresh 시작 관측과 두 guarded CPU route는 COMPLETE였다. 첫 차량 heavy에서 모델 적재 시작 파일을 남긴 뒤 `SYSTEM_PSI_FULL_PRESSURE`가 관측됐다. 최근10초 system memory PSI full stall 비율은 **0.1408681(14.08681%)**로 고정10% 기준을 넘었다. 해당 표본 MemAvailable117,401,010,176bytes, worker memory.current4,609,273,856bytes, high/oom/oom_kill0, swap.current0/swap.max0이었다. 전역 swap1,806,336bytes는 baseline과 같고 swap-out 증가0이었다. 넉넉한 available이나 낮은 worker 점유를 이유로 PSI 보호를 무시하지 않았다.

원인 주체는 UNKNOWN이다. 이 관측만으로 모델 OOM·CUDA 결함·다른 서비스 책임으로 재분류하지 않는다. static memory 추정은 실제 성공 peak의 측정값이 아니며 모델 전체 적재도 완료되지 않았다.

Raw supervisor 분류는 **NOT_CLEAN**, normal_exit_recorded=false다. worker_returncode=0도 정상 연구 완료를 뜻하지 않는다. worker log는 TERM 종료를 기록했고, 최종 memory verdict는 **OBSERVATION_FAILED / cgroup:REMOVED:exit_not_verified**다. 이를 소급 CLEAR/PASS로 고치지 않는다. cleanup_errors는[]이고 최종 systemd inactive/dead, owned/GPU 목록은 비어 있어 프로세스가 멈춘 근거는 있다. 정상 종료 검증 성공과는 구분한다. [정확한 중단 요약](STOP_EVIDENCE.json).

## 실제 수행·보존

사전 다운로드 계획355d19c9353a8d41df38318bffe649ce06747965, inference 전 코드/조건 freeze0c2ef51b1c3c2995b9ae35296e6c7c40346430c0를 원격에 게시했다. 공식 immutable14B revision과 exact7shards의 SHA256을 검증하고, 실제 설치 클래스의 CPU/meta에서 DiT1095+VACE236 key/shape가 모두 일치함을 확인했다. 기존 T5/VAE/tokenizer6개는 공식 hash와 기존 검증 기록이 맞아 재사용했다. [MODEL_MANIFEST](MODEL_MANIFEST.json).

첫 시도에 실제 저장한 condition/mask33장, config, model-load-attempt, 단계 관측과 원본 guard 로그를 private에 보존했다. final latent/raw/생성33장/새MP4는 존재하지 않는다. 개는 모델 적재도 하지 않았다. 전체heavy상한3 중1 사용·2 미실행이며 남은 예산을 새 승인으로 바꾸거나 자동 예약하지 않는다. imagegen/SAM/학습/새 패키지/품질 재시도0이다.

검토 뷰어는 source/reference/원래 앵커/C-002 두 기준선과 모델 입력 조건을 보여 주며14B 결과 자리는 NOT_RUN으로 명확히 표시한다. 기존 MP4 bytes를 유지하고 비교 시트/preview는 파생물로 구분한다. 파일 decode·브라우저 QA는 연속 지각 품질 검수가 아니므로 **temporal=UNVERIFIED**다. A/B와 C-001~004의 과거 판정은 변경하지 않는다.
