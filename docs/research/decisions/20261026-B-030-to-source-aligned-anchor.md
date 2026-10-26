# 2026-10-26 — B-030 해석과 자동 원본 자세 정렬 앵커 후보

## 확인한 결과와 범위

기준 결과 commit: `0e9af12e3daf28df418ba60726b847e6e941fa81`.

B-030 결과 보고서를 원격으로 읽었다. 사람의 큰 치마 부피/높이는 VAE+mask 행을 일부 따르지만 세부 손상은 열과 조합에도 의존했다. 차량의 추가 그림은 Y11에만 있고 네 셀 모두 source형 차체를 유지했다. 이는 제한된 조건부 의존과 상호작용의 관측이지 VAE=pose / CLIP=identity라는 분리가 아니다. 시간 품질은 UNVERIFIED이며 3시간 전체 상한 초과도 보존한다.

이번 검토에서는 첨부 compact ZIP에 대해 container와 Python을 각각 시도했으나 두 실행 서비스가 ClientError를 반환했다. 따라서 미디어/ZIP을 독립 검증하거나 실제 연속 재생을 시청했다고 하지 않는다. 원격 결과·공식 구현·원문헌에 근거해 다음 후보를 제안한다.

## 결정

이 결과만으로 reference joint-attention의 새로운 gate·계수·층·위치 변환을 정하지 않는다. 기존 실험에서 특정 경로가 원인으로 식별됐다는 해석은 유지하지 않는다. B-028/B-029의 NOT_ADOPTED와 B-030 PARTIAL/INCONCLUSIVE는 그대로 둔다.

다음 제안은 [B-031 PLAN](../experiments/B-031-source-aligned-edit-anchor/PLAN.md)이다. 원본 첫 프레임과 임의 target reference를 로컬 다중 이미지 편집기에 주어 target 외형+source 자세의 편집 이미지를 먼저 만들고, 그 foreground를 기존 SCAIL replacement 참조로 사용하는 분해형 기준선이다. 사용자가 서 있는 사진을 추가로 제공할 필요가 없도록 시스템이 중간 표현을 생성한다.

공식 SCAIL 논문 §3.2의 합성 데이터 reference 준비에도 source 첫 프레임의 자세 조건을 활용하는 과정이 있다. 이 사실은 이번 방법을 검토할 근거이지 성능/최적성 증거나 새 아이디어라는 뜻은 아니다. VideoPainter의 편집 첫 프레임→영상 전파도 관련 선행 설계지만 이번에는 새 영상 backend를 추가하지 않는다.

Qwen-Image-Edit-2511 공식 card의 두 이미지 입력과 공개 safetensors를 확인했다. 아직 Spark에서 실행하지 않았으며 공식 파일 크기와 실행 peak 메모리를 혼동하지 않는다. 해당 모델 하나의 추가 다운로드/격리 환경 설치는 기존 설치0 실험과 다른 신규 범위다. 계획을 전달받고 사용자가 실행을 지시하기 전에는 다운로드하지 않는다.

## 계획 상태와 예산 제안

상태: PROPOSED / NOT_RUN. 이미지 생성 최대6회(기존 공개3과제×2참조), 신규 SCAIL 영상 최대3회(각과제 사전선택R1 앵커가 적합할 때만), 학습0. 신규 이미지 모델1종·다운로드70GiB 상한·격리의존성설치 허용을 제안한다. 새 VideoPainter/FLUX/추가LoRA는0. 실패 앵커를 숨기거나R2로사후교체하지않으며전체6개분모와end-to-end비용을보존한다.

A0는생성결과이지GT나oracle이아니다. A0가좋아도영상이잘나온다는보장은없다. 이를실제영상frame0에덮어붙이거나관측되지않은시간품질을PASS로하지않는다. 새모델을연결하는것자체는연구신규성이아니다. 중간실패위치를분리하고작동하는task-alignedbaseline을얻는것이이번범위다.

문서작성중신규GPU·학습·다운로드·환경변경은0. 계획문서만추가하고기존코드/weights/결과/실패를변경하지않는다. 실행자는착수/종료시HISTORY·ROADMAP에이결정을연결하며,전체상한에는문서화/압축/전송시간도포함한다.

## 공식 근거

- SCAIL-2 v3 §3.2: https://arxiv.org/html/2606.10804v3
- Qwen-Image-Edit-2511 공식 model card: https://huggingface.co/Qwen/Qwen-Image-Edit-2511
- VideoPainter 고정 편집 구현: https://github.com/TencentARC/VideoPainter/blob/bbab6cd5cd5cb89f0e2444305c32fd74a010ae0a/infer/edit.py
