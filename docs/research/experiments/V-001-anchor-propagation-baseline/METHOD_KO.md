# V-001 해설

이번 실행은 구간 검증에서 멈췄다. 아래 엔진 설명은 공식 코드 검토이며 이번 실행으로 효과를 확인한 것이 아니다.

1. LTX의 첫 프레임 이미지 조건은 시작 외형을 latent 조건에 고정하고, IC-LoRA의 depth 참조는 이후 프레임의 구조를 제공한다. 공식 기본은 반해상도 생성 뒤2배 spatial 단계이므로 원래480높이는 맞지 않았고,사용자가576으로 개정했다. [고정 공식 코드](https://github.com/Lightricks/LTX-2/blob/e98f6d927d83c92ef2be6aec76c8440b19306e39/packages/ltx-pipelines/src/ltx_pipelines/ic_lora.py).
2. Bernini RV2V는 원본 영상과 참조 이미지를 각각 VAE로 encode해 video/image latent 조건으로 함께 받는다. single-GPU entry의 use_pe를 끄면 외부 prompt enhancer를 호출하지 않는다. [고정 공식 코드](https://github.com/bytedance/Bernini/blob/e6c2cf11843470b08491745947abcba9c3c6b079/bernini/pipeline.py). 이번 설치·실행은0이다.
3. C의 양끝 앵커와 약한 중간 조건은 중간 동작을 모델이 추론해야 했다. V는 한 앵커의 외형과 원본 전체의 조밀한 동작/구조를 함께 제공하려는 비교다. 이번에는 SAM이 반사도 객체로 세어 선행조건이 성립하지 않았다.
4. depth에는 원본 개체의 크기와 실루엣도 들어간다. 큰Lab을 요청하면 원본 구조 보존과 체형 변경이 충돌할 수 있다. 이 가설은 아직 시험하지 않았다.
