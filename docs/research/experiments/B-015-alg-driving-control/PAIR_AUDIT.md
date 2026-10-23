# B-015 actual cache pair audit

CPU actual16leaf 검사 PASS: 양 CFG의 pose_latents/driving_masks4개만 다르고 나머지12개는 shape/dtype/value bit-exact다. 전체 serialized structure/scalar/device metadata도 동일하다. GPU/P 실행 증거가 아니다.

새 filtered reference는 STILL cache를 parent로 기록하고 생성시각·원래MOV sidecarSHA를 연결했다. 원본reference와filtered 값은 각각 `0ad957276e89e5692743ee9d8438044fe37daa48500c311746ccd949e93703c0`, `40e6a0c2132cfc19f0a211a8cc654b21425e681b58cd45472656f3191454abda`이며 B014 실제tensor와 torch.equal PASS다. 원래MOV sidecar는 변경하지 않았다.

[PAIR_AUDIT.json](PAIR_AUDIT.json)은 실제 각leafSHA/shape/dtype/max_abs를 포함한다. configs/pair_audit.json이 실행 code manifest로 고정되며 각worker는 STILLcache/policy/newfilterfile·sidecarSHA를 다시 검증한 후 실행한다.
