# 생성 전 Lab task prompt 고정

2026-10-24 KST, 신규 GPU 실행 전 고정. 두 Lab 조건은 아래 문자열을 완전히 동일하게 사용한다. negative는 빈 문자열이며 enhancer는 OFF다.

> A broad-chested black Labrador retriever with short black fur, floppy ears, a broad muzzle, and sturdy limbs stands upright on its hind legs in the room shown in the reference photo. Its front paws hang bent in front of its chest as it gently leans and progressively tilts its head to the side near the end, while the torso remains facing the camera. Preserve the same Labrador appearance, room, full-body framing, and the observed sequence of movement.

B-012의 `small cream-colored short-haired dog`를 실제 Lab 사진의 검은 털·넓은 가슴·접힌 귀·넓은 주둥이·굵은 사지에 맞췄다. 밝은 스튜디오/반사 바닥 대신 reference의 방으로 장면 지시를 바꿨다. animation이며 침실 유지 자체는 실패가 아니다. 뒷발 직립·굽힌 앞발·후반 머리 기울임·전면 몸통·전신 framing이라는 B-012 동작/카메라 지시는 유지했다. 새로운 킥·윙크·입 닫힘·3D 회전 조건은 추가하지 않았다.

실제 사진은 침대 위 착석 자세다. 이를 편집하거나 가리지 않는다. 그 자세와 생성 목표의 차이는 이번 전신 전이 과제의 핵심이며, 원본/source row와 Lab row의 차이는 identity 하나만의 개입이 아니다. reference/task 묶음의 차이를 명시한다. 실제 T5 token length와 hash는 양 P에서 기록하며 결과 후 prompt를 바꾸지 않는다.
