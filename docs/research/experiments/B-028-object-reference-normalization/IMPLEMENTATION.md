# B-028 사전 구현 고정

2026-10-26 UTC. B-028 전용 실행 폴더/장부/프로세스가 없음을 확인했다. 이번 실제 시작은 통합 의뢰서의 선행 B-028 실행이며 중복 생성이 아니다.

- `code/normalize.py`: q=0.8, bbox의 pixel-edge 중심, 역 affine를 Pillow에 전달한다. Pillow의 destination pixel center sampling을 사용한다. RGB bicubic/support nearest 후 support 밖128. 기존 RGB·support는 수정하지 않는다.
- `code/prepare_inputs.py`: B-027의 실제 masked RGB와 RED support에서 파생한다. driver RGB/mask는 원래 파일의 읽기 전용 링크다. `task_manifest.reference_normalization`에 현재 변환/해시를 추가하고 이전 `target_refs`는 역사 입력 계보로 보존한다.
- `code/phase_encode.py`: 각 과제 worker 한 번에서 VAE/CLIP만 로딩하고 R1/R2를 각각 한 번 인코딩한다. T5/source/target/DiT 인코딩은0이다. 각 대응 B-027 cache를 CPU로 읽고 양 CFG의 ref_latents/clip_fea/ref_masks만 교체한다. structure/device 계약과 나머지10leaf를 그대로 검증한다. 초기 noise 파일도 그대로 복사한다.
- S/D/PROBE/guard는 B-027의 검증된 실행 코드를 보존한 실험 사본이다. 변경은 B-028 식별자, deadline 2026-10-26T05:37Z, 새 reference encoder와 입력 준비뿐이다. 72GiB 시작/24GiB 실행/swap0/서비스 보호 기준은 동일하다.

CPU 새 검사3개: bbox 중심·균일 scale, mask/밖128·동일RGB 정렬, q가 identity가 되는 경우의 pixel-center 일치/원본불변. 기존 contract 검사4개도 그대로 통과했다. 이는 GPU·영상품질 검증이 아니다. 신규 도구 설치 없이 실행했고, 정적 타입 진단은 기존 inherited code에 대해 NOT_CLEAN/미실행 범위를 별도 유지한다.

새 sampler는3과제×2참조 최대6회, 각40step80forward, 각 final latent의 decode1회다. 첫 품질 실패 때문에 나머지 case를 생략하지 않는다. 입력/자원/유한값 오류라면 중단하며 재시도하지 않는다. B-028 결과를 보기 전에 후속 방법이나 기준선은 고르지 않는다.
