# 실행 전 검토 범위

독립 읽기 전용 검토는 pinned SCAIL image cross-attention의 `img_x`가 text 합산·output projection 전에만 바뀌는지, 실제 block metadata의 generated 구간, OFF/0 원래 함수 보존, producer cache 검증, 40step/80forward 및 latent 선저장을 확인했다. 소스 검토에서 blocking defect는 발견하지 못했다. 이는 CPU 실행이나 GPU·영상 품질 검증을 대신하지 않는다.

이후 실제 CPU 지도 생성에서 AST가 config의 `WanSCAILModel` 이름을 찾다가 `StopIteration`으로 중단했다. pinned `model_scail2.py`의 실제 클래스는 `SCAIL2Model`이므로 그 이름만 수정했다. 지도 연산·source SHA·실험 설정은 변경하지 않았으며 이 실패 시점 GPU 사용은0이었다. 소스 검토 PASS를 실행 PASS로 소급 해석하지 않는다.

LSP 도구는 네 파일 요청에서 `Transport closed`를 반환했다. 따라서 LSP 정적 진단은 `UNAVAILABLE / NOT_CLEAN`이며 compile·CPU 계약 검사와 구분한다. 환경 재설치·경고 억제·전체 타입 리팩터링은 하지 않았다.

실제 지도 생성, CPU 계약 결과, 사전 고정 해시와 첫 forward의 범위/통계, 최종40×80 gate count는 각각 별도 실행 근거로 기록한다.

## 진행 중 문서 대조

읽기 전용 별도 agent가 전체 의뢰서와 METHOD·한국어 lesson·RESULTS·ABLATIONS를 대조했다. B027 전6case 공통 기준선, 합산/projection 전 image-only 변경, 남는 reference VAE 경로, 계수 평균과 특징 보존의 차이, generated 외 직접계수1, 실제 FP32, 단일seed 개발 패널 및8회/40step/80forward 상한에 실질 모순을 발견하지 못했다. 이는 시각 관측의 독립 재판독이나 최종 산출물 검증이 아니다. 당시 미완료 칸과 사전 상태 문구는 종료 기록에서 갱신한다.

## 최종 8case 실행 근거 대조

전체 실행 종료 후 별도 agent가 Spark의 실제 JSON 장부와 파일 SHA256을 읽기 전용으로 대조했다. 검토에는 Python 표준 라이브러리와 파일의 순차 해시만 사용했으며 Torch·모델·tensor를 적재하거나 추가 GPU 연산을 실행하지 않았다. 범위는 animal/human/vehicle METHOD R1/R2의 6case와 animal/vehicle CONTROL R1의 2case 전체다. 판정은 **RUNTIME_EVIDENCE_PASS**이며 시각 품질 PASS가 아니다.

- 모든 case의 완료 장부는 40step·80forward, 40개 block 각각 80회 gate 적용을 기록한다. 실제 generated 범위는 start1792/length8960/suffix2240, grid `[5,32,56]`, 첫 image feature dtype은 FP32이며 METHOD/CONTROL 설정과 support SHA가 일치했다.
- B027 producer binding과 실제 cache 파일 SHA, 16leaf metadata 및 runtime 복원 SHA/device를 대조했다. noise·RNG·scheduler도 이 16leaf에 포함한다. 사전 고정 코드·support·단계별 config·pinned upstream 파일 SHA가 최종 파일과 일치했다.
- 최종 latent 파일의 실제 SHA256은 해당 sidecar의 `file_sha256`과 일치했다. 이 파일 해시 검사와 별도로, `final_latent.json:tensors.t0.sha256`을 `conditions.json:tensors.t0.sha256`과 비교했다. 전체8case에서 shape `[16,5,64,112]`와 dtype FP32는 같고 tensor 해시는 달랐다. 두 tensor 해시는 동일한 `artifacts.save_tree`의 contiguous CPU tensor → uint8 raw bytes → SHA256 방식으로 생성된다. 따라서 file hash와 tensor hash를 서로 비교한 판정이 아니다. 이번 감사에서는 tensor 값을 재적재해 이 해시를 재계산하지 않고, 동일 형식의 sidecar 값과 저장·readback 코드 및 실행 계보를 대조했다. 저장된 consumer variant·cache·코드·40/80 counter·gate 보고가 해당 실행과 일치한다. D 성공 장부는 유한 `[3,17,512,896]`, MP4 17frame/24fps를 기록하며 출력 파일을 별도로 해시했다. 이 감사에서 latent 값을 다시 적재하거나 decode를 반복하지 않았다.
- 24개 PROBE/S/D stage 모두 단 한 번의 예약과 완료 기록을 가진다. sampler8·decode8이며 retries0이다. 장부의 시간 순서는 겹치지 않고 모든 종료는 `service_exit`, returncode0, MainPID0이다. 최종 live 조회에서 자체 pipeline/watchdog은 inactive/dead이며 자체 code 프로세스가 없고, 보호 대상의 PID·시작시각·명령 해시는 허용 장부와 일치했다.
- 모델은 기존 고정 가중치 manifest, 실제 동일 파일 경로·크기, 전체8회 loader의 tensor key/shape/dtype/precision 정책 일치로 계보를 확인했다. 이번 한정 감사에서 65GB 가중치 전체를 다시 해시하거나 메모리에 적재하지 않았다. 새 가중치 무결성 전수검사로 과장하지 않는다.

비공개 상세 근거는 `reports/independent-final-runtime-audit.json`이며 SHA256은 `27e0453773adbd642b71af105fb3d048a80b80645004bb933eb2c20955bbabe0`이다. 비공개 경로·미디어·cache·latent는 이 공개 요약에 넣지 않았다. ZIP의 CRC·추출·전송 검증은 별도 산출물 검증이며 여기의 판정에 포함하지 않는다. 영상의 실제 연속 재생 품질은 **UNVERIFIED**다.
