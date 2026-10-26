# B-031 환경과 공식 이미지 입력 계약

## 사전 고정

- 모델: [Qwen/Qwen-Image-Edit-2511](https://huggingface.co/Qwen/Qwen-Image-Edit-2511/tree/6f3ccc0b56e431dc6a0c2b2039706d7d26f22cb9), revision `6f3ccc0b56e431dc6a0c2b2039706d7d26f22cb9`.
- 공식 tree의 전체 파일 합계57,720,463,453bytes (53.756GiB). 이 값은 파일 크기이며 실행 메모리가 아니다. safetensors와 작은 공식 config/tokenizer/processor만 필요하며 다른 모델·추가LoRA는 받지 않는다. 모델 card의 Apache-2.0과 DAVIS 데이터 조건은 별개다.
- 별도 Python3.12 venv에서 기존 검증된 package site를 읽기 전용으로 재사용한다. 시스템 또는 기존 SCAIL/ComfyUI 설치에 쓰지 않는다. Torch2.14.0+cu130, Diffusers0.41.0, Transformers5.20.1, Accelerate1.15.0. 실제 전체 패키지149개의 버전을 `requirements.lock`에 기록한다. `.pth`로 연결된 패키지는 `uv pip freeze`에 나타나지 않아 importlib.metadata로 실제 import 가능 배포판을 고정했다.
- 공식 `QwenImageEditPlusPipeline`의 실제 signature에서 image list, width/height, true_cfg_scale, guidance_scale, negative_prompt와 step callback을 확인했다. 사용자 요청의 BF16/40step/trueCFG4/guidance1/negative단일공백/seed20261026/896×512를 유지한다. 모델 config guidance_embeds=False이므로 guidance_scale1은 인자를 전달하지만 공식 코드가 사용하지 않는다. trueCFG는 양/음80회 transformer forward와 공식 norm rescale을 사용한다.
- 공식 attention dispatch의 `native` (PyTorch SDPA)를 명시한다. 기존 SCAIL FA2 backend는 수정하지 않는다. 커널 개발·추가 attention 라이브러리 설치는 없다.

## 크기와 실제 입력

Image1 전체 source와 Image2 native GT bbox+10% crop의 순서는 고정이다. 공식 pipeline은 각 사진을 별도로 약384² pixel 면적의 vision 입력과 약1024² 면적의 VAE 입력으로 비율 유지 resize하고32배수로 반올림한다. 출력896×512는VAE16배수계약을 만족한다. 매우 작은 target 원천을 확대해도 새로운 세부 정보가 생겼다고 하지 않는다. 동물R1 175×54 crop의 낮은 원천 정보량을 보존해 기록한다.

`effective-inputs`는 같은 공식 resize/preprocess 함수를 호출해 내보낸 동등 전처리 사본이며 runtime hook 자체가 아니다. 별도 `actual-encoder-inputs.jsonl`은 실제 pipeline의 text encoder와 VAE encoder 첫 입력의 shape/dtype/hash를 기록한다. 관측 때문에 추가 encoder 또는 DiT forward를 실행하지 않는다. 첫 실제 transformer 두 branch와40개 완료step/80forward를 따로 기록한다.

## 메모리와 실행 정책

실측 준비 시 GB10 aarch64의 MemAvailable 약90GiB, swap0, 디스크 약1.247TB 여유였다. 기존 ComfyUI GPU 프로세스는 보존하고 idle queue/동일PID계보를 확인한다. 시작72GiB·실행24GiBheadroom·swap0과 다른 서비스 보호 정책은 유지한다.

공식 meta/sharded `low_cpu_mem_usage=True` BF16 로딩 후 text encoder, VAE, transformer를 순서대로 CUDA로 옮긴다. 큰 CPU 적재 전 tiny CUDA copy/add/synchronize/readback과 작은 anchor를 실행한다. CPU offload로 CPU/GPU 물리 메모리가 늘어난다고 보지 않으며 CPU 복사본을 상주시키는 offload를 사용하지 않는다. 가중치 약53.75GiB 외 activation과 일시적 복사 위험은 여전히 있으므로64GiB cgroup cap과 시스템headroom watchdog을 둔다. 실제 fit은 관측 전 UNKNOWN이다. Qwen 종료 후에만 SCAIL을 실행한다.

로컬파일만 불러오며 HF/Transformers offline을 켠다. 전량 SHA256/공식LFS SHA 또는Gitblob검증 뒤 code/input/package/model검증receipt를 seal한다. 실제 worker는 seal hash·설치버전·공식modulehash·가중치stat를 확인하고 시작한다. 로딩 자체가 실패하면 이미지 완료로 세지 않으며 실행 오류를 보존한다. 각 pipeline 호출 전 exclusive attempt를 만들고 재호출하지 않는다.

## 다운로드 중 관측된 비용과 제한 수정

UTC14:49:35에 pinned official snapshot 다운로드를 시작했다. Xet 경로에서 약14.93GB write 뒤 쓰기가 정체됐다. 세 가설은 네트워크 전송 정체, Xet 내부 buffering, auxiliary cgroup reclaim 압박이었다. process IO·파일mtime·cgroup·공식HTTP HEAD를 비교했다. HTTP는200/Range지원, Xet log는계속활성이나파일write는진전없음, cgroup은OOM0이었다. 원인은 확정하지 않았다.

다운로드 전용 신규4GiB cap을 한 번8GiB로 조정했지만 write 진전이 없어 해당 자체 unit만 종료했다. 이것은 GPU72/24GiB 가드 변경이 아니다. 같은 원격revision을 regular HTTP로 받는 한 번의 transport fallback을 선택했다. 기존 incomplete13,211,501,446bytes를 보존했다. 현재 hub는 unique temporary file을 사용해 partial 재개를 지원하지 않으므로 재개했다고 하지 않는다. 최종파일53.756GiB+보존partial12.304GiB는약66.06GiB이며70GiB 파일payload상한 안이다. 실제 네트워크 재전송량은 완전히 계측하지 못했으므로 UNKNOWN이다. 새 모델이나 이미지 재시도는 아니다.

최종 다운로드·hash 결과와 실제 memory/time은 실행 후 환경receipt와COSTS에 추가한다. 이 문서는 환경 설치 성공을 앵커 품질 또는 영상 성공으로 판정하지 않는다.
