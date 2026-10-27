# 같은 영역의 세 비교와 종료 신원

이 문서는 CONTINUATION_01의 고정 수식과 판정 규칙이다. 실제 결과는 [RESULTS](RESULTS.md)에 연결하며 운영 보완을 생성 방법 개선으로 세지 않는다.

## 직관: 원본을 언제 섞는가

RGB 후합성은 이미 생성된 영상의 바깥 영역을 원본으로 돌려놓는다. 마지막 latent 혼합은 VAE 디코딩 직전에 주변 latent를 원본으로 바꾼다. 생성 중 제약은 각 단계에서 주변 clean prediction을 바꾸므로 다음 모델 평가에 도달하는 상태도 달라질 수 있다. 같은 영역을 사용해도 이 세 연산은 동치가 아니다.

원본 RGB를 V, 생성 RGB를 G, 편집 support를 E∈[0,1]이라 두면 모든 비교의 마지막 연산은

`Y = (1-E) V + E G`.

E는 객체 alpha가 아니다. 원본 차량을 지워야 할 위치, BASE가 실제 생성한 차량, dilation과 feather를 포함한다. 이번 T는 원하는 클래식 차량의 GT가 아니라 잘못된 BASE SUV의 관측 support다. 이 support로 고정한 영역이 새 차체를 제한할 수 있다. H=empty이므로 확인되지 않은 접촉 그림자를 정답으로 채우지 않는다.

## 수식과 실제 tensor

픽셀 E의 shape는 `[17,512,896]`다. 시간 max 그룹 `[0],[1..4],[5..8],[9..12],[13..16]`, 공간8×8 max 후3×3 max guard를 적용해 `M:[1,1,5,64,112]`를 만든다. M=1은 자유 생성, M=0은 source 제약이다. full-resolution source의 WanVAE latent `z_src`와 BASE final latent `z_base`는 `[16,5,64,112]`다. 이것은 VAE receptive field의 정확한 역상이라는 보장이 없는 보수적인 support 대응이다.

FINAL_LATENT_ONLY:

`z_final = M z_base + (1-M) z_src`, `G_final = Decode(z_final)`.

STEP에서는 같은 noisy state `z_k`의 모델 출력과 공식 UniPC converter가 만든 clean estimate `x̂0,k`에

`x̃0,k = M x̂0,k + (1-M) z_src`

를 적용한다. 그 값을 공식 corrector/history/predictor에 넘기고 다음 상태를 만든다. noisy state에 clean source를 바로 붙이는 연산이 아니다. 고정 CFG와 모델 호출 수는40step/80forward이며 converter 제약은40회다.

실제 함수는 [clean_constraint.py](../video_code/clean_constraint.py)의 `latent_mask`, `mix_clean`, `CleanConstraintScheduler.convert_model_output`이다. converter는 `super().convert_model_output`을 한 번 실행한다. `mix_clean`은 M=0/1에서 torch.where로 source/generated endpoint를 정확히 보존하고 실제 prediction의 dtype/device를 따른다. [phase_sample.py](../video_code/phase_sample.py)는 source/cache를 읽고 final latent의 finite·40/80·제약40회·history=None을 검증해 decode 전에 저장한다. FINAL_ONLY는 새 모델 forward가 없다.

## 해석: 배경 exact와 외형 성공은 다르다

E=0의 RGB 원본 exact는 합성식의 성질이다. 그것만으로 모델이 장면을 이해하거나 target을 교체했다고 판단할 수 없다. 핵심 비교는 동일 RGB_POST를 거친 뒤의 편집 내부·경계·접촉이다. BASE부터 클래식 target이 없으므로 그대로인 SUV를 'target 비회귀' 성공으로 계산하지 않는다. 원래 없던 큰 도로 그래픽이 계속 없다는 사실도 추가 개선 증거가 아니다.

source 제약은 주변 문맥을 제공하지만 참조 외형의 누락을 반드시 복구하지 않는다. 원래 source 차량으로 회귀할 위험도 있다. 정확한 source 복원과 목표 객체 교체는 서로 다른 평가 축이다. 한 seed·한 유효 차량 사례 및 비강체 앵커 실패를 전체 성공률이나 일반화 근거로 합치지 않는다.

## 운영: PID는 신원이 아니다

PID는 재사용될 수 있는 숫자다. 관측 신원은 `(boot identity, PID, proc starttime, unit invocation, cgroup)`의 연결과 살아 있을 때의 command 근거로 확인한다. 현재 cgroup 목록과 GPU driver 목록은 같은 순간의 원자적 snapshot이 아니다. 하지만 차이가 있다는 사실만으로 종료 지연을 확정할 수도 없다.

새 가드는 기록된 같은 worker의 정상 종료만 최대30초 관측하며 그동안 다음 GPU 단계를 시작하지 않는다. 사라진 proc, 다른 starttime, 외부 GPU 작업, queue busy, 관측 실패, 메모리 위반은 별도로 남긴다. worker_complete와 returncode0는 결과 기록의 일부일 뿐 안전 오류를 무효화하지 않는다. 이전 로그에는 새 신원 정보가 없으므로 이번 fixture PASS가 과거 NOT_CLEAN을 소급 PASS로 바꾸지 않는다.

## 이해 확인 질문

1. E=0 영역이 원본과 완전히 같다면 왜 객체 교체 성공을 뜻하지 않는가?
2. 마지막 latent 혼합과 매 step clean 제약에 같은 M을 사용해도 왜 출력은 달라질 수 있는가?
3. 같은 PID가 systemd MainPID와 일치하지만 proc가 사라졌다면 왜 바로 자체 종료로 허용할 수 없는가?

해설은 [ANSWERS](ANSWERS_KO.md)에 분리한다.

## 이번 실제 관측과 실패의 위치

FINAL_ONLY는 실제 decode를 끝냈다. 원거리 raw 배경 변화는 있었지만 동일 E 후합성 뒤 SUV 외형과 바퀴 아래/우측 경계 조각의 뚜렷한 개선은 관찰하지 못했다. STEP은 loader 보고서 경로 환경변수 누락으로 첫 forward 전에 실패했다. 따라서 반복 clean 제약의 이번 효과를 수식만으로 추정하거나 실패한 것으로 판정할 수 없다. CPU fixture는 종료 정책/혼합 endpoint의 검사였고 전체 loader 실행 계약을 모두 검증한 것은 아니었다. 이 검증 공백과 실행 오류를 보존한다.
