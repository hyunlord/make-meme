# B-007E post-sampler offload/decode 경계의 메모리 guard 종료

## 확인한 결과

공식 run은 실제 전체 모델 적재와 첫 DiT forward를 통과했다. sampler 로그40/40 뒤 post-sampler offload/decode 경계에서 2026-10-22 14:30:22 UTC에 MemAvailable=23.898979GiB가24GiB 하한을 밑돌아 guard가 종료했다. swap0, OOM0이다. CUDA OOM 또는 FlashAttention 실패라고 바꾸어 쓰지 않는다.

raw_output.pt와 MP4는 없다. Lab는 NOT_RUN이며 review_outputs.py도 실행하지 않았다. first-forward finite PASS는 end-to-end 완료나 시각 품질의 증거가 아니다. 현재 initial noise만 저장됐고 **최종 denoised latent는 저장되지 않았다**. 이를 사용해 decode만 즉시 재개할 수 있다고 주장하지 않는다.

## 실제 소스 경로

고정 commit은 `78fe19576bb06be96c2375e088574a262a300edb`다. [scail.py421–426](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L421)은 offload에서 `self.model.cpu()`와 empty_cache를 호출한 뒤 `self.vae.decode(x0)`를 호출한다. CPU로 이동한 model 객체는 삭제되지 않는다. decoded video가 sample_func에서 반환된 다음에야 segment 결과를 CPU에 보관한다.

[vae.py544](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/vae.py#L544)는 latent scale 복원→conv2→각 latent time slice의 decoder 순서다. feat_cache를 사용하고 첫 출력 이후 `torch.cat([out,out_],2)`로 출력 시간축을 누적한다. 끝에서 cache를 정리한다. [외부 decode wrapper657](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/vae.py#L657)은 autocast로 decode한 출력을 float로 바꾸고 clamp한다. 따라서 latent보다 큰 spatial/temporal decoder activation, cache, 누적 출력·cat의 순간 공존, 최종 float 변환이 존재할 수 있다.

## 원인에 대한 가설과 미측정

**정확한 종료 subphase는 UNOBSERVED다.** sampler 뒤 model.cpu(), empty_cache(), vae.decode() 사이 phase hook이 없어 VAE decode에 실제 진입했는지 확인할 수 없다. RssAnon이 약13GB에서33,101,068KiB로 증가한 관측은 GPU→CPU offload의 순간 공존과 강하게 부합하지만 직접적인 원인 증명은 아니다. 따라서 VAE activation 폭증 또는 tiling 필요를 확정하지 않는다.

실측 DiT parameter payload는 약33.17GB다. 공식 경로에서는 decode 때 불필요한 DiT도 CPU 객체로 남고 T5 등 pipeline 구성요소도 유지된다. Spark는 통합 메모리이므로 CPU offload는 전체 물리 메모리에서 parameter를 제거하는 연산이 아니다. 이 잔류 상주와 decoder activation이 함께 pressure를 만들었다는 것이 **소스에 근거한 가설**이다. 정확히 어느 객체가 몇 bytes를 차지해 하한을 넘겼는지 완전하게 분해한 것은 아니다.

실제 첫 forward의 CUDA allocation/peak는 decode allocator peak와 다르다. decode peak가 직접 측정되지 않았으므로 이전 forward 수치를 대입하지 않는다. cgroup은 전체 CUDA allocation을 포괄하지 않아 global MemAvailable watchdog이 필요했다. OOM 없이 guard가 멈춘 사실을 영상 성공으로 취급하지 않는다.

## 다음 한 실험 — 최종 latent 보존과 post-sampler 메모리 전이 측정

다음 별도 승인 실험 하나에서, 먼저 동일 조건 sampler의 **최종 denoised latent를 decode 직전에 CPU tensor로 원자적으로 저장하고 hash·shape·dtype·scheduler 종료를 기록**한다. 현재 그 자산이 없으므로 이것에는 새로 승인된 sampler 예산이 필요하며 이번 실행에서 자동 재생성하지 않는다.

다음 실험의 단일 변경은 **sampler 종료 직후의 `self.model.cpu()`만 생략하고 DiT를 GPU에 유지한 채 decode까지 진행**하는 것이다. 다른 offload 정책·geometry·시간축·precision은 유지한다. 최종 denoised latent를 decode 전에 저장하고, 저장 전후·post-loop 경계·cache 정리 전후·VAE decode 진입/완료에 phase hook을 둔다. 같은24GiB headroom·wall-clock·자기 프로세스 종료 guard를 유지한다.

가설은 이 한 번의 CPU offload를 생략하면 CPU parameter 복사본과 아직 해제되지 않은 GPU cached weight의 순간 공존을 피할 수 있다는 것이다. DiT GPU 상주 자체가 decode headroom을 충분히 남긴다는 보장은 없다. 현재 종료 subphase는 UNOBSERVED이며 이 가설은 증명되지 않았다. 기존 full-pipeline decode 완료 비교군도 없어 완전한 인과적 분해를 주장하지 않는다. 새 tiling·해상도 축소·VAE-only 프로세스 분리·모델 변경을 함께 시험하지 않고, 실패하면 자동으로 다른 방법을 잇지 않는다. 본 문서는 하나의 후속 제안이며 구현·실행하지 않았다.
