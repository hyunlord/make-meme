# 실행 계약과 생성 방법은 다른 검증 층이다

## 직관

보고서 경로는 영상 수식에 등장하지 않지만, 적재가 종료되기 위해 필요한 실행 입력이다. CONT01은 그 입력을 전달하지 않아 DiT를 CPU에 적재한 뒤 실패했다. 따라서 계산을 못 한 사실은 clean-prediction 제약의 품질 증거가 아니다. 이번에는 실제 worker와 CPU preflight가 같은 초기화 함수를 사용한다. preflight만 환경을 따로 만들면 실제 실행과 검사가 다시 어긋날 수 있다.

## 계약과 순서

실행 허용 조건을 `C = stage ∧ input_paths ∧ offline ∧ report_path ∧ writable ∧ no_collision`로 쓴다. 이는 학습된 확률모델의 수식이 아니라 운영 전제의 논리곱이다. `C`가 거짓이면 torch/model 접근 전에 종료한다. 참이어도 현재 GPU 안전성·모델 연산·영상 품질은 별도 검증이다.

보고서는 이번 시도의 절대 `reports/loader.json`으로 명시 대입한다. 부모 셸의 값에 의존하는 setdefault는 이전 시도의 디렉터리로 누수될 수 있다. loader의 exclusive create(open x)는 기존 증거 덮어쓰기를 막는다. 쓰기 검사는 별도 고유 임시파일을 사용한다. 사전 검사와 실제 생성 사이의 경합 가능성을 사전 검사만으로 없앴다고 주장하지 않으며 실제 exclusive create도 유지한다.

## 생성 수학은 유지

기존 STEP은 UniPC가 얻은 clean prediction `z_hat0`에 `z_tilde0 = M*z_hat0 + (1-M)*z_source`를 적용한다. M=1은 생성값, M=0은 source latent이며 중간값만 혼합한다. 실제 `clean_constraint.py::mix_clean`은 endpoint에 torch.where를 써 exact 값을 유지한다. `[16,5,64,112]` CTHW latent와 `[1,1,5,64,112]` mask,40conversion/80CFGforward는 기존 계약이다.

최종 latent만 혼합하는 CONTROL과 STEP은 같은 혼합식을 쓰더라도 작용 시점이 다르다. STEP은 매번 solver에 전달되는 clean prediction과 이후 궤적을 바꾸고 CONTROL은 완성된 latent만 바꾼다. 같은 RGB_POST 뒤에도 편집 내부·경계 이득이 있는지를 확인해야 하며 원거리 배경 exact만으로 STEP의 추가 이득을 주장할 수 없다.

E는 RGB edit support, M은 시간그룹/공간max/guard로 얻은 latent영역이다. 둘 다 객체 alpha나 target정답이 아니다. BASE의 잘못된 SUV support를 포함한다는 제약을 유지한다.

## 질문

1. CPU preflight PASS 뒤에도 fresh GPU safety가 필요한 이유는 무엇인가?
2. 환경변수 누락으로 forward0인 결과에서 방법의 품질을 판정할 수 있는가?
3. 같은 혼합식을 마지막 한 번 적용하는 것과 solver의 매 clean prediction에 적용하는 것은 왜 다른가?

해설은 [ANSWERS_KO](ANSWERS_KO.md), 관측은 실행 종료 후 RESULTS에 별도 기록한다.

## 이번 관측

Mac의 공통 bootstrap/worker entrypoint fixture는24개를 통과했지만 Spark 접속이 실패했다. 따라서 `환경 함수의 로컬 기능 검증`과 `실제 호스트의 실행계약·안전 검증`을 구분한다. 새 solver/latent/영상 관측이 없어 위 생성수학의 효과는 이번 작업으로 판정할 수 없다. 기존 결과를 다시 평가한 것처럼 작성하지 않는다.

## 연결 회복 뒤 실제 호스트 검사

재개에서 같은 Spark Python/worker의4개 환경 조합 preflight와 CPU24검사가 통과했다. 다만 현재 큐서비스 관측과 기존 보호서비스 신원 검증은 실패했다. `C_runtime_env`와 `C_live_safety`가 다른 논리 조건이라는 실제 예다. 전자는 PASS여도 후자가 거짓이면 GPU를 실행하지 않는다. 이것은 clean-prediction 방법의 효과 평가가 아니다.
