# B-002 재현 경계

개인 사진·원본 영상·미공개 출력은 공개 저장소에 포함하지 않는다. 같은 입력 접근 권한이 있어야 픽셀 수준 재현이 가능하다. 해시와 별칭만 공개한다.

- upstream: `f39d731a3e318d25b725eb3389cfddb184619842`
- weights: `Wan-AI/Wan2.1-VACE-1.3B` revision `574e6a744642ce3bee319afc31496b88bde8aac4`
- 기존 B-001 격리 환경의 Python/PyTorch/BF16 CUDA/SDPA를 재사용한다. 신규 설치·학습·adapter 없음.
- `resolved_design.json`과 실제 로컬 config를 대조한다. 실제 실행 스크립트는 commit `9d81447919469c2cdeda69a9d7da25515a5b55f0`의 `code/`에 고정되어 있다. 최종 public `code/`에는 import 정렬만 적용했으며 import집합/나머지AST 일치를 검사했다. 원격 실행 스크립트는 변경하지 않았다. 참조 준비 스크립트만 private 절대경로를 CLI 인수로 바꾼 배포본이다.

```sh
# 권한 있는 로컬 입력/가중치/기존 baseline config를 준비한 뒤 실행한다.
python code/prepare_reference.py "${RUN_ROOT}" "${DATA_ROOT}/LAB_PHOTO.jpeg" "${DATA_ROOT}/source/000.png"
python code/assemble_configs.py "${BASELINE_CONFIG}" "${RUN_ROOT}" "${DEADLINE_UTC}"
# 실행 폴더에는 scripts/,configs/,reports/ 구조를 유지한다.
# PREREGISTRATION.json에는 실제 사전 등록 commit/push 확인만 기록한다.
# scripts/launch_video.py CONFIG LABEL 을 순서대로 실행한다. 자동 재시도 없음.
# 현재 단계의 원래 deadline 이후 재개하려면 새로운 승인 범위가 필요하다.
python code/review_outputs.py "${RUN_ROOT}" "${PREVIOUS_RUN_ROOT}"
```

R-bg의 reference mask는 배경 교체에만 쓰고 VACE video mask는 모든 프레임 흰색으로 유지한다. 마스크는 수동 윤곽과 비학습 처리이며 자동 분할 성능을 측정한 것이 아니다. 17프레임의 마지막 sample은16/24초, 컨테이너 길이는17/24초다. 인코딩 성공과 시간 품질 관찰은 다르다.
