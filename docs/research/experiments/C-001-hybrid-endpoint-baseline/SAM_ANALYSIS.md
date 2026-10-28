# SAM 분석 기록

실제 GPU 분석 완료: source 두 구간 각각33프레임과 native 앵커 네 장, 총70개 RGB 입력. 기존 ComfyUI SAM3.1 integration revision `5cc4b870094c89090db54bd8d12649dcaf89f2ba`와 기존 `sam3.1_multiplex_fp16.safetensors`를 직접 offline 호출했다. ComfyUI 서버를 시작하지 않았다. checkpoint metadata는 비어 있어 원래 upstream weight revision은 **UNKNOWN**이다. 파일명만으로 공식 upstream checkpoint revision을 추정하지 않는다.

source query는 `car`, `dog`였다. source 첫 프레임의 별도 DAVIS GT와 가장 많이 겹치는 후보를 `edited_subject`로 선택했다. 첫 프레임 IoU는 차량0.983681, 개0.952602이며 선택 보조 수치다. 전체 tracking 정확도나 target 정체성 점수가 아니다. source mask를 GT로 대체하지 않았다. 선택한 track은 양쪽33프레임 모두 비어 있지 않았다. 원래 packed masks도 full 산출물에 보존했다.

네 앵커는 별도 detection으로 처리했다. `edited_subject` 배역은 명시적으로 연결했고 원본과 앵커를 이어 붙인 tracking으로 cross-domain correspondence가 해결됐다고 하지 않는다. bbox·중심·면적·mask·overlay·선택 정보를 저장했다.70 mask와70 overlay 이미지가 실제로 decode되는 것을 확인했다.

두 에이전트의 제한된 정적 spot check에서 대상을 대체로 덮는 mask를 확인했다. 세부 roofrail/털 경계와 전체 clip의 가림·tracking 품질을 완전 검증한 것은 아니다. 연속 tracking 품질은 UNVERIFIED다. 비어 있지 않은 track이 이어졌다는 사실을 정확한 개체 동일성으로 해석하지 않는다.

분석 자체 wall time38.479초, 보호 실행41.383초. 관측 peak cgroup current6.205GiB, 최소 MemAvailable104.704GiB. 작업별 swap.current/max0, OOM/OOM-kill/high events0, 전역 swap1,040,384B로 안정적이었다. 실제 guard는 COMPLETE/CLEAR로 종료하고 GPU 자원을 회수했다. 이 관측값은 공식 안전성 보증이나 완전한 CUDA 메모리 회계가 아니다.

Fallback0, 새 설치0, 새 weight 다운로드0, 추가 SAM sweep0. 이 분석 결과는 영상 모델 입력에 사용하지 않았다. `SAM_CONDITIONING_NOT_RUN`이다.
