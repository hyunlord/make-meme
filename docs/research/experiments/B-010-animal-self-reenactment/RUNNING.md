# B-010 실행 기록

상태 RUNNING / GPU NOT_RUN. 시작 원격HEAD `646ba5415b9af9b5b2469a4a0455c06d143366d4`. 기존 격리 문서checkout과 A/B-009 자산을 보존한다. 보수적 종료 deadline2026-10-23 08:00UTC.

1. IN_PROGRESS: CPU STATIC COPY 및 보이는 표면점 관측·오차·사전 평가가능성 판단(30분 상한).
2. PENDING: 입력/prompt/기대 변경 집합·최소 코드·회귀 검증·공개 사전 고정.
3. PENDING: 관측가능성 통과 시 P1→조건 비교→PROBE1→S1→D1; 선행 실패 후 후속 미실행, 재시도0.
4. PENDING: 원본/STATIC COPY/출력의 전체17프레임 및24fps 비교, coverage/invalid·정적변화 평가와 한국어 해설.
5. PENDING: 결과/HISTORY/ROADMAP commit/push·비공개 ZIP CRC/해시·양호스트 전달 및 프로세스 종료 확인.

직립 자체는 성공 기준이 아니다. reference/text가 바뀌는 자기 재현 진단이며 B-009는 맥락용이다. source 움직임이 관측오차보다 작으면 DIAGNOSTIC_INSUFFICIENT로 남기고 추가구간이나seed를 고르지 않는다. 마스크/저역필터/학습/새모델/외부생성0. 기존72GiB시작/24GiB런타임·swap0가드를 유지한다.
