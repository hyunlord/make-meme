# B-003 실행 기록

- 01:26:56 UTC 시작,03:26:56 UTC deadline. PLAN `7368c1f9ff70030ff6490b1ff4a0a88e9213ebe2` push 확인.
- 입력 점검 완료: pinned VideoData로 real/null 모두 RGB uint8 (288,512,3). 원래 real PNG 저장은 grayscale L이지만 decoder가 RGB로 복제하며 기존 B002 입력 RGB와 같다. null min=max0,real0..255. [실측](decoded_input_audit.json).
- 실제 VACE 인자는 condition→vace_video,white mask→vace_video_mask,R-bg→vace_reference_image. sampler call AST는 B002와 같고 read-only context slice hash 관측만 추가했다.
- CPU synthetic wiring 검사는 실제 PipelineUnitRunner 호출 시 tensor identity/value/CPU RNG 보존을 확인했다. 이는 영상 품질 검사가 아니다.
- adapter=null 검사,4회 cap,동일 label 재실행 차단,deadline/메모리 guard 유지. 신규추론은 이 코드 고정 이후 시작한다.
- Spark GB10,driver580.126.09,Python3.12.3,torch2.14.0+cu130,CUDA13,BF16지원. 시작 MemAvailable86,186,254,336bytes,swap0,기존ComfyUIqueue비어있음. 기존작업중단없음.

## 첫 seed 완료

C-real20261022 및 C-null20261022 두 새 run이 exit0으로 완료됐다. 실제 noise/positive/negative text 및 reference prefix/inactive/mask 해시가 같고 reactive/context 해시는 다르다. 대표 f8 정적 관측에서 real은 착석, null은 네 발을 내린 자세로 보였다. 이는 아직 전체 네 셀의 결론이나 시간 품질 검증이 아니다. 두 번째 seed는 같은 계획대로 실행 중이다.

핵심 모델/토크나이저9파일 및 upstream5파일 fresh hash는 B002와 같았다. 전체 upstream tree의 독립 Git 검증을 했다는 뜻은 아니다. 추가 관측용 코드는 compile/AST 통과; Ruff/BasedPyright는 현재 경로에서 사용 불가여서 NOT_RUN, 추가 설치하지 않았다.

## 네 셀 완료

4started/4finished(exit0),재시도0,학습0. 모든pairedcontrol검사와17frame24fps검사를 통과했다. real착석/null사족이라는2seed공통변화와0/4직립실패를RESULTS에 기록했다. 후속생성은중단하며마지막문서·ZIP검증만진행한다.
