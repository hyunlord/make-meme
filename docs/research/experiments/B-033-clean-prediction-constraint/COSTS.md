# B-033 실제 비용

실행은 VAE → S → D 순차 fresh worker로 완료했다. source encode1, decode3(source/final-only/step), 신규 full sampler1(40step·80forward·40clean constraints), 재시도0이다. 신규학습·설치·다운로드·Qwen·T5·CLIP·추가 관측forward는0이다.

| 단계 | guard wall초 | CUDA peak allocated GiB | CUDA reserved 관측최대 GiB | cgroup peak GiB | 시스템 MemAvailable 최소 GiB |
|---|---:|---:|---:|---:|---:|
| VAE | 27.366 | 8.910 | 11.166 | 2.257 | 76.816 |
| S | 999.175 | 33.832 | 33.893 | 62.582 | 52.619 |
| D | 15.222 | 8.908 | 11.562 | 2.227 | 75.980 |

서로 다른 회계이며 합산하지 않는다. RSS/RssAnon/RssFile/VmHWM은 MEASUREMENTS.json에 별도 저장한다. 시스템 가용량은 watchdog1초 표본, CUDA는 phase allocator관측, cgroup은 읽힌 peak다. 모든 stage swap0/guard service_exit/returncode0/MainPID0, 완료 phase와 실제출력을 함께 확인했다.

VAE load0.807초/sourceencode4.437초/source decode6.267초/final-only decode6.253초. S staged CPUload37.211초/DiT device이동7.691초/샘플링루프 약948.450초다. D VAEload0.690초/stepdecode6.617초. GPU stage guardwall합1041.763초(17.363분)이며 준비·리뷰·전송 시간은 포함하지 않는다.

CPU 두RGB_POST 합성·PNG/MP4인코딩·endpoint확인6.21초, 최대RSS883306496bytes, swap0/exit0. 신규MP4총5개(source reconstruction, final-only raw, step raw, 두post합성)는 새파생물 인코딩이다. 기존영상 재인코딩0이다.

최초2CFGforward의 ref/CLIP provenance hook은 텐서복사0이지만, model입력 noisehash확인은 각각 작은CPU복사를 수행한다. 모든hook복사0으로 확대하지 않는다. ExecStopPost의 이미종료/unload된 unit 메시지는 정상종료후정리경고로 보존하며 재시도하지 않았다.

B-032 두합성 CPU3.900초와 비교해 본실험은 전체sampler가 추가됐다. B-031 Qwenworker43.315분과 vehicleS1003.427초, 기존support주석5.75분은 이전에발생한 비용이며 이번증분비용에중복합산하지 않지만 전체시스템의존비용이다. 새mask주석0.

실행후 pipeline/watchdog둘다 inactive/MainPID0/Resultsuccess, MemAvailable93927500KiB와swap0, 기존ComfyUI만GPU에남음을확인했다. 기존프로세스종료나서비스변경은없다. 시각효과·비용정당화는 RESULTS의별도판정이다.

CPU PNG export보정은 원본float왕복최대1uint8level(0..1RGB에서1/255, modelspace에서2/255)을 피하기위해 exactE0bytes를복사한것이다. 마스크·계수·GPU실행은변경하지않았다.
