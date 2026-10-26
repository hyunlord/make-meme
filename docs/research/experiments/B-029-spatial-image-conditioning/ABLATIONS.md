# 사전 대조 설계와 판정 경계

아래 설계는 생성 전에 고정했다. 결과는 완료된 출력부터 구분해 기록한다. 동일3과제 개발 패널, 단일seed이며 프레임을 독립 반복으로 세지 않는다.

| 비교 | 바뀌는 것 | 유지하는 것 | 검사하는 설명 |
|---|---|---|---|
| B027 BASE → METHOD 6case | generated query의 이미지 attention 출력 계수 | 입력16leaf·noise·RNG·모델·CFG·sampler·precision·caption | 한 경로의 위치 재가중이 외형/동작/형태/장면 결합에 유용한가 |
| METHOD → CONTROL animalR1,vehicleR1 | E의 공간 배정만 반H/반W cyclic shift | E histogram·평균·시간·lambda·NFE와 모든 입력 | 대상 위치와 맞춘 배정 때문인가, 단순 조건 변조 때문인가 |
| OFF/lambda0 CPU fixture | 코드 활성화 | 작은 고정 함수 입력·weights | 기준 함수 연결 보존. 전체14B 수치/시각 동일성의 증거 아님 |

CONTROL의 공간 겹침은 support.json에서 실행 전에 공개 요약한다. 다른 shift를 시험해 더 유리한 대조를 고르지 않는다. source mask는 edited RGB 정답이 아니며, 편집 후 더 넓어진 실루엣의 합당한 가림은 별도로 판단한다.

기존 B028은 기준선 선택에 사용한 역사 비교다. METHOD 결과를 본 뒤 B027/B028을 case별로 교체하지 않는다. 기준선의 문제와 방법의 문제를 모두 보존한다.

## 순차 결과와 해석

| 사전 선택 대조 | METHOD | shifted CONTROL | 판정 범위 |
|---|---|---|---|
| animal R1 | 작은 원형 하단 배지, 밝은 source 계열 개체 | 큰 빨강/흰 배지, 밝은 source 계열 개체 | 장면 오염 양상은 다르나 target 외형 교체는 양쪽 FAIL |
| vehicle R1 | 큰 차량 후면 그래픽, 은색 source Mini형 혼합 차체 | PENDING | CONTROL 출력 후 확정 |

animal의 전체17장/local0/8/16에서 배지 차이를 확인했다. METHOD의 장식이 작아 보이는 사실만으로 대상 위치의 identity 전달이 성공했다고 할 수 없다. 정확한 장식 면적이나 동작 오차는 측정하지 않았다. source-like 출력은 motion/scene 보존의 일부 관측일 수 있지만 identity-change 성공은 아니다.

human R1은 BASE보다 의상 형태가 일부 정돈됐으나 R2의 크게 들린 치마·얼굴 가림이 유지됐다. human에는 대조군 예산을 사후 추가하지 않는다. 차량 METHOD의 전체17장도 확보했고 CONTROL은 진행 중이다.

METHOD/BASE/CONTROL의 외형·동작·형태·보호 장면을 분리한다. 임의 joint score·유의성·identity accuracy를 만들지 않는다. METHOD~CONTROL이면 위치 설명은 미입증이다. 외형만 좋아지고 동작/형태가 나빠지면 trade-off다. 실제 연속 시청을 하지 않았으므로 temporal=UNVERIFIED다.
