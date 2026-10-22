# B-002 결과 — 참조 배경은 바뀌었지만 착석 자세는 남았다

상태: **COMPLETED (통제 비교)**. 신규 추론 **5/5 완료**, 실패 **0**, 재사용 **1**, 계획된 6개 셀의 미실행 **0**. 신규 학습 **0 optimizer update**, adapter=null. **실제 Lab 개체·춤 전이 성공은 수용하지 않으며 시간 품질은 UNVERIFIED**다.

## 질문과 실행 근거

같은 모델·원본 구조·텍스트·mask·초기 noise에서 Lab 참조 사진의 배경만 흰색으로 바꾸면 출력 배경과 자세가 어떻게 달라지는지 비교했다. 원래 [PLAN revision 1](PLAN.md)을 유지했다. 결과를 본 뒤 prompt, seed, scale, 마스크 또는 sampling을 변경하지 않았으며 실패 재시도도 없었다.

사전 계획은 `2a1bcc4eceb7a1f461c843ee71445b53ffb98493`, 실제 실행 코드·재사용 근거는 `9d81447919469c2cdeda69a9d7da25515a5b55f0`에서 push와 원격 SHA 일치를 확인한 뒤 실행했다. 현재 공개 코드의 후속 변경은 import 정렬이며, 실제 실행 파일은 해당 commit과 private 원본에 보존했다. [style 검증](code/style_verification.json)의 import binding/나머지 AST 비교는 실행 동등성의 모든 경우를 증명하는 테스트는 아니다.

- 고정 upstream `f39d731a3e318d25b725eb3389cfddb184619842`, model revision `574e6a744642ce3bee319afc31496b88bde8aac4`.
- Spark GB10, aarch64, driver580.126.09, Python3.12.3, PyTorch2.14.0+cu130/CUDA13.0. BF16, SDPA, offload 없음, adapter 없음.
- source f0~16, Canny70/150, video mask 전체 흰색,512×288,17프레임,24fps,20steps,CFG5,vace_scale1,sigma_shift5. [고정 설정](resolved_design.json), [실제 요약](run_summary.json).
- 새 실행의 실제 noise `(1,16,6,36,64)`와 positive/negative text `(1,512,4096)` 해시는 같은 seed의 조건 사이에서 일치했다. text 해시는 두 seed에서도 같았다. reference가 달라지면 VACE context `(1,96,6,36,64)`의 해시는 달라졌고 같은 reference는 두 seed에서 같았다.
- 기존 R/20261022는 source/edge17장 RGB, padded reference, sampler 호출, 실제 모델9파일 및 핵심 upstream5파일과 저장 noise를 대조해 재사용했다. **이전 text tensor hash는 미기록**이며 이전 noise는 동일 initializer로 별도 생성한 기록이다. 과거 sampler 내부 텐서를 새로 관측했다고 주장하지 않는다. 실행 후 검사 중 parameter_counts_unchanged는 개수 비교이며 가중치 값 전체를 비교한 검사가 아니다. [재사용 감사](reuse_audit.json).

## 참조 개입이 유지한 것

원본1536×2048 RGB를 같은 decoder 방향으로 읽고 수동 윤곽과 비학습 GrabCut으로 배경만 RGB255로 대체했다. alpha는0/1이며 유지한 전경 **595,340픽셀의 RGB가 원본과 정확히 같다**. Lab의 위치·크기·앉은 자세를 바꾸지 않았다. 귀·혀·가슴·양 앞발과 다리 사이 침구 제거를 정적 비교 시트에서 확인했다.

마스크 경계에는 수동 관측 오차가 남을 수 있다. hard alpha이므로 soft feathering은 없지만 resize filter가 전경 경계를 배경과 혼합한다. 원본과 R-bg 모두 동일한 gray128 padding을 사용한다. 모든 모델 입력 경계 픽셀이 같다고 주장하지 않는다. 최종 CPU 마스크 처리2.251초; 수동 작업 시간은 NOT_MEASURED. [공개 계보 요약](reference_preparation.json). 개인 사진·마스크·집 내부가 보이는 출력은 GitHub에 올리지 않았다.

## 정적 관측

먼저 조건 이름을 가린 시트의 f0/4/8/12/16을 읽고 관측을 기록한 뒤 대응표를 열었다. 과거 R을 이미 봤고 장면 내용으로 조건을 짐작할 수 있어 진정한 인간 블라인드 실험은 아니다. 이어 R-bg/P의 f8 원본512×288 프레임을 확대 없이 확인했다. **연속 재생을 직접 관찰하지 못했다.** 아래 표는 정적 시각 관측이며 수치 품질 점수나 전체 동작 정확도 판정이 아니다.

| 조건 | seed | 배경의 구체적 특징 | 자세·형상·개체 관측 |
|---|---|---|---|
| R (재사용) | 20261022 | 침대, 커튼, 창/방 배치를 재현. 일부 색 번짐/광택 경계 | 검은 개가 앉아 있음. 원본의 직립 자세가 아님 |
| R-bg | 20261022 | 밝은 벽·문 쪽 배경. 참조의 침대/커튼/창 배치는 보이지 않음 | 착석 유지. 뒷다리가 화면 오른쪽으로 벌어지고 목·가슴에 강한 은빛 광택. 사진 개체의 정확한 외형 수용 불가 |
| P | 20261022 | 단순 밝은 실내·문 | 뒷발 직립/앞발 듦. 긴 주둥이와 눈·체형이 실제 Lab와 다름 |
| R | 20261023 | 침대/커튼/창 배치와 좁은 중앙 영상·빈 측면 패널 | 참조와 비슷한 착석. 원본 직립 동작은 아님 |
| R-bg | 20261023 | 베이지 벽·걸레받이·바닥. 침실 배치가 사라짐 | 착석 유지. 사진보다 가는 가슴/몸통, 밝은 가슴 무늬가 나타남 |
| P | 20261023 | 원본에 가까운 단순 스튜디오 배경 | 직립하지만 긴 털 꼬리·배 쪽 갈색 털, 다른 얼굴/체형. Lab 개체 일치 아님 |

