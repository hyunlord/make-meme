# B-002 생성 전 코드 감사

검토 기준: [PLAN](PLAN.md), DiffSynth-Studio `f39d731a3e318d25b725eb3389cfddb184619842`, 모델 revision `574e6a744642ce3bee319afc31496b88bde8aac4`, B-001의 `vace_experiment.py` 및 `lab-single-before` 실행 config/noise 기록. 이번 감사는 읽기 전용이며 GPU 재실행이나 새 결과 관측이 아니다. 공개 문서에는 자산 별칭만 사용한다.

## 입력과 shape 계약

1. 이전 R runner는 PIL `image.convert("RGB")` 다음 `ImageOps.pad(...,(512,288),color=(128,128,128))`를 수행한다. **명시적 EXIF transpose가 없다.** 새 R/R-bg가 EXIF 방향을 새롭게 적용하면 이전 R와 동일 조건이 아니다. 실제 EXIF orientation과 최종 decoded RGB hash로 확인하고 이전 동작을 유지하거나 차이를 명시해야 한다. pad는 비율 유지 resize 후 캔버스를 채우며 upstream VACE unit 자체는 resize하지 않는다.
2. [BasePipeline.preprocess_image/video](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/diffusion/base_pipeline.py#L118)는 RGB를 BF16/device로 옮긴 뒤 기본 [-1,1] 범위로 변환한다. mask만 [0,1]이다. 실제 BF16 연산 rounding을 무시해 float32 정규화와 바이트 동일하다고 가정하지 않는다.
3. [VACE unit](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/pipelines/wan_video.py#L674): white=reactive, black=inactive. video mask 미지정은 all-one이다. 이전 runner의 흰 mask는 같은 의미다. 이번 reference alpha는 사진 배경 변경용이며 video mask가 아니다.
4. source RGB와 mask로 분리한 inactive/reactive 영상을 각각 VAE encode하여 16+16 channel, mask를 8×8 블록의 64channel로 변환하여 합계96channel context를 만든다. reference는 `[encoded_reference,zeros]`와 zero mask로 시간축 앞에 붙는다.
5. 17frame,288×512,reference1장은 noise `(1,16,6,36,64)`, VACE context `(1,96,6,36,64)`, patch output `(1,1536,6,18,32)`, token3456이다. R/R-bg/P 모두 같은 장수·크기여야 한다. B-001 기록에서 이 경로 shape는 관측되었으나 새 실행 hook 확인은 실행 담당 기록을 따른다.

## CFG, scale, scheduler

[실제 sampling](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/pipelines/wan_video.py#L328)에서 positive/negative text context만 다르고 `inputs_shared`의 VACE condition은 두 forward 모두에 전달된다. 따라서 negative branch는 reference-free나 structure-free가 아니다. `v=v_neg+5*(v_pos-v_neg)`이며 `cfg_merge=False` 기본에서 step당2forward다.

`vace_scale=1.0`은 [DiT hint 덧셈](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/pipelines/wan_video.py#L1760)의 배율이다. CFG와 같은 값이 아니다. 이전 config 생략값은 pinned signature 기준 vace_scale1, sigma_shift5, denoising_strength1, tiledTrue, tile_size(30,52), tile_stride(15,26), cfg_mergeFalse, TeaCache off, sliding window off이다. runner는 Flash3/Flash2/Sage available flag를 false로 설정해 SDPA fallback을 사용한다. 실제 GPU SDPA backend까지 동일하다는 주장은 환경/실행 기록을 대조해야 한다.

[Wan schedule](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/diffusion/flow_match.py#L47)은 20step grid에 shift5를 적용하고 sigma를1→0으로 내린다. [target 및 step](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/diffusion/flow_match.py#L436)은 noise−clean target과 음의 delta sigma Euler update다. 이번에는 학습하지 않는다.

## RNG와 이전 R 재사용 판정

[generate_noise](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/diffusion/base_pipeline.py#L183)는 seed가 주어지면 새 CPU Generator를 만든다. FP32 randn 후 pipeline BF16/CUDA로 변환한다. [NoiseInitializer](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/pipelines/wan_video.py#L395)는 reference 장수만큼 시간길이를 늘리고 마지막 noise slice를 앞으로 옮긴다. [VAE encode](https://github.com/modelscope/DiffSynth-Studio/blob/f39d731a3e318d25b725eb3389cfddb184619842/diffsynth/models/wan_video_vae.py#L984)는 mu를 반환하며 posterior sampling을 하지 않는다. 따라서 이 경로에서 reference 내용 차이가 난수 소비량을 바꾸는 근거는 없다. shape/device/dtype/torch RNG 구현이 다르면 seed만 같아도 tensor가 달라질 수 있다.

이전 `lab-single-before`/seed20261022의 저장 noise hash는 `2e9cb4e5dea03c81bc772a0a7dc960fe659480fd85826b616bf8df49507e1e78`, BF16 `(1,16,6,36,64)`다. 저장본은 같은 upstream initializer를 별도 호출해 계산한 것이므로 **sampler 내부 tensor를 hook해 저장한 증거와는 다르다**. 새 호출에서 실제 initializer 출력까지 비교하면 더 강한 근거가 된다.

**정적 결론: 재사용 가능한 후보이나, 이 감사만으로 최종 재사용 확정은 아니다.** 다음 항목을 실행 담당이 일치 확인하면 reuse로 등록할 수 있다.

- 이전 단일 개체 f0~16의 source/edge 픽셀 순서·해시. `lab-before`의 다른 구간과 혼동하지 않는다.
- 원본 R 및 모델 입력 reference decoded RGB hash, dimensions, EXIF 처리, pad 알고리즘.
- video mask all-white와 condition의 범위·채널·장수.
- prompt/negative prompt 문자열, 실제 text embedding,20steps/CFG5/vace_scale1와 생략 기본값.
- model 파일 hash, upstream SHA, 실행 코드의 의미 있는 변경, BF16/SDPA/device/tile 설정.
- adapter=null이며 fresh pipeline에 LoRA fuse/hotload 없음. 과거 도시 학습 프로세스와 분리.
- 초기 noise shape/hash와 완료된 raw 출력 lineage.

모든 항목이 확인되지 않으면 6번째 새 run을 허용하는 것이 아니라 PLAN의 최대5회 대체 순서를 따른다. 가중치를 로드했거나 shape가 맞다는 사실만으로 조건 수용·개체·춤 품질을 승인하지 않는다.
