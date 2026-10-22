# B-007C 실행 기록

시작 2026-10-22 10:21 UTC, hard deadline 12:21 UTC. 사전 원격 HEAD `6e2594fea94a31340989e022339d2c4340d23e0d`와 PLAN을 확인했다.

## 고정 범위와 순서

1. 공식 출처·현재 직렬화 구현 조사: 완료, CODE_AUDIT 참조.
2. 코드 및 synthetic fixture 사전 등록, 독립 보안 검토: 진행 중.
3. 제한된 protocol-2 symbolic stack/memo 그래프 테스트 후 실제 ZIP/data.pkl 읽기 전용 감사. GLOBAL/REDUCE/BUILD는 노드로만 기록하고 실행하지 않는다. 알 수 없는 opcode는 차단한다.
4. 별도 CPU 프로세스에서 자체 생성 소형 fixture에만 exact safe_globals + weights_only=True를 적용한다. mmap/FakeTensor/value/storage/예상 밖 global 차단을 각각 검사한다.
5. 실제 증거와 fixture 범위를 분리해 한 후속 경로 선정, 문서·ZIP·원격 동기화 후 종료.

실제 checkpoint는 기존 SHA256 `d6c73e94c57eb36e6351c800d1228e41ed7e45db1ccf410dd875bcfdd2945e7f`, 65,582,563,395 bytes를 전후 확인한다. 원본에는 torch.load, 새 allowlist, pickle 재작성 또는 변환을 적용하지 않는다.

정적 감사 guard: GPU 비노출, RuntimeMax 1200s, MemoryMax 2GiB, MemoryHigh 1.5GiB, swap 0. Fixture guard: CPU threads 2, timeout 180s, 별도 프로세스. 현재 시스템 자원 확인 후 실행한다. 전체 deadline이 우선한다.

신규 대형 다운로드·diffusion·학습·전체 변환·full model loading: 모두 0. 작은 fixture 통과는 실제 변환 성공이 아니다. A/VACE/기존 checkpoint 및 B-007B gate는 변경하지 않는다.

코드 SHA는 이 문서와 함께 등록되는 git commit의 blob으로 고정하고 실제 실행 manifest에 파일 SHA256을 보존한다. 공개 자료에는 개인 경로와 raw pickle을 포함하지 않는다.
