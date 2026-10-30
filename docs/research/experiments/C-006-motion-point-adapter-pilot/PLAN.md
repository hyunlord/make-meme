# C-006 사전 계획 — Point–Anchor Adapter 소형 학습

부모 `372c779103a6d5867757bc0df6c845bd920a5b7f`. 시작 2026-10-30 04:01:19 UTC, 총 8시간, 마지막 45분은 기록·전달. 전체 의뢰서는 work_orders에 원문 보존한다.

질문은 시간별 표면점과 양끝 VAE 특징을 작은 공유 adapter로 전달했을 때, 같은 동적 윤곽의 BASE 및 endpoint-only NULL보다 보이는 동작을 더 잘 따르는지다. 같은 개체 self reconstruction과 기존 개 cross-ID 탐색 결과를 분리한다.

## 실행 순서와 고정 예산

1. 기존 DAVIS 자료와 라이선스를 확인하고 원본 영상별 8/2/2 split을 고정한다. 부족하면 최소 4/1/2를 명시한다. dog/dog-gooses/car-roundabout/car-shadow는 train/validation에서 제외한다.
2. CoTracker3 offline 공식 pinned code/단일 checkpoint로 최대 16개 표면점을 한 번씩 추적한다. 별도 프로세스 종료 후 encoder를 실행한다.
3. 각 anchor를 독립 VAE 인코딩한다. target clean latent는 학습 target에만 사용한다. T5, encoded VACE context, mask, tracks는 캐시하되 noisy prefix/VACE hints는 매 update 재계산한다.
4. 기존 1.3B BF16 SDPA, 416×240×33, 마지막 4 block 직전에 FP32 master adapter residual을 넣는다. width192, 4 zero output projection, 총 ≤3M. 실제 frozen tail/head의 gradient를 유지한다.
5. AdamW 1e-4/(0.9,0.999)/weight_decay0.01/clip1, batch1, 최대256 update 또는 active2시간30분. train seed20261030, data seed20261030, inference seed20261028. NULL25%, text drop10%. 1000 Wan shift5 grid에서 새 sigma/noise. object/background area-normalized MSE 1:1. 체크포인트0/128/256 또는 마지막 완료상태.
6. heldout 두 영상에서 BASE→ON→NULL 순서로 각각50step/100model_fn, 최대6개. 유효한 대응이 있으면 기존 개 cross-ID BASE→ON→NULL 3개. 총 sampler heavy 최대10(기계적 예비1포함), VAE-only복구 최대1, 품질재시도0.
7. 모든33장과 fixed0/4/8/12/16/20/24/28/32 비교, 누락·가림·temporal UNVERIFIED를 보존한다. 기록·전달 후 종료한다.

## 변하지 않는 경계

C003에서 성공한 현행 guard와 MemoryMax/High, 시작72GiB/실행24GiB, swap/PSI/OOM/external GPU 조건을 그대로 사용한다. C00514B재실행·guard완화·imagegen·backbone학습은0이다. 안전 중단은 자동 재시도하지 않는다.

NULL의 모든 중간 좌표·속도·visibility/valid는 endpoints에서만 만든다. 공간 kernel bbox 폭은 ON/NULL 모두 같은 endpoint bbox 선형보간을 사용한다. ON의 실제 중간 배열을 읽지 않는다. 두 조건 모두 동적 윤곽이 있으므로 NULL을 모든 motion 제거로 해석하지 않는다.

## 검증과 해석

CPU에서 permutation/gating/NULL independence/token flatten/identity retarget를 검사한다. 실제 첫 update에 zero-init/base, late tail gradient, projection 이후 MLP gradient, frozen base/optimizer membership을 기록한다. 동일조건 replay tolerance는 atol=1e-3,rtol=1e-3로 사전 고정하며 실패 시 완화하지 않는다. loss/gradient/checkpoint와 실제 영상 품질은 별도 판정한다. 고정 검증 probes는 학습 전 지정하고 최종 완료 checkpoint만 평가한다.

실제 split·라이선스·tensor API·runtime freeze는 실행 전에 해당 JSON과 METHOD에 확정한다. 계획 작성은 학습 또는 영상 실행 성공이 아니다.
