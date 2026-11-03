# V-001 인수 중간 상태

영상 **0/4**. 앵커0, SAM0, 모델적재0. 품질 HUMAN_REVIEW_PENDING.
실제 추론 시간·메모리·15초 비용과 동작/개체/체형/깜빡임 측정은 NOT_RUN이다.

## 선행 차단

원본·Lab사진·IG사진·Kling비교 파일의 실제 해시를 확인하고 사전 기록을 `8ad08a9`로 push했다.
보존된 A 배역 의도는 lead=Lab,partner=IG이지만 실제 원본 개체와의 관측 대응표가 없다.
의뢰 §3.2에 따라 원본240프레임을 제시해 오른쪽 앞 갈색/왼쪽 뒤 회색 중 Lab 대응을 사용자에게 확인 요청했다.
답변 전 생성하지 않는다. 원본96프레임은 발바닥 클로즈업이다. 아직 SAM 구간 게이트를 실행하지 않았으므로
기본/대체 구간의 정식 PASS/FAIL은 주장하지 않는다.

E1 공식 기본 IC-LoRA 파이프라인은 첫 단계 반해상도 후 2배 확대를 사용한다.
최종 해상도가64의 배수여야 하므로832×480의 높이가 거부된다. 설정을 바꾸지 않고 ENGINE_BLOCKED_ENV로 남겼다.
[공식 고정 코드](https://github.com/Lightricks/LTX-2/blob/e98f6d927d83c92ef2be6aec76c8440b19306e39/packages/ltx-pipelines/src/ltx_pipelines/ic_lora.py).

E2 single-GPU entry는 `--use_pe`를 생략하면 외부 prompt enhancer를 호출하지 않는다.
설치·GB10 호환성과 실제 RV2V 실행은 아직 검증하지 않았다.
[공식 고정 코드](https://github.com/bytedance/Bernini/blob/e6c2cf11843470b08491745947abcba9c3c6b079/infer_single_gpu.py).

## 확인 범위

인수 시 Spark 여유781754515456bytes. 공식 파일 metadata 기준 E1구성73752107723bytes(1.3배95.88GB),
E2 self-contained126200552703bytes(1.3배164.06GB)여서 그 시점 용량은 충분했다. 실제 설치 직전 다시 측정한다.
공식 문서의 현재 LTX2.5 안내를2.3으로 대체하지 않는다. Bernini 현재 requirements와 카드의 torch버전 차이는 설치 시 RUNTIME_DIFF로 기록한다.
가드 사본 수정/실행도 아직 하지 않았다. 기존 공통 가드·다른 작업을 변경하지 않았다.

## 남은 작업

배역 확인 → 사전 입력 기록 갱신 → 기존 CPU/heavy 실행 경로의 승인된 V전용정책 검증 → SAM 구간 → 앵커 → E2측정/2seed → 평가/뷰어/ZIP전달.
이번 중간 상태는 완료 보고가 아니며 검토 ZIP/영상 전달을 주장하지 않는다. V-002 또는 추가학습은 예약하지 않았다.
