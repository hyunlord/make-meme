# B-023 실행 기록

2026-10-24 16:54 UTC 착수, 종료 deadline 19:54 UTC(3시간). 사용자 통합 지시와 최신 fee6896 개정 PLAN을 적용한다. 이전 밈 입력·2case·ROI 후보는 실행하지 않는다.

1. 최신 HEAD/clean 문서 worktree와 B022 종료 확인. 기존 B023 실행 디렉터리 및 활성 작업 없음. Spark의 기존 Comfy 서비스 보존.
2. CPU 사전 검증 진행. 신규 GPU sampler/P/PROBE/D 모두 아직0. 기존 B020 adapter-OFF 기준선과 입력/조건을 재사용한다.
3. 실행 전 코드·입력 계보·semantic mask 기대 차이·[작은 EditSpec](EDIT_SPEC.json)을 고정하고 push한 뒤에만 제한 실행한다.

평가: 원본/참조/B020미학습OFF/새replacement 전체17장 및local0/8/16. 사족 자세, 머리 방향/순서, 얼굴·귀·주둥이·목, 원본 장면, padding/잘림, 실제 개체와견종유사성, 비용을 분리한다. 정적 검토는 연속 시간 품질 PASS가 아니다.

## 사전 고정과 PROBE

코드/config/실제 조건 차이를 `9bdae0b665beca1b78b07022626bc526770ff7b5`로 commit/push하고 원격 SHA 일치를 확인했다. original helper prefix exact, 변경2reference-mask/보존14leaf와 device구조·noise/RNG/scheduler 검사를 통과했다. P는0이다.

PROBE1은 실제 tiny CUDA copy/add/synchronize/readback과 조건복원을5.16초에 통과했다. 깨끗한 worker 종료 후 신규 S1을 시작했다. 아직 최종latent·raw 영상은 없고 품질 판정은 PENDING이다.

## 종료

PROBE1→S1→D1을 완료했다. 실제40/80·finite final latent/raw·17f30fps 저장 PASS, 자체worker종료. 정적 전체17장 비교에서 착석/침실/세로경계와 후반 얼굴손상이 지속되어 원본보존 FAIL·품질개선 미입증, temporal UNVERIFIED다. 추가 실행 없이 결과/검토자료를 정리한다. [RESULTS](RESULTS.md).
