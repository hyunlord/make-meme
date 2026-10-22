# B-007C 해설

1. 값은 storage와 `offset + Σ index × stride`로 결정된다. tensor의 key·dtype·shape·논리적 값 및 공식 mapping 순서는 같아야 한다. safetensors는 연속 배열로 저장하므로 원본의 view stride·storage 공유나 파일 전체 hash까지 같을 필요는 없다. 원본 불변 hash와 각 mapped tensor의 값 hash를 따로 확인한다.
2. 아니다. 정적 검사는 동적으로 만들어지는 dtype class를 놓칠 수 있다. 허용된 REDUCE/BUILD는 함수 호출이나 상태 복원을 수행한다. FakeTensorMode는 tensor storage materialization을 줄이지만 NumPy 등 비텐서 복원을 제거하지 않는다. scoped allowlist의 context도 OS sandbox가 아니며 프로세스 공용 상태에 영향을 준다.
3. 아니다. fixture는 그 작은 객체 graph와 정확한 버전의 배선을 확인한다. 실제 파일 provenance, top-level graph와 memo alias, storage references, shape/dtype/offset bounds, 허용할 정확한 함수·class, isolated resource policy, 원본 불변, mapping과 per-tensor parity의 독립 검증이 더 필요하다. 실제 metadata load·전체 변환·모델 추론은 각각 별도 실행이며 이번 감사가 자동 승인하지 않는다.
