# CPU 실행 증거

최종 명령은 [REPRODUCE](REPRODUCE.md)의 `CUDA_VISIBLE_DEVICES='' SCAIL_MODEL_SOURCE=.../wan/modules/model_scail2.py` 환경에서 두 테스트 파일을 함께 실행했다. 기존 pinned Torch 환경이며 새 설치0, GPU0이다.

도구가 반환한 실제 stdout (exit code0):

```text
..........                                                               [100%]
10 passed in 0.75s
```

기존 계약4와 방법 계약6을 합한 실행이다. 원래 source에서 추출한 작은 CPU 연산과40개 tiny hook은 실제14B 전체 forward 수치 검증이 아니다. 세 실제 source map은 별도 CPU CLI로 생성하고 metadata/hash와 검토 시트를 남겼다. initial AST 클래스 불일치 및 test env 누락은 REPRODUCE에 실패로 보존했다.
