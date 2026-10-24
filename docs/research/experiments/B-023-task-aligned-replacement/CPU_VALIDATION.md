# CPU 준비 검증

- CPU 전용 `CUDA_VISIBLE_DEVICES=""`에서 최초 `wan.utils.scail_utils` package import가 `wan/__init__.py → modules/t5.py:482 → torch.cuda.current_device()`의 eager 초기화로 실패했다. 오류: `RuntimeError: No CUDA GPUs are available`. 모델 구성·가중치 적재·P·PROBE·sampler는 실행되지 않았다.
- 수정: 같은 pinned `wan/utils/scail_utils.py`를 `importlib.util.spec_from_file_location`으로 직접 import했다. helper 내용·연산은 수정하지 않았다.
- 후속 CPU 실행 성공: 원래 WHITE mask prefix가 기존 cache와 exact 일치, BLACK 파생 prefix 생성. RED 37209 pixel 보존, WHITE 421543 pixel만 BLACK으로 변경.
- 새 cache의 t4/t10만 변경, 나머지14 tensor leaf exact 동일. 양 CFG replace_flag False→True. 원본 cache 불변.
- 4개 CPU 테스트 PASS (0.71s): 실제cache계약,입력계약,공식replacement/animation mode식,기존sampler추출. 컴파일 PASS.
- 이 검사는 full14B 실행/시각품질 성공이 아니다. GPU 0회 상태에서 사전 기록.

- 현재 ruff/basedpyright executable은 기존 Mac/Spark 실행 환경에서 확인되지 않았다. 신규 설치하지 않았으며 lint/typecheck NOT_RUN, 기존 타입 진단 NOT_CLEAN을 유지한다. 컴파일/계약 검사 및 실제 실행 성공과 별도다.
