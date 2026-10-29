# C-003 사전 고정 — 같은 윤곽에서 내부 시간 정보

작성: 2026-10-29 KST. 부모 C-002 `853ee952795246648b3a6e46d37d5dead03abef3`. C 트랙 기존 branch/worktree를 이어 쓰며 과거 결과와 A/B 환경을 보존한다.

질문은 같은 동적 외곽선·양끝 앵커에서 source의 시점별 내부 구조선이 머리·앞다리 진행에 도움이 되는가다. 개 사례 한 구간·한 seed의 표현 기준선이며 관절 정답·순수 motion·체형 전이 모듈이 아니다.

## 입력과 순서

C-001 dog33 무손실 source, dog-gooses 참조, native 앵커2장, 기존 selected SAM visible33와 C-002 실제 layout33을 재사용한다. OUTLINE_ONLY는 C-002 개 MOV 출력이며 재생성하지 않는다. 신규 순서는 INTERNAL_DYNAMIC → INTERNAL_HOLD다. 첫 출력 품질 때문에 두 번째를 생략하지 않는다.

832×480,33frames,source_fps=null,preview_fps16,timebase_assumed=true. 파일 길이33/16초와 양끝 표본간격32/16초를 구분한다. 모든 기존 prompt/negative/checkpoint/installed pipeline/Euler50/CFG5/shift5/seed20261028/CPU RNG/BF16/SDPA/tiled/scale1.0을 유지한다.

## 표현과 불변 조건

공식 VACE pinned `48eb44f1c4be87cc65a98bff985a26976841e9f3` scribble 한 종, FP32/eval/inference_mode/strict weights_only load. 기존 로컬 weight가 없을 때 공식 배포의 한 파일 ≤64MiB만 허용한다. Source full-frame33을 완료된 pass1회로 추출하고 캐시한다. 실제 revision/hash/polarity를 영상 생성 전에 고정한다.

S=기존 SAM 영역, L=기존 외곽선, J=흰 바탕의 grayscale 구조, I=(정확 Euclidean 내부거리>4px)&(L==255), G=기존 생성 마스크다. 두 조건은 같은 bbox pixel-center 정규화256×256와 bilinear 왕복을 쓰며 영역 mask는 nearest다. DYNAMIC은 각 시점 내부 구조, HOLD는 첫 프레임 정규화 내부 구조를 현재 bbox로 이동/확대한다. I 밖은 L pixel-exact, 중간 grayscale3채널, 양끝 앵커/G/reference=None 불변이다. 세부 좌표 규약과 실제 hash는 METHOD/CONDITIONS에 고정한다.

## 평가 고정

생성 전 source/앵커/OUTLINE을 실제 보고 0/4/8/12/16/20/24/28/32의 머리 방향·높이, 보이는 코/귀/앞다리, 화면상 발의 전후 배치, 접근/크기, 가림, 종료 앵커 충돌을 OBSERVED/OCCLUDED/AMBIGUOUS로 기록한다. 주석은20분 이내. 결과 전체33장과 같은 고정 인덱스 및29–32를 비교한다. 머리·다리 진행, 전체 이동, target 외형, 보호 장면, 형태, 비용을 분리한다. 가려진 관절이나 낮은 발끝을 접촉 GT로 보지 않는다.

USEFUL_INTERNAL_GAIN/COARSE_GAIN_ONLY/APPEARANCE_ONLY/TRADE_OFF/NO_ESTABLISHED_GAIN/WORSE/INCONCLUSIVE 중 근거에 맞게 판정한다. 실제 연속 지각 검수 없으면 temporal=UNVERIFIED. Hash 차이는 전달 증거이며 품질 증거가 아니다. 선 밀도/질감/가림/보간/clipping/앵커 충돌이 함께 달라져 순수 관절 시간정보 인과효과로 해석하지 않는다.

## 예산과 종료

영상 정상2×50step/100call, heavy 최대3(기계적 예비1), 품질재시도0. 저장 latent 뒤 VAE-only 복구 전체최대1; sampler 반복 금지. Imagegen/SAM/학습/새패키지/다른모델/추가사례/후합성0. 기존 C-001/C-002 guard/adapter/절대경로/공통lock/한도를 그대로 쓴다. 안전 중단은 자동재시도/완화하지 않는다. 구조 추출과 VACE는 순차 실행한다.

전체3시간·마지막20분 전달, 조건 구현목표45분. 유효한 조건이면 두 실제 영상까지 실행한다. 내부정보가 전부 없거나 오류로 양 조건이 같으면 구체적으로 중단한다. 추가 탐색은 하지 않는다. 공개에는 비민감 code/docs/hash만, 실제 미디어/raw/latent/weight/개인경로는 비공개 보존한다. Spark/Mac /tmp compact의 CRC/hash/manifest/추출/전송동일성을 확인한다.
