# 사전 대조 설계와 판정 경계

생성 전 고정. 결과 칸은 아직 미실행이다. 동일3과제 개발 패널, 단일seed이며 프레임을 독립 반복으로 세지 않는다.

| 비교 | 바뀌는 것 | 유지하는 것 | 검사하는 설명 |
|---|---|---|---|
| B027 BASE → METHOD 6case | generated query의 이미지 attention 출력 계수 | 입력16leaf·noise·RNG·모델·CFG·sampler·precision·caption | 한 경로의 위치 재가중이 외형/동작/형태/장면 결합에 유용한가 |
| METHOD → CONTROL animalR1,vehicleR1 | E의 공간 배정만 반H/반W cyclic shift | E histogram·평균·시간·lambda·NFE와 모든 입력 | 대상 위치와 맞춘 배정 때문인가, 단순 조건 변조 때문인가 |
| OFF/lambda0 CPU fixture | 코드 활성화 | 작은 고정 함수 입력·weights | 기준 함수 연결 보존. 전체14B 수치/시각 동일성의 증거 아님 |

CONTROL의 공간 겹침은 support.json에서 실행 전에 공개 요약한다. 다른 shift를 시험해 더 유리한 대조를 고르지 않는다. source mask는 edited RGB 정답이 아니며, 편집 후 더 넓어진 실루엣의 합당한 가림은 별도로 판단한다.

기존 B028은 기준선 선택에 사용한 역사 비교다. METHOD 결과를 본 뒤 B027/B028을 case별로 교체하지 않는다. 기준선의 문제와 방법의 문제를 모두 보존한다.

## 결과 기록 예정

METHOD/BASE/CONTROL의 외형·동작·형태·보호 장면 항목별 개선/동일/악화와 근거 프레임을 실제 출력 후 기록한다. 임의 joint score·유의성·identity accuracy는 만들지 않는다. METHOD~CONTROL이면 공간 위치 설명은 미입증이다. 외형만 좋아지고 동작/형태가 나빠지면 trade-off이며 성공으로 합치지 않는다. 현재 새 sampler0, temporal=UNVERIFIED다.
