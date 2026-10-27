# 검증 수준과 도구 제한

실행 전 종료 정책 CPU fixture14개를 구현 담당·리뷰어·부모가 실행해 모두 통과했다. Spark의 CPU-only transient unit에서 running→exited metadata 유지→자체 stop→inactive/GC를 실제 관측했다. 이 검증은 GPU 종료 재현이나 과거 원인 확정이 아니다.

BASE artifact의 파일/sidecar/tensor 해시, FP32 shape·finite·생성40/80 계보, FINAL_ONLY의 M=0/source exact·M=1/BASE exact, S/T core coverage와 고정 E/M을 확인했다. CPU_ARTIFACT_VALIDATION의 E0/E1 필드는 latent 혼합 mask M의 endpoint 검사 명칭이며 RGB 전영역 품질 지표가 아니다.

사전 검사 중 존재하지 않는 helper 이름을 import한 inspection 명령 오류와 공식 모듈 import 뒤 CUDA initialized=False라는 가정의 실패는 기록에 보존했다. 명시적 CUDA tensor 연산이나 모델 worker를 추가 실행한 것은 아니다. 검사 목적과 무관한 초기화 가정을 안전 기준 완화로 바꾸지 않았다.

부모의 LSP 오류 진단 요청은 `Transport closed`로 실패했다. Mac PATH에 ruff/basedpyright가 없어 CLI lint/typecheck는 NOT_RUN_TOOL_UNAVAILABLE이다. 이를 진단 CLEAN으로 보고하지 않으며 설치/플러그인/환경 복구로 범위를 확대하지 않았다. 실제 실행에 영향을 줄 수 있는 종료 신원·artifact·shape·횟수 계약은 CPU 검사 및 runtime 결과로 별도 확인한다.

영상 파일 decode/프레임 수/브라우저 조작 검증과 실제 속도의 연속 시청은 별개다. 이번 정적 이미지·전체 프레임 배열 검토는 독립 인간 ground truth가 아니며 temporal=UNVERIFIED를 유지한다.
