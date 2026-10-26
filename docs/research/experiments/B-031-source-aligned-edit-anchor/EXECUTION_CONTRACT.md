# B-031 실행 고정 계약

2026-10-26 사용자 수행 지시로 기존 PLAN의 다운로드·설치·추론 범위가 승인됐다. PLAN의 PROPOSED 문구는 계획 등록 당시 상태이며 삭제하지 않는다. 시작 원격 HEAD는 `9ca7606a5c230a1af0a946fa05a2eb9384713def`다.

시작 UTC14:46:41, hard deadline20:46:41, 마지막30분 보존·종료용이다. 준비 목표60분. 종료/전송도 상한에 포함하고 자동 연장하지 않는다.

- 기존 B027 animal/human/vehicle R1/R2 총6개; source 첫 프레임 전체, target 원천GTbbox에 폭/높이10%를 각 변에 추가하고 imagebounds에서 clip. target support 밖128. 좋은crop 사후선택 없음.
- Qwen-Image-Edit-2511 한 모델, 가중치 신규70GiB 이하, 별도venv/lock; 기존 환경과 원본 불변.
- 이미지1=source, 이미지2=target. 출력896×512, BF16,40step,trueCFG4,guidance1,negative 단일공백,seed20261026. 지원인자/실제전처리/버전은 실행 전 고정한다.
- 각 case1attempt, 최대6. sourcepose/방향/위치/카메라와 보호장면을 유지하는 같은tasktemplate. 외형반영·자세/위치·형태·장면은 각각 판정하고 source-copy/recolor는 성공이 아니다.
- 영상은 사전R1만, 정적 적합성 부족이면 ANCHOR_UNSUITABLE. R2대체 없음. 실제A0support를CPU수동준비(총30분), 밖128/RED-BLACK. A0는GT아님, 영상첫프레임clamp/합성 없음.
- Qwen process 종료·자원회복 후 SCAIL. B027 R1 driving/text/noise/RNG/scheduler 재사용; reference VAE/CLIP/mask만 인코딩. replacement,40step80forward,17frame preview24fps. source_fps=null/timebase_assumed=true.
- SCAIL 최대3sampler/decode각1, final latent 우선저장. 학습·추가모델·외부생성·imagegen·재시도0. LoRA/ALG/B029gate/manualRoPE OFF.
- 기존72GiB 시작/24GiB headroom/swap0, 타서비스보호. CPU/GPU회계를합산하지않는다.

전체6개와 실패를 보존하고 R1적합subset만으로 성공률을 만들지 않는다. 실제연속시청이없으면 temporalUNVERIFIED. full/compact분리, MP4재인코딩없음. compact에없는raw/latent까지검증했다고하지않는다. 각호스트실제ZIP/CRC/extract/payloadSHA/전송동일성을확인한다.
