# 단일 변경과 실제 조건 경로

C002 `video_generate.py`를 수정 없이 재사용한다. 원래 config와의 차이는 `end_anchor`와 `output`이며, 생략된 기본값을 확장한 effective model settings도 동일하다. 실행 adapter는 C001 원본, guard는 C003 명시적 amendment 뒤 실제 성공한 버전이다. 별도 launcher/supervisor·안전 정책을 만들지 않았다.

Native imagegen 입력은 source local32, C001 실제 사용 target crop, 원래 raw 시작 앵커 세 장이다. 기존 끝은 비교에만 사용했다. 출력 한 후보를 aspect-fit LANCZOS/blackcanvas로832×480에 맞췄다. 자세 warp/수동 편집/배경 후합성은 없다. 생성 전에 PARTIAL_BUT_USABLE 판정을 고정했다.

조건 X의0은 기존 시작,1..31은 기존 C002 동적 윤곽,32만 새 끝이다. G는 끝0/중간255 그대로다. 실제 CPU pixel hash에서0..31 동일/32 변경과 전체 G 동일을 확인했다. 정규화 후 inactive의 끝 입력만 달라지고 reactive는 같다. 시간 VAE/Transformer의 내부 영향 범위가 끝 하나로 제한된다고 가정하지 않는다.

최초 원래 model_fn 직전 noise/context/mask64를 읽는 기존 hook을 사용하고 추가 forward나 RNG 조작을 하지 않았다. Euler50/CFG5/shift5/seed20261028/CPU noise/BF16/SDPA/tiledVAE/scale1.0과 기존 checkpoint·prompt를 유지한다.33→9 마스크 압축에서 끝0이 빠지는 한계도 그대로다.

최종 latent를 원자 저장/readback 후 raw/PNG33/MP4를 보존한다. 출력 끝을 앵커로 대체하지 않는다. 앵커 전체 변경의 효과로 해석하며, 새 얼굴·털·빛·배경 차이와 약한 자세 교정이 해석을 제한한다. 실제 관측·비용·수치는 RESULTS/NUMERICS/COSTS를 따른다.