두 seed 모두 **참조 배경의 구체적 복사는 줄었고 착석은 남았다**. 이는 이 입력 개입의 반복 관측이지 모든 배경·개체에 대한 평균 효과나 모델 내부의 독립 배경 채널 증거가 아니다. R-bg의 대비·입력 분포도 바뀌었으므로 외형 변화까지 전혀 없는 순수 semantic 분리를 했다고 볼 수 없다.

P는 같은 Canny에서도 reference를 원본 첫 프레임으로 바꾸자 직립 결과를 만들었다. 그러나 P의 reference 개체와 검은 Lab prompt가 충돌하며, reference 자체에도 직립 자세가 있다. 따라서 **순수한 동일 개체 복원 positive control이 아니며, P의 직립만으로 Canny의 동작 전달 효과를 분리할 수 없다**. 원본 전체 motion 대응·발 위치 정확도·실제 개체 유지도 승인하지 않는다.

source는 짧은 직립 움직임 구간이다. R-bg의 낮은 프레임 변화량이나 안정된 착석을 좋은 춤 전이로 취급하지 않았다. 배경·바닥 그림자/반사 일치도 별도로 수용하지 않는다. 인코딩/decoded frame 수 검사는 시간 품질 관찰과 다르다.

## 실행 시간과 자원

| 새 run | process초 | pipeline초 | 40 model forward 합계초 |
|---|---:|---:|---:|
| R-bg/20261022 |120.08|44.11|37.11|
| P/20261022 |100.07|40.86|34.31|
| R/20261023 |82.06|38.88|32.41|
| R-bg/20261023 |86.07|39.50|32.96|
| P/20261023 |88.05|38.77|32.45|

process는 guard가 관측한 child 전체 시간, pipeline은 전처리·decode 포함, model 시간은 CUDA sync를 포함한 actual model_fn40회 합계다. loading·hook I/O·cache warm-up 차이 때문에 독립 속도 벤치마크로 해석하지 않는다. 총 새 child 실행 시간은 약476.33초다.

모든 새 run의 CUDA allocated peak **17,056,366,080 bytes (15.89GiB)**, reserved peak **17,687,379,968 bytes (16.47GiB)**. OS MemAvailable 최솟값 **64,743,706,624 bytes (60.30GiB)**, swap0. 통합 메모리에 CUDA와 CPU 메모리를 별도 총량으로 더하지 않았다. 동시에 무거운 작업 하나만 실행했고 기존 ComfyUI 큐는 비어 있었으며 그 프로세스를 종료하지 않았다.

모든 출력과 비교 영상은17프레임/24fps, container0.708333초다. 마지막 sample시각은16/24=0.666667초다. 프레임 복제·보간·업스케일·후처리 복원·속도 변경을 쓰지 않았다. 영상은 자동 loop의 끝→처음 점프와 내부 변화를 구분해서 검토해야 한다.

## 남은 불확실성과 다음 한 가지

- 정확한 Lab 개체 유지, 직립 동작 전이, 자연스러운 사지/목·시간 품질은 미수용이다. 두 seed와 한 참조/한 source만 관측했다.
- 재사용 첫 R의 과거 text tensor를 직접 비교하지 못했다. 새 seed의 R/R-bg/P는 실제 tensor hash로 통제했다.
- A와 신규 학습/새 모델은 실행하지 않았다. 전체 제작·IG·윙크·발차기·Kling 수용은 NOT_RUN이다.

**다음 실험 하나:** R-bg·prompt·mask·noise를 고정하고 구조 입력 S만 **현재 Canny vs 같은 크기의 무정보 검정 Canny**로 비교한다. 현재 착석 결과에서 Canny가 어떤 관측 가능한 변화를 일으키는지 분리하는 질문이다. reference 내용과 구조 scale을 동시에 바꾸지 않는다. 차이가 작아도 즉시 경로 고장/모델 무능력을 결론내리지 않는다. 이번에는 실행하지 않았다.

## 자료

[수학·코드·결과 연결](../../lessons/B-002-conditioning.md), [질문](QUESTIONS_KO.md), [별도 해설](ANSWERS_KO.md), [재현 경계](REPRODUCE.md), [실행 요약/해시](run_summary.json).

비공개 검토 ZIP에는 모든 여섯 조건의 출력, 원본/condition, 참조/마스크, 같은 시간축 비교 영상, 실제 config/장부/로그 요약·재현 코드를 포함한다. ZIP 자체와 이미지는 공개 GitHub에 올리지 않는다. ZIP 무결성·호스트 위치·최종 동기화 SHA는 전달 보고에서 별도로 확인한다.

## 코드 검증의 별도 한계

실제 실행·입력·해시·인코딩 검증은 통과했고 공개 스크립트의 문법/ruff 검사는 통과했다. **Mac strict basedpyright 검사는 NOT_PASS (326 diagnostics)**다. 로컬 torch/upstream import 부재뿐 아니라 연구용 스크립트의 불완전한 annotation과 혼합 JSON 타입 추론 문제도 있다. 진단을 끄지 않았고 제품 수준 타입 검증 완료로 보고하지 않는다. [요약](static_typecheck_summary.json). 이번 통제 실험의 실행 코드와 결과를 보존하며 이를 이유로 새 추론이나 큰 코드 재작성을 하지 않았다.
