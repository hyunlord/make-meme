# B-012 실행 기록

**최종 상태 COMPLETED / 두 조건 실행·조건 통제 PASS / 후반 상대 머리 roll의 탐색적 대응 근거 / temporal UNVERIFIED.** P/PROBE/S/D 각 조건1회, full sampler2/2·재시도0. 모든 자체 GPU 작업은 종료됐다. [최종 결과](RESULTS.md), [실측](MEASUREMENTS.md). 아래 RUNNING/NOT_RUN 문장은 당시 단계의 이력이며 현재 상태를 뜻하지 않는다.

상태 RUNNING / 실제 P·PROBE·S·D NOT_RUN. 시작2026-10-23 13:19 UTC, 원격 HEAD `aea64a71baf75db31a4aa4b9240ae4de8ad44545`. 총 deadline17:19 UTC, worker는17:10 UTC를 보수적 종료 시각으로 사용한다. 앞선 연결 실패 시도는 파일 읽기 응답을 확보하지 못한 도구 장애이며 sampler사용0이다. B-010 사용0·B-011 사용1 기록을 보존한다.

1. COMPLETED: 실제24fps·361프레임 원본과 후보3개 확인. 가장 이른 적합 [7,24)를 선정하고 local0/12/14/16 사건을 고정했다. 큰 마지막 머리 기울임은 난점으로 유지한다. [선정](SOURCE_SELECTION.md).
2. COMPLETED / GPU0: RGB·mask 모두 동적/정적 대응, 동일reference/text, 실제CPU 전처리와 입력 해시를 고정했다. 4변경/12보존 검사와 CPU8fixture·critical lint 통과. strict typecheck는92개 진단으로 NOT_CLEAN이며 이를 숨기지 않는다. [입력](INPUT_PREPARATION.json), [CPU](CPU_VALIDATION.json), [평가](PREREG_EVALUATION.md). 과거 B009 mask metadata가 복사된 것을 사전 검토에서 발견해 제거했으며 actual B012 입력만 기록한다. 생성 후 계약 변경이 아니다.
3. IN_PROGRESS: MOV P1·STILL P1 정상 완료/종료. 실제16leaf 중 예상 driving4개만 변경, 나머지12개 모두 bit-exact(max_abs0). noise/RNG/scheduler 포함. [실측 비교](CONDITION_COMPARISON.json). 사전 코드 `8e80bdcfb9351bde5960cea4655f95ffaf22e98b`를 원격 확인한 뒤 실행했으며 이제 각 PROBE/S/D를 순차 진행한다. 각단계1회·전체sampler2회·실패포함·재시도0.
4. PENDING: 전체17장 SOURCE/STATIC COPY/MOV/STILL, 사전 상대 사건·coverage·불확실성·실측·한국어 해설.
5. PENDING: RESULTS/HISTORY/ROADMAP·재현 commit/push/원격 SHA와 비공개 ZIP·양호스트 무결성.

MOV PROBE/S/D 각1회 기술 완료: 실제40step·80forward, finite FP32 final latent `[16,5,112,64]`, raw `[3,17,896,512]`,17f24fps MP4. S guard1102.221초, 정상exit0/PID0. 최종 latent 파일SHA `7f407b8d2acf3c8b8b30d73732676be7ac9a7c964e0646f477c70b98f63f177d`; initial noise가 아닌 최종 값의 lossless readback을 확인했다. STILL PROBE도 통과해 마지막 S1을 시작했다. 두 출력의 유용한 동작 비교·연속 시간 품질은 아직 판정하지 않았다.

기존 tiny CUDA/anchor/mixed loader/FlashAttention/조건-샘플링-decode 분리·72GiB시작/24GiB실행 headroom·swap0·타 서비스 보호를 유지한다. 새 모델·다운로드·학습·LoRA·imagegen·외부생성0. 첫 결과의 품질만으로 STILL을 생략하지 않으며 입력·자원·안전 실패는 후속 중단 사유다. 동일seed만이 아닌 실제noise/RNG를 비교한다. 현재 결과·품질 미실행이며 실제 연속 재생을 관찰하지 못하면 temporal UNVERIFIED다.

대형4가중치는 이전 검증 SHA와 이번 실제 파일 크기/stat를 재사용 확인했다. 이번 전체 바이트 SHA 재계산으로 표현하지 않는다. tokenizer4파일은 이번 SHA를 대조했다. 실행 코드·case config·upstream·입력의 격리된 case/stage1080개 대조를 통과했다. 실제 두 P의 조건 비교를 통과해야 sampler로 진행한다.

## 종료 관측

STILL도 실제40step·80forward, finite final latent/readback, finite raw `[3,17,896,512]`와17f24fps MP4를 확보했다. 전체17장 정적 비교에서 MOV의 local14~16 상대 머리 roll은 원본 방향·순서에 가까웠고 STILL은 초기 자세에 가까웠다. 정밀 앞발/접촉은 UNCERTAIN, temporal UNVERIFIED, Lab 전이는 NOT_RUN이다. 조건4변경/12bit-exact, sampler2/2 소진, 실패·재시도0. 공개 기록과 비공개 검토 자료를 마무리하며 추가 실행하지 않는다.
