# 2026-10-24 — B-016 검토, 추론 설정 탐색에서 학습 데이터 설계로 전환

## 확인 범위

원격 `dd98d1f226b72e9701bcc12d530c032c3683e9cd`의 B-016 RESULTS와 MODEL_PATCH.diff, branch HEAD를 조회했다. patch는 optional scalar와 reference H override·scalar 관측을 추가했다. 실제 실행 보고는 40step/80forward·전체 모델 연결·최종latent/17f24fps 출력, 착석·후기 얼굴/귀/목 손상 지속, 전신 FAIL·개체 UNCERTAIN·temporal UNVERIFIED다. 코드 diff/기록 확인과 검토자의 Spark 재실행은 다르다.

제공 ZIP `make-meme-B-016-20261024-final.zip`에 container/Python 두 방식으로 접근했으나 ClientError가 나서 bytes·SHA·CRC·363payload·영상 자체를 독립 검증하지 못했다. 보고값150,796,636bytes/SHA `1fe40f6821cd04f76ee82389e107d2e41196578be7cb5f8e6384cfa37c88e3a7`를 직접 검증한 값처럼 쓰지 않는다.

## 판단

1. 현재 ALG와 H120은 기본 경로로 승격하지 않는다. 향후 baseline은 보존된 CFG/H0다. 한 seed의 두 실패는 모든 추론기법이 무효라거나 학습데이터 부족이 유일원인이라는 증거가 아니다.
2. 로컬 상용급 품질·생성 원리 연구라는 목표에서, offset/blur 숫자 탐색을 반복하는 것보다 입력·target을 정의하고 제한된 학습 가설을 준비하는 편을 선택한다.
3. 다음 단계의 함정은 R의 자세만 바꾸고 D=Y를 유지한 자기 재구성을 cross-identity 훈련이라고 부르는 것이다. 깨끗한 driver에 target 외형이 이미 들어 있으면 R 없이도 loss를 낮추는 shortcut이 가능하다. 이는 학습 배선 smoke에는 허용하되 개체/자세 분리 근거와 구분한다.
4. 실제 Lab의 정답 동작 영상이 없으면 다른 강아지나 실패한 Lab 생성물을 Lab 정답으로 쓰지 않는다. 자연 동작 데이터와 의인화된 직립 춤 사이의 분포 차이도 별도다.

## 공식 근거 확인

SCAIL paper §3.2는 다른 개체로 합성한 영상을 driving으로, 실제 원본을 denoising target으로 쓰는 reverse-driving 구성을 설명한다. 이 방법은 기존 연구이며 새 아이디어가 아니다. 본문에 포함된 외부 이미지/생성 서비스는 B에 자동 도입하지 않는다.

공식 Wan README Training은 `GT.mp4`, driving video/mask, reference image/mask와 caption을 요구하고 실제 training은 SAT branch로 연결한다. 동일 README의 MotionPair는 form/terms 기반 접근이다. 코드 라이선스가 데이터 권한을 보장하지 않으며, 공개됐다는 문구만으로 동물 paired 영상의 실제 확보를 주장하지 않는다.

APT-36K는 animal pose/tracking 자료이며 clip당15frame이라는 공식 정의가 있다. 연속17frame24fps 학습영상을 자동 제공하거나 개체를 바꾼 정답 target을 주는 자료로 취급하지 않는다.

## 다음 작업

[B-017 PLAN](../experiments/B-017-paired-animal-data/PLAN.md)을 등록했다. 문헌 조사만 하고 끝내지 않도록 기존 허용 자료의 실제 inventory·R/D/Y manifest·가능한 최소 case·CPU validator와 공식 training interface mapping을 요구한다. 진짜 cross-ID pair가0이면0으로 남기고 smoke case와 분리한다. 부족하면 필요한 자료와 권한을 구체적으로 정의한 다음 한 경로를 선택한다.

B-017은 PLANNED/NOT_RUN. 이번 등록에서 신규 모델 다운로드·데이터 수집·생성·학습은0회다. 최대3시간 CPU 중심 작업을 제안하며, 실제 backward/LoRA나 synthetic driving 생성은 후속 실행 범위로 남긴다. 실제 착수·종료 시 HISTORY.md/ROADMAP.md에 이 결정을 링크한다.

이번 원격 수정은 PLAN과 결정문 두 파일 추가뿐이며 기존 결과·코드·공통이력·모델·A 트랙을 변경하지 않았다. 새 연구가 논문 기여가 되려면 이후 허가된 데이터, shortcut 방지, 미사용identity/motion 평가와 강한 baseline 대비 증거가 필요하다.
