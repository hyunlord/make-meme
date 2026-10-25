# B-027 실제 조건 연결

최초 완료 animal pair의 `conditions.json`·`pair-conditions.json`과 실제 S/D receipt를 확인했다. 나머지 과제는 완료 후 같은 표에 추가한다. CPU 코드 검토만으로 runtime PASS를 채우지 않는다.

| leaf | 의미 | 실제 shape/dtype (animal) | pair 계약 |
|---|---|---|---|
| t0 | actual initial noise | [16,5,64,112],FP32 | 동일 |
| t1 | positive text | [44,4096],BF16 | 동일 |
| t2,t8 | 두 CFG CLIP | [1,257,1280],FP16 | 참조 변경 허용 |
| t3,t9 | 두 CFG reference VAE | [16,1,64,112],FP32 | 참조 변경 허용 |
| t4,t10 | 두 CFG reference semantic mask | [28,6,64,112],FP32 | prefix 변경 허용; 뒤5slice zero |
| t5,t11 | 두 CFG driving VAE | [16,5,32,56],FP32 | 동일 |
| t6,t12 | 두 CFG driving mask | [28,5,32,56],FP32 | 동일 |
| t7 | empty negative text | [1,4096],BF16 | 동일 |
| t13 | actual generator state | [16],uint8 | 동일 |
| t14 | UniPC timesteps | [40],int64 | 동일 |
| t15 | sigmas | [41],FP32 | 동일 |

참조 RGB 입력은896×512이고 driving latent는 공식 경로의 절반 공간 해상도다. reference mask의 첫 latent slice와 전체 reference-mask tensor를 혼동하지 않는다. 이 semantic tensor는 RGB alpha/attention hard mask가 아니다. 양 CFG 시각 조건은 같은 의미의 값을 공유하고 text만 conditional/negative로 나뉜다.

Animal actual initial-noise tensor hash는 `9d26386e01a5dce6b0dc21e3df26aab79b65a4403e11b6c8fc5a71873dd3c950`이다. 저장 container의 hash와 tensor-value hash는 별개다. 같은 seed라는 문장만으로 동일성을 가정하지 않고 모든 보존 leaf의 값 hash와 원래 device 구조를 비교했다.

| task | 변화한 leaf | 보존한 leaf | runtime 상태 |
|---|---|---|---|
| animal | t2,t3,t4,t8,t9,t10 | 나머지10개 | pair PASS, R1/R2 S40step80forward와 D17frames 완료 |
| human | t2,t3,t4,t8,t9,t10 | 나머지10개 | pair PASS, R1/R2 S40step80forward와 D17frames 완료 |
| vehicle | 미실행 | 미실행 | 미확정 |

R2 `provenance.preprocessed_inputs`는 R1 공식 경계 포착에서 계승된 값이다. 이를 R2 전처리 실측으로 설명하지 않는다. R2 RGB/mask 파일 hash·실제 encoder output hash·별도 config·parent cache hash가 해당 참조의 직접 근거다. 이 점은 [독립 코드 검토](CONTRACT_REVIEW.md)에도 보존한다.

실제 S의 첫 conditional/negative forward에서 cache의 ref/CLIP/pose/mask 객체 연결과 replacement 모드를 확인했다. 관측 전용 추가 forward·attention dump는 없다. final latent는 초기 noise와 다른 실제40번째 step 이후 상태이며, counters·config·condition hash·code manifest를 묶고 readback_exact를 확인한 후 D에 전달한다. raw decoded output은[3,17,512,896]이다. 이 기술 계약은 target 외형이나 시간 품질 성공을 뜻하지 않는다.

Human positive text는 실제[55,4096]이며 같은pair 안에서 동일하다. Animal의[44,4096]과 다른 것은 과제별 사전caption 차이이며 참조별 변경이 아니다. Human actual noise tensor hash는 위animal과 같고, 각pair의 t0 값으로도 다시 확인했다.
