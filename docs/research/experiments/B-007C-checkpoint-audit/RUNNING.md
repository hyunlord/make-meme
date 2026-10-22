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

## 10:30 UTC fixture amendment

최초 synthetic 실행은 full/mmap 검사를 지난 뒤 FakeTensor scope 복원 검사에서 실패했다. 별도 fresh process에서 빈 FakeTensorMode 초기화만으로 framework safe_globals 10개가 추가됨을 재현했다. 이를 NumPy context 누출로 혼동하지 않도록 FakeTensor 초기화를 먼저 실행하고 ambient 목록과 추가 목록을 기록한 뒤 각 context 전후 집합을 비교한다. 기존 실패 로그는 보존하고 허용 목록을 clear하거나 실제 checkpoint에 적용하지 않는다. 정확한 NumPy 네 항목은 전체 허용 집합이 아니라 기록된 framework ambient 집합에 대한 추가분이다.

## 10:34 UTC second and final fixture amendment

두 번째 실행에서는 scope 복원이 통과했지만 FakeTensor storage 객체의 `is` 동일성 검사가 실패했다. 별도 관측에서 세 객체의 식별자는 다르지만 checkpoint offset 4806과 storage 144 bytes는 같았다. 실제 CPU/mmap 로드의 storage 공유 검사는 그대로 유지한다. FakeTensor 객체 공유는 NOT_PRESERVED로 기록하고, metadata와 `_checkpoint_offset`을 실제 ZIP storage payload 위치에 대조한다. 이전 실패를 PASS로 덮어쓰지 않는다. 이 시험은 FakeTensor 객체 identity가 물리 storage alias의 일반 대리 지표가 아님을 드러냈다. 수정은 두 번으로 제한하며 실제 대형 checkpoint에는 적용하지 않는다.

## 종료 관측

실제 ZIP/graph 감사151.633초 완료, 원본 전후 SHA동일. NumPy3globals의 RNG-only 도달과 cross-root nonliteral/storage 공유0 확인. synthetic v3 PASS, v1/v2 실패 보존, FakeTensor object alias NOT_PRESERVED 별도. 최종 판단·미검증·한 후속 경로는 RESULTS에 기록했다. A의 기존111개 파일 hash는 B-007B 종료 snapshot과 모두 동일했다. 작업은 audit에서 종료하며 전체 변환·모델·추론은 시작하지 않는다.
