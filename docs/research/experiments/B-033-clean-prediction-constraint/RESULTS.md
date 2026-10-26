# B-033 결과 — 생성 중 제약에서 접촉 주변 오염이 부분적으로 줄었다

**COMPLETED / 실행 계약 PASS / 국소 시각 개선 PARTIAL / 기본 방법 채택 보류 / temporal UNVERIFIED.** 같은 편집 영역의 RGB 후합성 이후에도 STEP_CONSTRAINED는 B-032 및 FINAL_LATENT_ONLY에 남던 적색·검정·흰색 바퀴 아래 조각을 더 작은 밝은 잔여 조각으로 줄였다. 높은 은색 target 차체와 거친 회전 순서는 유지됐고, 원본의 낮고 짙은 Mini로 돌아가는 뚜렷한 회귀는 관찰되지 않았다. 완전한 접촉·그림자 복원이나 일반적인 객체 편집 성공은 아니다.

## 무엇이 달라졌는가

사전에 고정한 전체 17프레임과 local0/8/16의 body/contact/graphic crop을 raw 및 동일 RGB_POST 조건에서 정적으로 확인했다. 부모 agent와 별도 read-only agent가 같은 자료를 검토했으며 독립 인간 평가가 아니다. 출력별 위치·시간 정렬, 마스크 축소, 좋은 프레임 선별은 하지 않았다.

| 판정 축 | B-032 RGB_POST | FINAL_LATENT_ONLY + 같은 RGB_POST | STEP_CONSTRAINED + 같은 RGB_POST |
|---|---|---|---|
| 뒤 바퀴 아래 오염 | 색이 강한 쐐기 조각이 남음 | 유사한 적색·검정·흰색 조각이 남음 | 색이 강한 조각이 줄고 작은 밝은 흔적이 남음: PARTIAL |
| target 외형 | 높은 밝은 차체·큰 창·세로 후미등 유지 | 주요 외형 유지 | 주요 외형 유지; 뚜렷한 source Mini 회귀는 미관찰 |
| 거친 동작 | 후면 노출이 증가하는 기존 진행 | 기존 진행 유지 | 같은 방향의 진행 유지; 정확한 회전각·속도 품질은 미검증 |
| 경계·접촉·그림자 | 어두운 하단부와 오염의 관계 불확실 | 완전히 해결되지 않음 | 하단부가 더 깨끗해 보이지만 밝은 잔여와 그림자·접지 정확성은 UNCERTAIN |
| 보호 장면 | E=0 원본 복사 | 동일 | 동일: 이 자체는 합성식의 성질 |
| 시간 품질 | UNVERIFIED | UNVERIFIED | UNVERIFIED |

FINAL_LATENT_ONLY raw도 큰 원거리 그래픽을 줄였다. 따라서 원거리 복원만으로 생성 과정의 개선을 주장할 수 없다. 이번 STEP의 관측상 차이는 **동일 후합성 뒤에도 남는 접촉 주변 조각의 감소**다. 작은 조각이 실제 차체 내부인지, 기존 수동 support의 margin인지까지 확정하지 않는다. 새로운 target이 경계에서 미세하게 잘렸는지, 바퀴가 실제 도로에 접촉하는지와 얇은 구조의 정확성도 완전 검증하지 않았다.

SOURCE_RECON은 원본 어두운 차량과 거친 진행을 유지하지만 세부 질감·경계가 원본과 pixel exact하지 않다. 이 압축 복원 오차와 clean 제약 효과를 분리한다. 전체 17장의 정적 변화 관측은 실제 속도의 연속 시청을 대신하지 않는다.

## 실제로 실행한 계산과 계보

사전 등록은 `4eba8318dd4a7010fa249988945d6209f29f45fb`, 코드·설정·입력·CPU 검증 고정은 `d893c618432c06d062173d75e4e811a6568e3f93`이다. [입력 검증](INPUT_VERIFICATION.json), [실행 freeze](EXECUTION_FREEZE.json), [방법](METHOD.md), [대조군](CONTROL.md).

