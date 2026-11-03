# V-001 해설

이번에는 반사 규칙을 고친 뒤 구간과 앵커까지 검증했다. 전파 엔진은 차단됐으므로 아래 설명은 공식 코드 분석이며 전파 효과의 실측이 아니다.

1. LTX 첫 프레임 조건은 앵커를 인코딩한 latent로 시작 외형을 고정하고 IC-LoRA depth는 매 시점 구조를 제공한다. E1은 승인된1024×576이며 이번에는 Gemma 접근403으로 실행하지 못했다. [공식 IC-LoRA 코드](https://github.com/Lightricks/LTX-2/blob/e98f6d927d83c92ef2be6aec76c8440b19306e39/packages/ltx-pipelines/src/ltx_pipelines/ic_lora.py).
2. Bernini RV2V는 원본 영상과 앵커 이미지를 각각 encode한 조건으로 받는다. Renderer-only 경로와 use_pe=false는 외부 planner 없이 실행할 수 있다. 원본832×480·앵커를 준비했고 renderer import는 성공했지만 고정 worker 한도 때문에 모델을 적재하지 않았다. [공식 pipeline](https://github.com/bytedance/Bernini/blob/e6c2cf11843470b08491745947abcba9c3c6b079/bernini/pipeline.py).
3. C의 양끝 앵커와 약한 중간 조건에서는 중간 동작을 모델이 채워야 했다. V의 한 앵커와 조밀한 원본 조건은 외형과 시간별 구조를 별도로 전달한다. 이번 앵커 게이트 통과가 시간 전파 성공을 뜻하지는 않는다.
4. Depth는 원본 개체의 크기와 실루엣을 포함한다. 큰Lab의 체형 변경과 원본 구조 유지가 충돌할 수 있다. 이번에는 생성이 없어 이 가설을 평가하지 못했다.
