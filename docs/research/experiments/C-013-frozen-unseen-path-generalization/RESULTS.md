# C-013: 제한된 새 경로 제어 확인, 전체 품질 보존은 미달

검토 ZIP의 `index.html`에서 새 네 실제 영상, 부모 A/B, seed2 BASE/ON을 비교한다. 원 MP4·전33PNG를 제공한다. 위치 판정: **SAME_SCENE_INTERPOLATION_SUPPORTED / NEW_PATH_SHAPE_SUPPORTED**. 외형·배경까지 포함한 전체 품질 성공은 아니다. temporal=UNVERIFIED.

|경로|t16 요청 (x,y)|실측 (x,y)|주시점 평균 오차 px|중앙 E_req px|중앙 E_mem px|
|---|---|---|---:|---:|---:|
|I25|(208,96)|(207,99)|2.212|2.905|19.252|
|I50|(208,120)|(211,117)|2.174|2.909|34.062|
|I75|(208,144)|(206,142)|1.467|2.052|18.434|
|S|(208,120)|(207,122)|2.859|3.684|17.053|

## 일곱 질문에 대한 답
1. 보간 가운데 y는 실제99/117/142로 움직였다. 목표96/120/144의 사전 허용오차 안이다. 핵심5시점 모두 순서·최소간격 통과. t16 간격18/25px는 최소12px 이상이다.
2. 네 경로 모두 E_req+4≤E_mem을 만족한다. 이번 출력은 학습 A/B보다 새 요청에 가깝다. 내부의 암기 메커니즘이나 임의 좌표 전체의 연속성 증명은 아니다.
3. S의 t8/12/16/20/24 실측 y=140/145/122/93/92. 아래→가운데→위 순서를 따랐다. 전33프레임 detector는 모두 단일 객체 정상, 핵심 누락·중복0이다.
4. 무늬·형태·배경의 완전한 보존은 아니다. 주9시점 시각 검토에서 공은 식별되지만 I25/I75에는 윤곽 잔상·무늬 변화, S에는 더 두드러진 흐림·투명한 겹친 윤곽과 띠/반점 변형이 있다. I50도 미세한 윤곽/배경 변화가 남는다. 별도의 두 공이나 녹색 잔해는 이 표본에서 보이지 않았다. 전33프레임 시각적 무결성으로 확대하지 않는다.
5. seed2 BASE부터 큰 색 블록·줄무늬와 장면 붕괴가 나타났다: **BASE_FAILURE_PRESENT**.
6. ON은 공과 경로를 더 식별 가능하게 만들고 배경 평균 오차를 낮췄지만, 모자이크 같은 배경 변형은 남았고 손상 형태도 바뀌었다: **MIXED_BASE_ADAPTER_EFFECT**. BASE 실패가 adapter 무영향을 뜻하지 않는다.
7. 확인 범위는 같은 공·장면·양끝·동결2048 adapter·고정 seed1의 세 보간 및 한 S 경로다. 범용 편집/동물/가림/속도/seed 분포 일반화 근거가 아니다. 다음에 바꿀 요소 하나는 **보호 배경 보존 제약**이며, 이번에는 제안만 하고 추가 실험을 시작하지 않았다.

## seed2 matched 배경 비교
공통 ROI는 학습 A/B와 새 네 경로 mask 합집합의8px 팽창 바깥69,231픽셀이다. 아래는 전33프레임 지표의 평균이다. p95는 프레임별 절대 RGB 채널 차이 p95의 평균, >25는 픽셀별 평균 RGB 차이>25 비율이다.25는 품질 합격선이 아니다.

|출력|원 배경 대비 RGB MAE|p95|>25 픽셀 비율|
|---|---:|---:|---:|
|BASE_S2|40.868|101.515|58.13%|
|ON2048_S2_A|18.582|43.697|26.05%|
|ON2048_S2_B|23.484|54.121|38.48%|

BASE와 ON 자체의 ROI 차이도 MAE30.000(A)/29.523(B), >25 비율41.46%/41.51%로 크다. 입력 noise/context/text/앵커/계산 설정은 양쪽 ON과 exact 대조했다. 표식의 peak·dx/dy·raw median은 METRICS에 보존했으며 변형된 표식 위치를 카메라 이동 거리로 단정하지 않는다. 새 seed1 네 출력의 배경 MAE는4.722–5.315다.

## 실행과 검증
5 sampler,250 scheduler steps,250 model_fn calls. 모든 실제 parity와10개 CPU/heavy stage 정상 종료 확인. 학습/backward/추가 probe/target·patch encode/설치/다운로드/품질·기계 재시도0. 조건 VAE encode10, 생성 decode5는 기존 정상 live 경로의 횟수다. raw/latent는 Spark 비공개 원위치에 보존한다.

생성 전 Spark 연구 Python의 renderer/template fixture PASS: 새4정답 최대 중심오차0.654px 미만, 빈 배경 missing·두 공 duplicate·이동 배경·A/B 반례 확인. 전체화면 탐색과 기존 임계값 유지. 브라우저375/768/1280px,3탭,slider,실제 재생 기술 검사 PASS. 연속 지각 검수 및 독립 human 평가는 하지 않았으므로 temporal=UNVERIFIED. lint/typecheck 도구는 미설치로 NOT_RUN; Python syntax/기하/정책/fixture/실제출력 검사는 수행했다.

## 안전 정책과 과거 기록
8a5cc37의 BLOCKED_SAFETY는 historical-attempt01 및 RUNS.historical_attempt에 그대로 보존한다. 승인된40cf524 이후 C-013 전용 사본의 swap 총량 시작 차단 두 줄만 제거했다. 원 swap 경고와 나머지 보호는 유지했다. 새 live 관측10.272초에서 swap247,238,656bytes, 증가0/swapout0/PSI0, 가용약121.25GB였으며 짧은 초기 구간은 INCOMPLETE로 유지했다. CPU/heavy 모두 같은 guard freeze를 검증했다. 공통 정책/서비스/타 프로세스는 변경하지 않았다. C-012의 SEED_SENSITIVE_CAPABILITY도 유지한다.