- 기존 B-031 조건 16leaf·noise·RNG·scheduler와 B-032 source/S/T/E를 보존했다. E preview 17장 일치, 주석된 source/target core 17장 모두 M=1 포함을 확인했다. 재주석·마스크 변경은 0회다.
- full-resolution source VAE encode 1회로 `[16,5,64,112]` FP32 model-space latent를 만들었다. 절반 공간 크기 driving을 확대하지 않았다. source reconstruction decode 1회와 final-only decode 1회를 수행했다.
- 신규 sampler 1회에서 실제 40step·80forward·40clean conversion을 확인했다. 기존 converter를 한 번 호출한 결과에 제약을 적용하고, corrector와 history가 그 결과를 사용한다. 추가 관측 forward는 0회다.
- 실제 첫 양 CFG model 입력의 noise hash와 cache 조건 연결을 확인했다. converter trace는 CPU FP32 `[1,16,5,64,112]`이며 모두 finite다. sigma와 변화 norm은 개입 진단값이지 품질 점수가 아니다.
- 최종 latent를 원자적으로 저장·readback 검증한 뒤 S가 종료됐다. 별도 VAE worker에서 STEP decode 1회가 완료됐다. 신규 decode는 총 3회이며 모두 finite `[3,17,512,896]`, 17프레임·preview24fps다.
- source_fps=null, timebase_assumed=true를 유지한다. 파일 길이 17/24초를 실제 원본 시간축 확인으로 해석하지 않는다.

최종 STEP latent SHA256: `0356b5351122950a27334fcdef8ae6fd69a4554acaf5362c238dd303e6015280`. source/control latent와 실제 noise 해시는 [MEASUREMENTS.json](MEASUREMENTS.json)에 기록했다. weights·조건 cache·latent는 공개하지 않는다.

CPU PNG 저장 전 float 왕복에서 E=0 원본이 최대 1 uint8 level 달라지는 문제를 확인했다. 원래 freeze를 보존하고 [별도 export 보정](CPU_EXPORT_AMENDMENT.md)을 `9eee71bc888b18c6ec165de7f26b5fa59be98e08`에 고정한 뒤 처음 사용했다. 이는 B-032와 같은 명시적 endpoint 바이트 복사이며 마스크·GPU 계산은 변경하지 않았다. 두 새 합성의 저장 PNG를 다시 읽어 E=0 source exact / E=1 generated 양자화 exact를 확인했다. 손실 MP4의 pixel exact 주장은 하지 않는다.

## 추가 비용은 정당한가

source 준비·control·S·D의 GPU worker 합계는 **1,041.763초, 약 17.36분**이다. 그중 S는 로딩 포함 999.175초, STEP decode 자체는 6.617초다. S CUDA peak allocated는 약 **33.832GiB**, cgroup peak는 **62.582GiB**, 시스템 MemAvailable 최저는 **52.619GiB**였다. 서로 다른 회계이므로 더하지 않는다. swap은 0이며 기존 서비스는 보존했다. 두 새 RGB_POST 합성·저장·인코딩·endpoint 확인은 CPU 6.21초다. [실측과 비용](COSTS.md).

마지막 latent 혼합의 decode 자체는 6.253초이고 B-032의 기존 두 합성은 CPU 3.900초였다. 추가 sampler가 만든 국소 개선은 관찰됐지만 이 작은 개선만으로 17분대 추가 계산을 기본 비용으로 채택하지 않는다. **제한된 후속 검증 후보는 남기되 기본 경로 채택은 보류한다.** 기존 앵커 생성과 output-mask-assisted 주석 약 5.75분도 시스템의 선행 비용이다. 이번 증분만으로 전체 자동 편집 비용이라고 하지 않는다.

신규 학습·모델/패키지 설치·다운로드·Qwen/T5/CLIP·재시도는 모두 0회다. 자체 pipeline/watchdog 종료와 MainPID=0, 자원 회복을 확인했다. 정상 worker 종료 후 이미 unload된 unit 정리 경고는 기록으로 보존했다. CPU 계약 4개 및 실행 검증과 별개로, 미설치 ruff/pyright lint/type 검사는 NOT_RUN이다.

## 한계와 다음 판단 하나

B-031의 raw 결합 FAIL, 동물·사람 앵커 실패와 영상 NOT_RUN, B-032 PARTIAL은 그대로다. 이번 결과는 차량 한 개발 사례·한 seed·기존 출력 보조 mask에서의 부분 개선이다. 정확한 target instance 일치, 자동 mask, 다른 객체·장면, 긴 영상, temporal 품질, 일반화 또는 새 알고리즘의 우월성은 입증하지 않았다.

다음에 검토할 가설 하나는 **동일한 고정 clean-prediction 제약이 다른 공개 편집 사례에서도 target 회귀 없이 접촉 주변 오염을 줄이는가**이다. 현재 작은 잔여를 없애려는 mask/강도/스케줄 탐색은 하지 않았다. 사용자 검토 전 추가 실행·예약은 0이며 이번 비교로 종료한다.

[재현](REPRODUCE.md) · [한국어 수학·코드 설명과 질문/해설](../../lessons/B-033-clean-prediction-constraint.md) · [전달·검증](DELIVERY.md). compact에는 8개 비교 MP4와 전체 시트·crop·뷰어·보고서를, full에는 새 raw/latent와 재사용 규약을 추가한다. 실제 압축·전송 검증은 DELIVERY의 별도 영수증으로 확인한다.
