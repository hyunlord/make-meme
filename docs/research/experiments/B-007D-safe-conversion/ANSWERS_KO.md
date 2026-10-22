# B-007D 해설

1. 각 shape는 (D,D), 각 논리 bytes는 4D², 합계는 12D²다. 연속 행 분할은 같은 storage를 가리키는 view일 수 있어 full copy가 필수는 아니다. 저장된 tensor의 값 순서와 dtype를 검증해야 하며 원본 storage 공유까지 safetensors에 유지할 필요는 없다.
2. chunk는 쓰기 buffer 단위다. 입력 mmap resident pages, 출력 dirty/file cache, runtime allocations 등이 별도로 존재한다. cgroup과 RSS·GPU allocator는 측정 범위가 다르다. OOM 방지나 통합 메모리 상한을 chunk 숫자만으로 보증할 수 없다.
3. 각각 metadata 재구성과 파일 구조의 제한된 사실만 입증한다. 실제 전체 값의 per-tensor parity, OS 격리 probe, 자원 guard, model forward는 추가 증거가 필요하다. 이번 단계에서는 실제 model load와 영상 생성이 승인되지 않았다.
