# 사전 결정 — 같은 차량 잔여를 튜닝하지 않고 고정 규칙을 이동한다

B033의 작은 접촉 오염 감소는 후보이지 기본 채택 근거가 아니다. 같은 차량·마스크·계수를 조절하면 사례 적합과 방법 효과를 분리하기 어렵다. 따라서 B027–033 생성/방법 선택에 쓰지 않은 두 source/target 조합을 실제 입력만 보고 고정했다. 기존 car-roundabout의 인접 프레임이나 car-shadow의 다른 사진을 새 test라고 부르지 않는다.

강체는 car-turn→classic-car, 비강체는 hike→lady-running이다. 입력 GT와 실제 관측으로 category/track을 확인하며 사람 신원 인증은 하지 않는다. 두 앵커 모두 생성 전에 고정되고 실패해도 더 좋은 입력으로 채우지 않는다. 데이터셋 사전학습 중복은 UNKNOWN, 결과 확인 후에는 개발 사례로 편입한다.

방법은 B033 clean_constraint byte 동일, support는 B032의 고정식이다. BASE 이후 target 주석에 의존하므로 두-pass/output-mask-assisted 비용을 숨기지 않는다. 이번 campaign 비용, 기존 BASE+support가 있을 때 증분, 가상 one-pass 제품 비용을 분리한다. 성공하더라도 자동 채택하지 않고 효과/회귀/무효를 보고 종료한다.
