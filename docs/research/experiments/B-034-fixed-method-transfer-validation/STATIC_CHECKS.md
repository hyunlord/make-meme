# 코드 검사 범위

- 새 실행 Python 모듈의 syntax compilation: PASS.
- B-033과 B-034 clean_constraint.py byte SHA 일치: PASS.
- 기존 B-033 네 CPU 계약 fixture를 그대로 재사용, 실제 pinned UniPC에서 실행: PASS. 기능 범위는 작은 CPU tensor이며 전체 모델 수치 동등성이나 영상 품질의 증명이 아니다.
- local PATH에서 `ruff` 및 `basedpyright`를 찾지 못했다. lint/type 진단은 NOT_RUN_TOOL_UNAVAILABLE이다. 이번에 패키지를 설치하거나 경고를 억제하지 않았다.
- 공식 upstream의 AMP/config deprecation 경고는 기존 경로에서 관측되며 실행 성공과 별도로 보존한다.

실제 입력 freeze, GPU 실행, 출력 품질은 별도의 receipt와 RESULTS를 따른다.
