# 출력 전 관측

Root Codex가source전체33장및fixed9를실제정적으로검토했다. 독립human평가/연속재생이아니며temporal=UNVERIFIED다.

## horsejump-low
0–16 우향접근/보이는다리교대.18–20 앞다리들림과rider전방기울기.21–25 장애물bar와기둥에다리일부가림.26–29 머리낮아지고앞다리가재등장하며하향.30–32 몸통하강이나hoof접촉UNCERTAIN. rider/blue-whitebar/planter를별도보호항목으로본다. 해부학적좌우/관절GT를만들지않는다.

## lucia
측면우향보행,카메라추적으로인물은대체로중앙이고배경은좌측이동한다. bench가우측등장한다.0–4/14–18/30–32 다리겹침,6–10/20–24 넓은보폭이라는거친사건을비교한다. blackdress/yellowbackpack/whitefootwear 보존을본다.치마와풀의가림때문에다리상부와발접촉은UNCERTAIN이다. 화면위치만으로보행정확도를평가하지않는다.

Tracker의가시성은정확성보증이아니다. 별도TRACK_REVIEW에서명백배경이탈만제외한다. 작은overlay에서root가luciaID3을4로오독한관측은raw좌표확대로정정했고ID4는유지했다.

## 별도 cross-ID: 실행 전 수동 대응 범위

기존 C-001 개 원본과 원래 두 편집 앵커를 직접 비교했다. nose, 화면 왼쪽 eye, 화면 오른쪽 eye의 세 표면점만 양끝에서 제한적으로 식별 가능하다. 귀나 보이지 않는 발은 추가하지 않는다. 이 진단은 HEAD_ONLY이며 해부학적 관절·발 접촉의 정답이 아니다. 원 832 좌표의 수동 오차는 약 ±4px, target 전체 bbox 경계는 털 때문에 약 ±5px다. 416 좌표는 pixel-center 변환 `(q+.5)*.5-.5`로 고정한다.

원본 bbox는 기존 selected SAM mask의 정확한 bbox, target bbox는 수동으로 보이는 개체를 둘러싼 axis-aligned bbox다. 이는 비강체 대응이나 3D 정렬이 아니다. source tracker의 실제 끝점과 수동 눈·코의 차이를 별도로 보고, retarget 수식이 target 끝점에 맞았다는 사실을 추적 정확성으로 해석하지 않는다. 기존 종료 앵커의 낮은 자세 충돌을 보존한다. 수동 검토 시간은 별도 timer가 없어 null이다.
