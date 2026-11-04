# V-002 결과: BLOCKED_EXTERNAL_GPU

**신규 영상 0/5, 출력 SAM 측정 0회.** M1·M2·M3·LTX canny는 외부 GPU 배치와 충돌하여 시작하지 않았다. 최초 guarded CPU admission이 UNKNOWN_GPU_PID로 거절됐으며 worker 생성·모델 적재는 없었다. 약 10분 동안 외부 배치가 계속 살아 있고 GPU 자식 작업이 반복됐으므로 순간적인 GPU 공백을 종료로 간주하지 않았다. 타 작업을 종료하지 않았고 자동 재시도도 하지 않았다.

검토 ZIP의 index.html에는 실제 원본과 기존 V-001 E1-s1을 나란히 두고, 신규 다섯 열은 NOT_RUN으로 표시한다. 원본은 보존된 73 PNG에서 만든 검토용 파생 MP4이며 E1-s1은 생성 MP4와 byte 동일하다. 입력 진단 시트는 모델 출력이 아니다. 품질은 **HUMAN_REVIEW_PENDING**이다.

| 항목 | 결과 |
|---|---|
| M1 / M2 / M3 | BLOCKED_EXTERNAL_GPU, 생성 0회 |
| VACE 14B | ENGINE_BLOCKED_MEMORY_ESTIMATE: 보수적 사전 추정 128GiB > 100GiB |
| LTX canny | BLOCKED_EXTERNAL_GPU, 생성 0회 |
| V-001 E1 두 영상 SAM | BLOCKED_EXTERNAL_GPU, 자동 수치 없음 |
| 새 영상 시간·메모리·동작 IoU | 미측정 |
| 14B 변형 선택 | NOT_EVALUATED, M1–M3 결과 부재 |

## 확인한 준비물

동일 구간 [240,313), 기존 앵커·SAM·depth를 재사용했다. 실제 개체 track0(Lab)·track1(IG), 반사 track2·3에 고정 팽창을 적용했다. 73프레임의 RGB 이진 마스크 검사, 모델 입력 제작, 흰 배경 참조 두 장과 lossless canny 조건 제작을 완료했다. M1–M3 및 LTX canny 직접 CPU 입력 검사는 모두 통과했고 torch를 import하지 않았다. LTX CLI의 누락된 --config 인자는 모델 실행 전에 수정했고 원래 오류도 보존했다.

CPU 평가기 fixture는 통과했으나 생성 영상 성능을 뜻하지 않는다. 원본을 자기 자신과 비교한 IoU 1.0도 fixture 값이다. V-001에 대한 사용자의 “원본과 전혀 다른 동작” 판정은 사용자 관측으로 보존하며, 이번에 자동 측정으로 확인했다고 쓰지 않는다.

## 운영·제약

승인된 drop-caches helper는 Spark에 없었다. 사용자 규칙대로 ABSENT_CONTINUE로 기록했으며 설치나 다른 sudo 명령을 실행하지 않았다. 커널 로그 읽기는 가능했다. allocator·100GiB cgroup·NVRM 첫 오류 중단은 V-002 실행 사본에만 구현하고 CPU 검증했다. 실제 heavy guard 동작과 모델 runtime 성공은 미검증이다.

14B 추정에는 원본 파일 page cache, BF16 가중치, T5/VAE와 활성값을 포함했다. 이는 측정 peak나 불가능성 증명이 아니라 시작 상한을 적용한 보수적 추정이다. 숫자를 낮춰 실행하지 않았다. M3 첫 프레임 mask0은 원본 입력 계약대로 보존했지만 기존 native mask 시간 압축 때문에 latent의 엄격한 첫 프레임 고정을 보장하지 않는 제한을 기록했다.

## 종료와 남은 일

V-002 worker·systemd unit은 시작되지 않았고 종료 확인에서도 0개였다. 외부 작업은 그대로 살아 있었다. 7시간은 상한이며 외부 충돌을 우회하거나 시간을 채우기 위해 계속 호출하지 않았다. 모델 실행은 미완료다. 자원 충돌이 해소된 재개 시점에는 보존된 사전 계획·입력·예산을 사용하되 새 시작 관측이 필요하다. V-003 및 추가 학습·생성은 예약하지 않았다.
