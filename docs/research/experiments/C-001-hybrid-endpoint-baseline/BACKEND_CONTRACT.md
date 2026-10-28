# C-001 양끝 조건 backend 계약

기존 `Wan-AI/Wan2.1-VACE-1.3B` revision `574e6a744642ce3bee319afc31496b88bde8aac4`를 재사용한다. 로컬 config는 `VaceWanModel`, dim1536/layers30/vace_in_dim96이며 Preview와 혼용하지 않는다. 기존 DiffSynth snapshot의 기록 revision은 `f39d731a3e318d25b725eb3389cfddb184619842`이고 실제 파일 해시는 별도 freeze에 고정한다. 원본 snapshot/venv/checkpoint는 수정하지 않는다.

## 실제 시간 조건

[VACE 공식 frameref helper](https://github.com/ali-vilab/VACE/blob/48eb44f1c4be87cc65a98bff985a26976841e9f3/vace/annotators/frameref.py)의 `FrameRefExpandAnnotator` class를 그대로 읽어 실행한다. helper SHA256 `dd622057ce57078c0afdac2ad89d9698f1fd28867c4db8379efabbe2dc861053`. 같은 크기로 준비된 앵커만 허용해 align_frames는 동일 크기 identity 분기로 제한한다. 이미지별 crop/warp는 하지 않는다.

`firstlastframe`, expand_num31은 앵커2+삽입31=33프레임이다. 지정위치는0/32, 중간RGB는 helper의127.5를uint8로변환한127, mask는양끝0/중간255다. PNG/인메모리PIL로전달하여조건MP4압축은없다. `vace_reference_image=None`이며두사진reference목록은사용하지않는다.

선택한 검증된 DiffSynth pipeline은 `vace_video`와 `vace_video_mask`를 VACE의 inactive/reactive VAE branch에 보낸다. 두 endpoint RGB는 inactive branch에 위치한다. CPU entry에서33개RGB/mask픽셀해시·시간위치·실제압축mask를기록한다.

중요한 구현 한계: 설치 DiffSynth와 [공식 VACE vace_encode_masks](https://github.com/ali-vilab/VACE/blob/48eb44f1c4be87cc65a98bff985a26976841e9f3/vace/models/wan/wan_vace.py)는 mask의시간축33→9에nearest-exact를사용한다. 그결과endpoint의0mask가압축mask채널에서빠질수있으며실제값을기록한다. 이를고치려고공식수식을바꾸지않는다. RGB의inactive VAE조건은남지만known입력조건이최종endpointRGB의pixel-exact일치를보장하지않는다.

## 고정 생성 설정

832×480·33frames·preview16fps, seed20261028, BF16, SDPA, adapter OFF. 기존검증DiffSynth `FlowMatchScheduler("Wan")`의Euler update를사용하며50steps·sigma_shift5·CFG5를명시한다. 공식VACE runner의UniPC50/shift16과동일solver라고하지않는다. 기존검증실행경로와공식firstlast helper를연결하는선택이며SCAIL40/shift3을복사하지않는다. 두사례동일설정이고품질에따른변경없음이다.

CPU-only와실제생성은같은`video_generate.py`와절대config를사용한다. 공통검사는절대경로/존재/앵커크기/33frames/endpoint/mask/helperhash와실제pipelineimport까지확인한다. CPU-only는가중치를읽거나CUDA를초기화하지않는다. 부모의기존보호supervisor가cgroup/서비스/GPU/메모리정책을담당하며본파일은새관리프레임워크가아니다.

실제model_fn호출과scheduler step을각각기록한다.50번째scheduler출력latent를원자저장·readback한다. VAErawtensor/모든PNG/MP4를보존하며양끝출력덮어쓰기·SAM후합성·업스케일은없다. latent이후실패시sampler를재실행하지않고저장물로복구해야한다. 실측전성능·품질PASS를선언하지않는다.

## 실행 전 실파일 SHA-256

모델 revision 표기와 별개로 기존 host 파일을 직접 읽어 확인했다. 가중치는 공개 저장소/검토 ZIP에 복사하지 않는다.

| 파일 | SHA-256 |
| --- | --- |
| diffusion_pytorch_model.safetensors | `c46a6f5f7d32c453c3983bbc59761ea41cd02ad584fb55d1a7ee2b76145847a2` |
| models_t5_umt5-xxl-enc-bf16.pth | `7cace0da2b446bbbbc57d031ab6cf163a3d59b366da94e5afe36745b746fd81d` |
| Wan2.1_VAE.pth | `38071ab59bd94681c686fa51d75a1968f64e470262043be31f7a094e442fd981` |
| google/umt5-xxl/spiece.model | `e3909a67b780650b35cf529ac782ad2b6b26e6d1f849d3fbb6a872905f452458` |
| google/umt5-xxl/tokenizer_config.json | `ed9a3a8b0faa71a70a32847e0435fe036e6e112d4df4edb7bb48a921e344dc05` |
| google/umt5-xxl/tokenizer.json | `6e197b4d3dbd71da14b4eb255f4fa91c9c1f2068b20a2de2472967ca3d22602b` |
| google/umt5-xxl/special_tokens_map.json | `7b8a9f5040adb67b5805abdfd42c1f8d0f3d0e711f10726580eb3789cd0ad61d` |
| diffsynth/pipelines/wan_video.py | `e3ab58df6db88987661813f92bca601de1397aa6a2986f2a9dda6e2771183bcc` |
| diffsynth/models/wan_video_dit.py | `68d35cffc5b12ac3942f15eafa5fc30f692d8ea099f5aad516ad82b866a97f6e` |
| diffsynth/models/wan_video_vae.py | `17ad9aa496a13626f55d8c0b2508d72a98f3195353ba39e3cc451434371315d7` |
| diffsynth/diffusion/flow_match.py | `43abe34773144e7f3ce660d40bf5f3ee25fe5538cbc7654c3992b9e40a761486` |
