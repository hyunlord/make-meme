# B-020 준비 상태

2026-10-24 · 기준 원격 HEAD `82d22372693a641aa78eaa7974b0a269dab81665`.

**PLANNED / DATA_PENDING / GPU NOT_RUN. 실행 미착수.** [PLAN](PLAN.md)과 [전환 결정](../../decisions/20261024-B-019-to-real-fm.md)을 확인했다. B-018/B-019 구성요소 smoke는 종료하며 다른 synthetic block 실험으로 대체하지 않는다.

## 현재 누락과 확인 범위

B-017의 등록자료 결론은 실제 Lab Y 부재·학습 권한 미확인이다. 이번 준비 요청에는 새 자연동작 영상이나 참조 파일 및 사용 범위가 제공되지 않았다. 이 기존 기록과 이번 요청을 근거로 DATA_PENDING을 유지한다. 개인 폴더 재검색·동일 권한 감사·외부 자료 수집은 하지 않았으며, 모든 로컬 파일에 자료가 없다고 새로 검증했다는 뜻도 아니다.

다음에 필요한 것은 같은 실제 Lab의 자연 고개돌림·걷기·자세 전환 영상 Y 하나와 실제 reference R, 그리고 촬영/사용 권한 및 비공개 연구 학습 허용 범위다. 기존 사진을 R로 사용할 경우 그 파일과 사용 범위를 명시한다. 가능하면 clip 밖 다른 시점 R을 쓰되 여러 세션이나 정밀 관절 정답을 첫 smoke의 필수조건으로 늘리지 않는다. 업로드를 공개 재배포 허용으로 해석하지 않는다. 동물에게 직립 춤을 요구하지 않는다.

## 자료 제공과 실행 지시 이후의 고정 순서

1. 제공 자료만 대상으로 R/D/Y의 동일 개체·사용 범위, 실제 파일·해시·원본 fps/PTS를 확인한다. D=Y는 SELF_RECON_FM_SMOKE이며 driving 복사 shortcut을 명시한다.
2. source만 보고 최초 적합17frame 구간과 RGB/mask의 같은 공간변환·시간 대응·caption을 확정한다. 없는 target을 다른 동물이나 생성물로 채우지 않는다. 새 자료의 시간축을 기존24fps로 단순 재표시하지 않는다.
3. 실제 Y의 VAE latent와 공식 SAT RFLoss/RFScaling 및 Wan head/unpatchify의 부호·scale·축 계약을 대조한다. 계획의 z_sigma=(1−sigma)z_Y+sigma*epsilon, target=epsilon−z_Y가 실제 경로와 맞지 않으면 실행 중지한다. 인공 hidden MSE로 대체하지 않는다.
4. 앞39block의 frozen no_grad 특징을 학습3tuple(sigma0.2/0.5/0.8)과 동일clip 보조평가1tuple(sigma0.65) 각각에서 얻는다. 실제 noise seed·tensor hash·조건·가중치·dtype·geometry·timebase를 사전 고정한다. 지금 존재하지 않는 입력/noise/특징 hash를 만들어 등록하지 않는다. 다른 noise/sigma/조건에 기존 특징을 재사용하지 않는다.
5. 마지막 block self_attn.q/v rank4·alpha4·dropout0 LoRA만 새 Bzero로 시작한다. 공식 head는 동결하되 gradient를 유지하고, 실제 최종 velocity에서 loss를 계산한다. prefix 원경로와 분리 tail/head의 parity tolerance를 결과 전에 고정한다. B-019 TEST_ONLY adapter를 이어 학습하지 않는다.
6. 실제 코드·입력·설정·예산을 사전 commit하고 HISTORY/ROADMAP을 RUNNING으로 바꾸는 시점은 데이터 게이트를 충족하고 실행을 시작할 때다. 이번 문서 등록은 그 시점이 아니다.

## 예산과 판정 경계

계획상 향후 상한은 조건/target 인코딩1회, prefix4tuple 각1회, tail worker1회·최대20update·추가tail평가12회, 학습 전후 sampler 각최대1회와 해당decode 각1회, 재시도/튜닝0이다. 이 문서로 GPU 실행을 승인하거나 예약하지 않는다. 기존72GiB 시작·24GiB 실행 headroom·swap0·타서비스 보호와 단계별 자원 회복을 유지한다. tail cap16GiB/high14GiB는 cgroup 규약이며 전체 CUDA 통합메모리 상한 보장이 아니다.

loss 전후, 저장/reload/OFF, 영상 변화, 실제 개체·동작 품질을 별도로 판단한다. 같은clip noise/time holdout은 독립 영상 평가가 아니며 한clip overfit을 cross-ID 춤 전이나 일반화로 보고하지 않는다.

## 이번 준비 작업의 실제 사용량

| 항목 | 실행 |
|---|---:|
| 새 데이터 감사·수집 / synthetic block 실험 | 0 |
| GPU worker / 인코딩 / prefix 추출 | 0 |
| optimizer update / 영상 sampler / decode | 0 |
| 모델·패키지 다운로드 / 외부 생성 | 0 |

실제 입력 manifest·학습 runner 검증·split parity·실측·영상 품질은 아직 NOT_RUN이다. RESULTS와 실행 결과용 학습 해설은 실제 실험 이후 관측에 근거해 작성한다. 개인 미디어·특징·latent·adapter·weights는 공개하지 않는다. 기존 A·B 실행 코드·가중치·결과는 변경하지 않았다.

## 후속 상태: 실제 자료 제공, 입력 확정 진행

2026-10-24 사용자가 실제 Lab 영상과 기존 사진의 비공개 연구 학습·평가 사용을 허용하고 실행을 지시했다. 위 DATA_PENDING은 자료 제공 이전의 기록이다. 현재 해당 Lab 자료 게이트는 해소됐으며 입력/코드 계약을 확정 중이다. [추가 입력 계약](INPUT_AMENDMENT.md). GPU는 아직 NOT_RUN이며 기존 제3자 자료 권한 기록은 유지한다.

## 2026-10-24 실제 실행 종료

COMPLETED / FM_TAIL_UPDATE_RELOAD_PASS / 목표전신FAIL / QUALITY_NOT_ESTABLISHED / temporalUNVERIFIED. 새자료로해당DATA_PENDING을해소하고 계획된20update와전후영상각1을수행했다. 과거제3자권한미확인과cross-ID/일반화NOT_RUN은보존한다. 상세 RESULTS참조.
