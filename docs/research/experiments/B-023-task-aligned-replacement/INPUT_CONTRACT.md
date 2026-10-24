# B-023 입력과 평가 사전 계약

B-020의 허용된 실제 Lab 자연동작과 앉은 같은 개체 reference를 재사용한다. [사전 입력 확정](../B-020-real-fm-tail-overfit/INPUT_AMENDMENT.md), [EditSpec](EDIT_SPEC.json). source와 reference가 같은 개체라는 판단은 기존 사용자 확인에 근거한다.

## 변경과 보존

| 입력/경로 | B020 미학습 기준선 | B023 | 확인 방식 |
|---|---|---|---|
| reference RGB/CLIP/VAE | 기존 사진·letterbox | 그대로 | 파일/캐시 실제 해시 |
| reference semantic mask | RED+WHITE | 같은 RED+BLACK | RED37209픽셀 보존, WHITE421543픽셀만 변경 |
| driving RGB·mask | 실제17장, RED+WHITE | 그대로 | 전체17장 실제색·파일·조건 해시 |
| 양CFG mode | replace_flag=False | True | 실제 forward 인자와 공식 위치 설정 trace |
| caption/negative | B020 실제값/empty | 그대로 | config와 text 조건 |
| noise/RNG/scheduler | 실제B020 저장물 | 그대로 | 실제 tensor·state hash |
| adapter/ALG/manual RoPE | OFF/OFF/OFF | OFF/OFF/OFF | vanilla projection·실행 코드 확인 |

reference의 WHITE에는 사진 밖 letterbox도 포함한다. BLACK 의미 마스크로 바꿔도 reference RGB의 흰 padding이나 침실 픽셀은 그대로다. 새로운 segmentation·boundary 보정·RGB alpha masking은 하지 않는다. 저장된 driving 마스크는17장 모두 RED/WHITE 두 색이며 얇은 경계·안쪽 뒷다리 support의 기존 PARTIAL은 남긴다.

공식 helper를 CPU에서 호출해 원래 WHITE 조건과 기존 캐시의 exact parity를 먼저 검사하고 BLACK 파생 조건을 만든다. 바뀔 tensor는 양 CFG reference mask 2개이며, 나머지14개 tensor leaf와 초기noise/RNG/scheduler는 유지한다. mode bool은 tensor leaf 수에 포함되지 않는다. 실제 검증 결과는 별도 receipt에 남긴다.

## 시간·공간

원본 SHA256 `d286f6e25990080fe87b6903cdbcf8e30f89b0f367bd066f8e346d959fff31b0`. f126..142 inclusive, PTS4.2..4.733333초. 기존1920×1080→896×504 resize와 위/아래4px letterbox를 재사용한다. 17장·30fps, 표본간격16/30초와 파일지속시간17/30초를 구분한다. reference를 source 자세로 warp하지 않는다.

## 기준선의 정체

B020 BASE_S의 adapter-selection은 enabled=false/sha256=null이며 raw baseline SHA256은 `50579b6aa7739de4d4b65d959255d1ba71c980248ad7f52fd91e26ea0dc9d00e`다. B022의 학습된20/100회 결과는 주요 미학습 대조군이 아니다. baseline 재생성은0회다.

## 결과 전에 고정한 관측

전체17장 및 local0/8/16에서 사족 서기, 후반 화면 왼쪽 고개 전환 방향·순서, 얼굴/귀/목 손상과 잘림, 원본 타일바닥·창가·배치, 참조침실/padding 복사, 실제 개체·체형을 따로 판정한다. 원본의 사족 자세와 후반 머리 방향 변화는 입력 시트에서 확인했지만 가려진 발 접촉·정밀각도는 UNCERTAIN이다.

raw RGB 생성 결과만 비교한다. 좋은 프레임 선별·후처리·시간 맞춤·ROI 원본 복원은0이다. 의미 마스크 가시성은 raw pixel 보존 보증이 아니다. 같은 개체이므로 source-copy가 좋은 점수를 받을 수 있으며 reference 활용·cross-ID 교체·일반화는 이번에 식별하지 못한다. 실제 연속 시청이 없으면 temporal=UNVERIFIED다.
