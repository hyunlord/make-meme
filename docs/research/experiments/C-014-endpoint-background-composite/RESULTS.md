# C-014 결과: 위치 보존, 배경 복원과 경계 한계 분리

검토 ZIP의 `index.html`에서 세 RAW/POST 실제 영상을 먼저 비교할 수 있다. POST는 **CPU 후합성 파생물**이며 새 생성 모델 결과가 아니다. 새 MP4 3개/PNG99장 완료, 모델 적재·sampler·VAE·학습·GPU·설치·다운로드0. temporal=UNVERIFIED.

|사례|판정|RAW→POST 최대 중심 변화|주9시점 평균 경로오차 RAW=POST|
|---|---|---:|---:|
|I50_S1|NO_ESTABLISHED_JOINT_GAIN|0px|2.174px|
|S_S1|NO_ESTABLISHED_JOINT_GAIN|0px|2.859px|
|ON2048_S2_A|BACKGROUND_GAIN_WITH_BOUNDARY_TRADEOFF|0px|2.087px|

## 요청한 일곱 질문
1. **관측 앵커만으로 plate를 얻었다.** 실제 A0/AT의 공통 관측82,846픽셀은 RGB exact, unknown0. 전체99,840픽셀 중91,343은 A0,8,497은 AT에서 같은 좌표로 복사했다. source map과 저장 plate의 계보를 보존했다. 합성에 renderer background/sprite/중간RGB를 사용하지 않았다. 별도 oracle audit은 하지 않았다. 평가기의 기존 Reader는 plate freeze 후 marker template 초기화에 부모 background를 읽지만 합성에는 연결되지 않는다.
2. 세 RAW 모두 요청 중심44px 이내의 생성 픽셀은 그대로,44–52px는 동일 cosine feather,52px 바깥은 plate 복사다.99장 PNG 저장/readback에서 core/outside exact. 양끝도 같은 규칙이며 앵커로 통째로 덮어쓰지 않았다. 부모 PNG·MP4·앵커 hash 불변.
3. **위치와 단일 객체 판독이 유지됐다.** 세 사례 전33프레임 RAW/POST 모두 정상 단일 검출, 중심 변화0px, 부모 RAW 측정 재현PASS. I50/S는 C-013 기준, A는 C-012의 해당 단일 경로 위치 기준을 재사용했다. 임계값 변경·검출 위치로 mask 이동 없음.
4. seed2 A의 화면 전역 모자이크는 복사 영역에서 제거됐다. 그러나 보존 collar의 MAE18.510은 그대로이고 feather MAE는16.717→8.072다. 공 주변 오염은 원형 패치로 남는다. 먼 배경 MAE0은 복사식의 성질이며 독립 성능 증명이 아니다.
5. 전33축소 시트와9시점 경계 crop에서 뚜렷한 공 잘림은 보이지 않았다. **NO_OBVIOUS_CLIPPING_IN_REVIEWED_FRAMES**이며 완전한 support 포함 증명은 아니다. I50/S는 큰 새 seam 없이 배경의 밝은 얼룩이 줄었지만, 공 주변 약한 halo와 기존 띠/반점·흐린 윤곽 손상은 남는다. 특히 S의 손상을 합성 개선으로 주장하지 않는다. seed2 A는 공 위치를 따라 다른 프레임 위치에 나타나는 원형 모자이크 패치가 명확하다. 연속 popping은 미검수다.
6. 정적 배경·알려진 크기/경로 toy의 **저비용 기준선으로 유지할 근거**는 있다. 위치를 바꾸지 않고 먼 배경을 회복했지만, seed2의 경계 tradeoff 때문에 세 사례 전체의 무조건적 joint-quality PASS는 아니다. 회전/가림/동적 배경/카메라/새 체형/그림자 일반화는 미검증이다.
7. 다음 후보 하나는 **동일 후합성 뒤에도 이득이 남는 생성 중 문맥 제약**이다. seed2의 core 주변 오염을 이 고정 기준선과 비교할 이유가 있다. B-033의 제한적 교훈을 참고한 제안이며 이번에는 구현·학습·추론·mask 탐색을 하지 않았다.

## 구역별 배경 차이
reference는 이번 앵커 기반 plate. 아래는 전33프레임 구역 MAE의 평균이며 C-013의 다른 ROI 숫자와 직접 비교하지 않는다. 세 case 모두 OBJECT_CORE의 RAW/POST 차이는exact0이나, 공과 plate의 차이를 배경 품질로 해석하지 않는다. 전체 p95·>25비율·픽셀수는 METRICS에 기록했다.

|사례|보존 collar RAW→POST|feather RAW→POST|복사 outside RAW→POST|
|---|---:|---:|---:|
|I50|4.604→4.604|4.133→2.010|4.585→0|
|S|6.224→6.224|4.505→2.196|4.876→0|
|seed2 A|18.510→18.510|16.717→8.072|18.423→0|

I50/S의 원거리 얼룩 제거와 위치·관측 경계 회귀 부재는 확인했다. 그러나 원래 배경 손상이 비교적 작고 S의 객체 결함이 그대로여서, 의도적 배경 복사를 넘어선 유용한 결합 품질 개선은 NO_ESTABLISHED_JOINT_GAIN으로 보수적으로 남긴다. 형태를 고치거나 새로운 그림자·접촉을 생성한 것이 아니다. 공을 둘러싼 오염이 plate보다 나쁜 이유를 별도 모델 내부 원인으로 확정하지 않는다.

## 비용·안전·검증
합성3건·99PNG·MP4 3개와 fixture를 포함한 처리3.977초. 합성 worker 프로세스 RSS peak68,763,648bytes, systemd cgroup peak120.5M. 평가/검토물 stage도 각각37.5M/71.6M이며 worker swap0B, 세 stage 정상 종료. NumPy/BLAS/OpenCV/encoder의 지정 thread cap2, 프레임 순차 처리. 실측 비용은 이 작은 CPU 처리 범위이며 전체 모델 생성 비용이 아니다.

C-013 승인 guard 사본을 변경 없이 승계했고 시작 swap 잔량 경고를 보존했다. 각 stage 충분한 시작 관측과 실제 baseline, 증가/swapout/PSI/worker/외부 보호를 유지했다. GUARD_RUNS.json 참조. 사전97a5d4f, 코드be64d7d 이후 실행. 입력 인수 때 부모 manifest의 Spark 위치 부재는 이미 저장된 공개 manifest 사본으로 연결 수정했고 신규 자료를 생성하지 않았다. 품질 재시도0.

검증: 작은 CPU fixture,99프레임 readback,RAW hash 불변,전체화면 검출,원본MP4 byte-copy,ffprobe 416×240/33/16fps/2.0625초. 같은 세션 정적 이미지 관측이며 독립 human 평가나 연속 지각 검수가 아니다. lint/typecheck 도구는 미설치로 NOT_RUN, 설치하지 않았다. Python AST/실제 guarded 실행으로 확인했다. 과거 C-012/C-013 및 BLOCKED 이력은 변경하지 않는다.
