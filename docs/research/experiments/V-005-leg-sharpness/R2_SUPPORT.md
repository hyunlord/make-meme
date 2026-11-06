# R2 공식 지원 확인

확인 시각: 2026-11-06 04:07 UTC. 판정: **NOT_SUPPORTED** (고정 코드 `e98f6d927d83c92ef2be6aec76c8440b19306e39`에서 공식 dev + Union IC-LoRA + keyframe 조합 경로 미지원). R2-s1/R2-s2 생성 0회, checkpoint 다운로드 0회다. 이 판정은 모델의 수학적 불가능성이나 향후 다른 코드 버전의 미지원 주장이 아니다.

| 필수 조건 | 확인 |
|---|---|
| 공식 비축소 체크포인트 존재 | PASS. 공식 모델 카드가 `ltx-2.3-22b-dev`를 BF16 full model로 명시한다. |
| distilled와 같은 라이선스 | PASS. 같은 모델 카드가 full/distilled를 함께 LTX-2 Community License Agreement에 연결하며 Union 카드도 같은 `LICENSE-2`를 가리킨다. |
| 해당 IC-LoRA와 체크포인트 조합 안내 | 모델 계열 수준의 호환 근거는 있으나 **dev 실행 recipe는 확인되지 않음**. Union 카드는 LTX-2.3-22b 기반이라고 설명하지만 dev를 특정한 실행 예는 제시하지 않는다. |
| 공식 pipeline의 dev + IC-LoRA + keyframes 지원 | FAIL. 고정 버전의 상세 문서는 IC-LoRA pipeline을 distilled 전용으로 명시하고, 실제 구현도 guided dev denoiser를 연결하지 않는다. |

## 실제 코드 근거

Spark의 공식 checkout HEAD가 고정 SHA와 같고 Git 변경이 없는 것을 읽기 전용으로 확인했다.

- [`docs/pipelines.md` §5, 74·84행](https://github.com/Lightricks/LTX-2/blob/e98f6d927d83c92ef2be6aec76c8440b19306e39/packages/ltx-pipelines/docs/pipelines.md#L68): IC-LoRA CLI는 distilled checkpoint의 2단계이며, Python custom stage recipe 설명 뒤에도 distilled 전용이라고 명시한다.
- [`ic_lora.py` 289–295행](https://github.com/Lightricks/LTX-2/blob/e98f6d927d83c92ef2be6aec76c8440b19306e39/packages/ltx-pipelines/src/ltx_pipelines/ic_lora.py#L289): class 계약도 두 단계 distilled 사용을 설명한다.
- [`ic_lora.py` 785행](https://github.com/Lightricks/LTX-2/blob/e98f6d927d83c92ef2be6aec76c8440b19306e39/packages/ltx-pipelines/src/ltx_pipelines/ic_lora.py#L785): `denoise_chunks`에 custom guided denoiser를 넘기지 않는다. CLI도 815행에서 `distilled=True`로 설정된다.
- [`chunks/operators.py` 65–69행](https://github.com/Lightricks/LTX-2/blob/e98f6d927d83c92ef2be6aec76c8440b19306e39/packages/ltx-pipelines/src/ltx_pipelines/chunks/operators.py#L65): 생략 시 `SimpleDenoiser`를 사용한다. sigma 배열 교체만으로 공식 full-model guidance 경로가 되는 것은 아니다.
- [`ti2vid_two_stages.py` 430–461행](https://github.com/Lightricks/LTX-2/blob/e98f6d927d83c92ef2be6aec76c8440b19306e39/packages/ltx-pipelines/src/ltx_pipelines/ti2vid_two_stages.py#L430): guided dev 경로는 존재하지만 이 경로의 video condition factory는 이미지/keyframe 입력을 받으며 Union reference video 조건을 연결하는 공식 결합 경로가 없다.

상위 `pipeline-selection.md` 표에는 ICLoraPipeline의 multimodal guidance 칸에 체크가 있어 상세 문서·실제 코드와 불일치한다. 이 표만으로 지원을 선언하지 않고 상세 문서와 호출 배선을 기준으로 판정했다. 현재 웹 Union 가이드는 이미 LTX-2.5 distilled 예시로 바뀌어 있으므로 이를 고정 LTX-2.3 dev 지원 근거로 대체하지 않았다. R1에만 허용된 최소 patch 권한을 R2의 새 guided IC-LoRA 구현으로 확대하지 않는다.

## 공식 파일과 라이선스 식별

- [공식 LTX-2.3 모델 카드](https://huggingface.co/Lightricks/LTX-2.3/blob/c1521179de480464f366a98a9d9b2acc4cc097b9/README.md): snapshot `c1521179de480464f366a98a9d9b2acc4cc097b9`.
- 후보 파일 `ltx-2.3-22b-dev.safetensors`: **46,149,344,974 bytes** (약42.98GiB), HF LFS SHA256 `7ab7225325bc403448ea84b6db2269811a880e5118cd2ee2b6282a93d585016f`. 이는 공식 API 메타데이터이며 로컬 다운로드 검증값이 아니다.
- [Union 모델 카드](https://huggingface.co/Lightricks/LTX-2.3-22b-IC-LoRA-Union-Control/blob/20a580c8606c06a0988d40375a61309e0fe5893d/README.md): snapshot `20a580c8606c06a0988d40375a61309e0fe5893d`.
- [고정 버전 LICENSE-2](https://github.com/Lightricks/LTX-2/blob/e98f6d927d83c92ef2be6aec76c8440b19306e39/LICENSE-2): 2026-01-05 LTX-2 Community License Agreement, 파일 SHA256 `c325da090976a313b214bf0d6a1738003b96505c01c46043e80edc200a72c147`.

공식 결합 경로 조건이 실패했으므로 R2의 권장 step/guidance를 다른 파이프라인에서 임의로 가져오거나 메모리 추정만으로 실행하지 않았다. R2 메모리·시간은 **NOT_RUN**, 출력 품질은 평가 불가다. 이번에 지원되는 R1·R3는 별도로 계속한다.
