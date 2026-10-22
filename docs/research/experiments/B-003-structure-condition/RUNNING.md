# B-003 실행 기록

- 01:26:56 UTC 시작,03:26:56 UTC deadline. PLAN `7368c1f9ff70030ff6490b1ff4a0a88e9213ebe2` push 확인.
- 입력 점검 완료: pinned VideoData로 real/null 모두 RGB uint8 (288,512,3). 원래 real PNG 저장은 grayscale L이지만 decoder가 RGB로 복제하며 기존 B002 입력 RGB와 같다. null min=max0,real0..255. [실측](decoded_input_audit.json).
- 실제 VACE 인자는 condition→vace_video,white mask→vace_video_mask,R-bg→vace_reference_image. sampler call AST는 B002와 같고 read-only context slice hash 관측만 추가했다.
- CPU synthetic wiring 검사는 실제 PipelineUnitRunner 호출 시 tensor identity/value/CPU RNG 보존을 확인했다. 이는 영상 품질 검사가 아니다.
- adapter=null 검사,4회 cap,동일 label 재실행 차단,deadline/메모리 guard 유지. 신규추론은 이 코드 고정 이후 시작한다.
- Spark GB10,driver580.126.09,Python3.12.3,torch2.14.0+cu130,CUDA13,BF16지원. 시작 MemAvailable86,186,254,336bytes,swap0,기존ComfyUIqueue비어있음. 기존작업중단없음.
