# V-002 RESUME_R1 사전 계획

착수 2026-11-04T18:12:33Z (2026-11-05 03:12:33 KST). 부모 9f78153c05459fbb5a42867658b70ed1cf315322. 첫 실행 코드·입력·판정은 제자리 수정하지 않는다. r1 의뢰서와 동봉 JSON을 실행 계약으로 사용한다.

## 고정 실행
기존 73프레임 [240,313), 캐스팅/앵커/SAM/depth/입력 그대로 hash 검증 재사용. E1 두 출력 SAM → M1/M2/M3 → SAM 선택 → 중간 전달 → 후보 있을 때14B BF16변환/1step/생성 → LTXcanny → 최종 측정 전달. seed20261103, VACE50step CFG5 shift16 기존Euler, LTX11step 강도1.0/canny92/200 유지. 품질 HUMAN_REVIEW_PENDING. imagegen/학습/Bernini/새depth 0회. 영상최대5,14Bprobe1,품질재시도0.

## r1 운영 변경
heavy 전60초 간격 외부 GPU와 알려진 외부 배치 부모 관측. 최소180초 구간과 마지막3표본 모두 없음을 요구한다(첫t0후60/120/180초). 단계120분/누적180분 대기상한. 실행 중 새외부GPU는 CONCURRENT_EXTERNAL_GPU 기록 후 현재 생성완료, 다음단계 다시대기. OOM/NVRM첫오류/가용12GiB30초/PSI25%60초 등 안전중단은 유지. worker MemoryHigh=Max100GiB. 공통가드가 아닌r1사본만 수정.
helper 현재 존재, 각heavy직전 지정sudo -n만 호출. 실패하면 SAM/1.3B진행,14B/LTX생략. slotkeeper는문서화된범용interface가있을때만사용. CPU상시서비스는GPU작업아님,메모리만기록.
14B변환은선택후CPU순차/낮은우선순위/CUDA비활성으로원본보존,모든tensor BF16bit일치검증. BF16loader확인후pagecache포함peak재추정<=100GiB일때만실행. 기존128GiB판정은당시원본적재평가로보존.

## 예산과 기록
실행7시간(대기제외), 마지막30분전달. 기본종료2026-11-05T01:12:33Z, 실제외부GPU대기만추가최대3시간, 절대종료04:12:33Z. 실행중예상시간으로새생성착수판단. Mac야간heavy금지기존원칙에따라실제모델/변환/포장은Spark에서,Mac은가벼운기록/전달. 모델작업과환경import시험병렬0. 자체GPU흐름은root만운영.
누락측정은null/NOT_RUN,fixture와실측분리. 14Beligible66/73,최고castIoU,eligible M1이0.02내면M1;M2/M3정확동점M2 유지. 재생/기술검증은사용자품질판정대체아님.

## 인수 확인
입력808+369+6파일 hash일치,재제작0. helper실제호출APPLIED. slotkeeper는FLS디렉터리/세션구조에결합돼문서화된타프로젝트interface없음,미사용/서비스변경0. 첫SAM전18:13:49–18:16:49UTC 4표본모두GPU/배치부모없음. 첫SAM50.35초정상종료.
