# 실행 전 검토 범위

독립 읽기 전용 검토는 pinned SCAIL image cross-attention의 `img_x`가 text 합산·output projection 전에만 바뀌는지, 실제 block metadata의 generated 구간, OFF/0 원래 함수 보존, producer cache 검증, 40step/80forward 및 latent 선저장을 확인했다. 소스 검토에서 blocking defect는 발견하지 못했다. 이는 CPU 실행이나 GPU·영상 품질 검증을 대신하지 않는다.

이후 실제 CPU 지도 생성에서 AST가 config의 `WanSCAILModel` 이름을 찾다가 `StopIteration`으로 중단했다. pinned `model_scail2.py`의 실제 클래스는 `SCAIL2Model`이므로 그 이름만 수정했다. 지도 연산·source SHA·실험 설정은 변경하지 않았으며 이 실패 시점 GPU 사용은0이었다. 소스 검토 PASS를 실행 PASS로 소급 해석하지 않는다.

LSP 도구는 네 파일 요청에서 `Transport closed`를 반환했다. 따라서 LSP 정적 진단은 `UNAVAILABLE / NOT_CLEAN`이며 compile·CPU 계약 검사와 구분한다. 환경 재설치·경고 억제·전체 타입 리팩터링은 하지 않았다.

실제 지도 생성, CPU 계약 결과, 사전 고정 해시와 첫 forward의 범위/통계, 최종40×80 gate count는 각각 별도 실행 근거로 기록한다.
