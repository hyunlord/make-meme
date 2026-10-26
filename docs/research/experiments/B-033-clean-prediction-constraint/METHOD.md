# B-033: 고정 편집 영역의 clean prediction 제약

B-032의 float edit support E를 같은 source/target support, dilation 11px, feather 4px로 재구성한다. PNG는 미리보기 비교에만 사용하며 float E의 입력 대용으로 사용하지 않는다. 시간 max 그룹은 [0],[1..4],[5..8],[9..12],[13..16], 공간은 8×8 max pooling 후 3×3 max pooling이다. M=1은 자유 편집, M=0은 source 제약이다.

공식 full-resolution Wan VAE encode로 얻은 z_src와 기존 B-031 final latent z_base에 대해 FINAL_LATENT_ONLY = M z_base +(1-M) z_src다. source와 최종 control은 각각 한 번만 decode한다.

STEP은 공식 `FlowUniPCMultistepScheduler.convert_model_output`을 정확히 한 번 실행한 뒤 clean prediction에 같은 혼합을 적용한다. CFG 80forward, scheduler step/corrector/predictor는 원본이다. 변환된 prediction은 corrector와 model_outputs history에 함께 전달된다. velocity/raw prediction을 x0로 오인하거나 scheduler를 두 번 호출하지 않는다. `solver_p=None`, `predict_x0=True`, flow_prediction, thresholding=False, lower_order_final=True를 검사한다.

`clean_constraint.py`는 stored M[1,1,5,64,112]와 source[16,5,64,112]를 실제 sample의 4D/5D에 명시적으로 맞춘다. dtype/device는 실제 clean prediction을 따르며 endpoint는 정확히 복사한다. 원본 source/cache는 수정하지 않는다. OFF와 M=1 실제 소형 scheduler 궤적, M=0 history, mask 축, final endpoint 네 CPU 검사만 사용한다. 소형 PASS는 전체14B 동등성이나 시각 성능 증거가 아니다.

최종 raw와 동일 E의 RGB_POST를 별도로 비교한다. 이 개입은 source latent 제약이 대상 외형을 원래 차량으로 되돌릴 위험도 가진다. 보호 영역의 pixel exact는 후합성 성질이지 생성 모델 성능이 아니다.
