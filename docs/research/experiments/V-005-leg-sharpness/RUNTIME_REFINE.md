# R1: 고정 IC-LoRA 경로의 최소 다듬기 어댑터

확인 기준은 공식 LTX-2 commit `e98f6d927d83c92ef2be6aec76c8440b19306e39`와 V-004 S2 실행 파일이다. 공식 `ICLoraPipeline`은 단계별 sigma를 받지만 초기 입력 영상 latent를 받는 인자가 없다. upstream 파일은 수정하지 않고, 해당 실행 프로세스에서만 `ic_lora.denoise_chunks` 호출 경계를 감싼다. 종료 시 원래 함수로 복원한다.

## 실제 schedule과 두 요청의 중복

공식 첫 단계 grid는 `[1, .99375, .9875, .98125, .975, .909375, .725, .421875, 0]`, 두 번째는 `[.909375, .725, .421875, 0]`이다. 종료점 0을 제외한 가장 가까운 시작점을 선택한다.

| 요청 | 1단계 시작 index / 실제 sigma / 남은 step | 2단계 시작 index / 실제 sigma / 남은 step |
|---|---|---|
| R1-a: 0.35 | 7 / 0.421875 / 1 | 2 / 0.421875 / 1 |
| R1-b: 0.55 | 7 / 0.421875 / 1 | 2 / 0.421875 / 1 |

따라서 **두 요청은 동일한 실제 강도로 매핑된다.** seed·입력도 같으므로 독립적인 강도 비교가 아니다. 새 timestep을 삽입하거나 가까운 두 번째 값을 선택하지 않는다. 실제 실행의 grid·call·step은 각 receipt로 다시 확인하며, 위 표는 CPU 사전 계산이다.

## 변경 경계

```diff
 # 공식 ic_lora.py: denoise_chunks 호출 경계에만 적용
- chunks = denoise_chunks(chunks, stage, sigmas=sigmas, noiser=noiser, fps=fps)
+ selected = select_schedule(sigmas, requested_sigma)
+ if stage_index == 0:
+     chunks = replace_first_chunk_video_with_source_vae_latent(chunks)
+ chunks = denoise_chunks(chunks, stage, sigmas=sigmas[selected.start_index:], noiser=noiser, fps=fps)
```

실제 구현은 [refine_runtime.py](code/refine_runtime.py), CPU 선택은 [refine_schedule.py](code/refine_schedule.py), 실행·검증·receipt는 [refine_entry.py](code/refine_entry.py)이다. 위 diff는 변경 경계를 나타내며 공식 checkout에 적용한 patch가 아니다.

첫 단계는 S2-s1 RAW MP4를 공식 decode/preprocess로 576×320에서 읽고 기존 VAE encoder로 인코딩한다. 빈 생성 latent만 이 값으로 교체한다. 원래 chunk의 text context, 이미지·canny conditioning factory, audio 및 layout은 그대로다. 첫 단계 생성 결과를 공식 spatial upsampler에 통과시킨 latent가 두 번째 단계의 입력이다. 두 번째 단계도 자신의 grid에서 가장 가까운 sigma부터 다시 noise/denoise한다. 원본 입력을 두 번째 단계에 다시 인코딩해 첫 단계 결과를 버리지 않는다.

공식 flow-matching `GaussianNoiser`는 단순 `clean + sigma * noise`가 아니라 `(1-sigma)*clean + sigma*noise`를 사용한다. 이어 원래 conditioning denoise mask로 clean 조건을 유지한다. 이 noiser와 masking 순서, RNG 객체, sampler 연산은 수정하지 않는다. 오디오도 공식 파이프라인의 같은 기본 경로를 유지하며 원본 음성을 입력하지 않는다.

## 메모리와 실행 계약

추가 source encode는 첫 denoise 전 generator에서 실행된다. `ImageConditioner.__call__`의 `gpu_model(...TRIM)` scope가 닫히면서 encoder storage를 dispose하고 메모리를 정리한 뒤 latent를 넘긴다. DiT의 실제 `stage(...)` 호출은 그 이후다. 소스 RGB 텐서는 encode 후 해제하고, 단계 사이에는 작은 latent만 유지한다. VAE와 DiT의 동시 상주를 추가하지 않는다.

첫 단계 입력 RGB BF16 버퍼 자체는 약 0.075GiB다. VAE 활성값은 기존 작은 control encode보다 클 수 있으며 실측 전 상한을 보증하지 않는다. 가드의 기존 95GiB 추정 여유와 100GiB worker 한도, NVRM·OOM·PSI 정책을 유지하고 실제 peak를 기록한다.

## CPU 확인

- 실제 공식 constants.py의 AST에서 grid를 읽으며 torch/model import는 하지 않는다.
- 요청 두 개 모두 각 단계 1step, 합계 2step으로 계산됨을 확인했다.
- 잘못된 grid 거부, 종료점 0을 시작점으로 선택하지 않음, 2단계가 첫 단계 결과를 이어받음, 원래 noiser 객체·호출 경계를 유지하고 wrapper를 복구함을 확인했다.
- Spark의 기존 연구 executable에서 두 runtime의 `--cpu-only`가 통과했다. 입력 RAW hash·73프레임·24fps·1152×640, 부모 코드 hash·공식 checkout·앵커 위치를 검사했다.
- CPU 검사는 실제 GPU 실행·영상 품질 확인을 대체하지 않는다.

공식 근거: [IC-LoRA pipeline](https://github.com/Lightricks/LTX-2/blob/e98f6d927d83c92ef2be6aec76c8440b19306e39/packages/ltx-pipelines/src/ltx_pipelines/ic_lora.py), [chunk operators](https://github.com/Lightricks/LTX-2/blob/e98f6d927d83c92ef2be6aec76c8440b19306e39/packages/ltx-pipelines/src/ltx_pipelines/chunks/operators.py), [GaussianNoiser](https://github.com/Lightricks/LTX-2/blob/e98f6d927d83c92ef2be6aec76c8440b19306e39/packages/ltx-core/src/ltx_core/components/noisers.py).

## 기계적 import 수정 (2026-11-06, 첫 CPU guard 이후)

직접 `python entry.py` 사전 검증은 통과했으나, 실제 보호 worker의 `runpy.run_path`는 스크립트 디렉터리를 자동으로 import 검색 경로에 넣지 않아 `refine_schedule` import에서 실패했다. 이 실패는 모델 적재·sampler 전에 발생했으며 기존 실패 stage·로그·entry bytes를 보존했다.

최소 수정은 sibling import 전에 `sys.path.insert(0, str(Path(__file__).resolve().parent))` 한 줄을 추가한 것이다. 다른 cwd의 새 인터프리터에서 `runpy.run_path`로 실행하는 회귀 검사는 수정 전 동일 오류로 실패하고 수정 후 통과했다(전체 CPU 검사 5개). Spark의 실제 연구 executable에서도 `/tmp` cwd에서 `run_name='__main__'`로 CPU 계약 검사를 통과했다. 기존 stage 파일을 덮어쓰지 않도록 새 entry 이름과 새 `importfix` stage를 사용한다. sigma·입력·모델·예산 변경은 없다.
