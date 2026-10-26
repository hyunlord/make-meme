# B-029 runtime 연결과 보존 범위

B-027 전체6case를 공통 기준선으로 읽기 전용 재사용한다. B-028의 정규화 reference/cache는 사용하지 않는다. 새 task 아래 METHOD(R1/R2), animal/vehicle CONTROL(R1)를 분리하며 모든 case는 PROBE→S→D 순서다. ENC 단계 자체가 없다.

`contracts.verify_producer_cache_receipt`는 기존 B-027 validator 본문을 보존한다. 원래 producer worker의 receipt·code manifest·pair·noise·config를 먼저 검증한다. 그 뒤 새 `verify_cache_receipt`는 producer receipt와 원래 code manifest의 고정 해시, 소비 cache3개 및 receipt 파일의 byte equality, 실제16leaf metadata, unchanged public config를 확인한다. B-029 consumer code와 B-027 producer code의 해시가 다르다는 이유로 provenance gate를 제거하지 않는다.

`extract.py`, `staged_loader.py`, `cuda_probe.py`, `phase_decode.py`, `artifacts.py`는 B-027/B-025와 byte-identical이다. 새 S는 모델 적재·eval 뒤 gate를 설치하며 기존 cache 복원·모델 이동·tiny CUDA 순서를 유지한다. 각 block의 실제 metadata로 generated 구간을 식별한다. 관측용 추가 forward는 없다.

Sampler 실제40step·80forward, 모든40block의 gate 호출80회씩을 완료 전에 검사한다. final latent provenance는 consumer B-029와 producer B-027을 구분하며 variant·gate 보고·config·condition hash를 보존한다. D는 B-029 provenance와40/80, config·condition SHA를 확인한다. decoder 연산은 변경하지 않는다.

새 `spatial_gate.json`/`execution.json`은 소비 실행 설정이며 원래 cache 내부 config를 고치지 않는다. 코드·단계별 config·producer binding·support tensor/metadata를 실행 전에 고정한다. METHOD와 CONTROL 모두 같은 lambda0.5를 쓰며 CONTROL은 동일 지도를 이동할 뿐이다.

기존 시작72GiB/실행24GiB/swap0 정책, 타 서비스 보호, 순차 fresh worker를 유지한다. deadline은 전체 의뢰의 2026-10-26 09:37 UTC다. stage 중복 attempt는 exclusive-create로 거부한다. 최대8sampler·8decode·8probe, 재시도0. 코드/fixture 성공은 영상 품질 성공이 아니다.
