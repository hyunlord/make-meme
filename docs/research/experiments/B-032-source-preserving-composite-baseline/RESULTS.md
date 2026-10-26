# B-032 결과 — 원본 복원은 도움이 되지만 편집 내부 오염은 남는다

상태 COMPLETED_CPU_COMPARISON / 기술 계약 PASS / 보호 장면 PARTIAL / 완전한 편집 성공 미입증. B031 raw의 결합FAIL과 animal/human 앵커실패·영상NOT_RUN은 변경하지 않는다.

## 실제 해결된 것과 남은 것

SOURCE / 기존 B031 RAW / FIXED_ENVELOPE / MASK_ASSISTED 전체17장과 local0/8/16의 동일 crop을 정적으로 관찰했다. 두 합성 모두 큰 하단 차량 그래픽의 대부분을 source 도로로 복원하면서 높은 은색 차체·큰 창·세로 후미등과 기존 거친 회전 진행을 유지했다. 새 움직임이나 외형을 생성한 결과가 아니라 기존 generated 영역을 보존한 것이다.

| 축 | FIXED_ENVELOPE | MASK_ASSISTED |
|---|---|---|
| 큰 도로 그래픽 | 크게 줄었으나 사각형 내부의 긴 적색/흰색/검정 조각이 남음 | 더 작아졌으나 뒤쪽 바퀴 아래 쐐기 모양 조각이 남음. local0/8/16 및 전체시트에서 지속 |
| target형 외형·거친 회전 | 기존 raw의 주요 차체와 회전 진행 유지 | 기존 raw의 주요 차체와 회전 진행 유지 |
| 원본 보호 장면 | E0 영역 exact 복원; 안쪽의 생성 배경은 남음 | E0 영역 exact 복원; 작은 edit footprint로 더 넓은 원본을 사용 |
| 원본 차량 잔상/잘림 | 뚜렷한 이중 주차체는 보이지 않음; annotated support undershoot0 | 뚜렷한 이중 주차체는 보이지 않음; annotated support undershoot0 |
| 경계·접촉·그림자 | 사각 경계의 배경 전환, 어두운 접지/그림자와 오염 strip 잔존 | 바퀴 아래 오염, 밝기 전환과 접촉 그림자 관계 UNCERTAIN |
| 자동화 | source GT+A0 support 제공 조건의 고정식 | 출력 기반 agent 수동 polygon 필요, MASK_PARTIAL |

완전한 그래픽 제거는 두 방법 모두 FAIL이다. 작은 조각을 없애려고 ROI·r·feather·polygon을 사후 조정하지 않았다. 별도 inpaint·색보정·warp·SR·보간은0이다. 큰 이중 차량이 보이지 않는다는 정적 관측은 모든 원본 경계 잔상이 없다는 보증이 아니다. 얇은 antenna/roof rail·정확한 접지·가림은 불확실하며 독립 인간 GT가 없다.

## 실제 계산 계약

사전 고정 commit175453622e52146f68c1af5e7336c6c75e1346b6 뒤 CPU에서 두 결과를 만들었다. Source17 GT support+A0 bbox와 각 방향10% margin으로 [147,162,754,423) 고정영역을 얻었다. 안쪽8px feather다. MASK_ASSISTED는 source+실제 generated 차량 support union, radius11 Euclidean dilation, 바깥4px feather를 사용했다. H는 접촉/cast shadow 구분 불확실로 empty다.

모든17프레임·두 결과에서 E0 source/E1 generated의 float exact와 저장 PNG의 uint8 endpoint exact를 확인했다. 원본 uint8의 float 왕복 반올림 오차를 피하려고 E0는 원본 bytes를 명시적으로 복사했다. 새 MP4는 손실 인코딩이므로 decoded MP4 pixel exact를 주장하지 않는다.

- FIXED: nonzero158427px/frame, core144795px/frame.
- MASK: nonzero92462~99110px/frame, core88256~94642px/frame.
- 주석된 source/target support의 core 밖 pixel0. 이는 불확실한 실제 얇은 구조까지 coverage100%라는 뜻이 아니다.
- 기존 파일의 입력 SHA 전후 동일. 새 파생영상2개는 각896×512·17frame·preview24fps다. source_fps=null/timebase_assumed=true를 유지한다.
- 신규 GPU worker·이미지·encoder·sampler·VAE decode·학습·설치 모두0. 기존 raw tensor CPU 로딩은 VAE decode가 아니다.

독립 read-only agent도 bbox/radius·34개PNG·edit map을 별도 계산해 byte 일치를 확인했다. 정적 관측은 agent 검토이며 독립 인간 평가가 아니다. 실제 연속 시청이 없으므로 temporal=UNVERIFIED다. 경계 흔들림의 지각 품질을 정적시트만으로 PASS하지 않는다.

## 비용과 다음 한 가설

수동/agent polygon 준비345.005초(약5.75분), CPU runner3.900초(두 합성과 새MP4 인코딩 포함), 별도 process wall4.15초·최대RSS515997696bytes였다. 기존 B031 생성 비용을 없앤 것이 아니다. [COSTS](COSTS.md), [SUPPORTS](SUPPORTS.md), [재현](REPRODUCE.md), [한국어 해설](../../lessons/B-032-source-preserving-composite.md).

원본 복사만으로 원거리 장면과 그래픽의 대부분을 값싸게 복원할 수 있다는 한 사례의 근거다. 그러나 오염이 target 근처 edit core 안에 겹치면 단순 합성은 그대로 보존한다. 다음 한 가설은 **target/접촉 주변의 편집 내부에서도 source 문맥을 반영하는 생성 중 알려진 영역 제약이 잔여 그래픽과 경계를 줄일 수 있는가**이다. 후속 방법은 RAW뿐 아니라 이번 저비용 MASK_ASSISTED와 노동비용까지 비교해야 한다. 이번에는 구현·샘플링하지 않았다. 차량 한 사례를 일반 편집 성공으로 확대하지 않는다.

작은 ZIP은 기존SOURCE/RAW영상을 변경 없이 포함하고 새 합성영상2개·support·전체시트·확대·viewer·재현을 포함한다. 큰raw/latent/weights는 제외한다. 실제 검증은 DELIVERY에 별도 기록한다.

## 검토 도구의 한계

기존 SOURCE MP4는 Chrome에서 녹색/자홍색으로 표시되는 문제가 관찰됐다. 기존 영상 bytes는 변경하지 않았으며 정확한 RGB 전체 프레임 시트를 함께 제공한다. 데스크톱·태블릿·모바일 뷰어의 링크·조작 확인은 영상 시간 품질 검수를 대신하지 않는다. Python 단위검사와 compileall은 통과했지만 ruff/pyright가 설치되어 있지 않아 해당 lint/type 검사는 NOT_RUN이다.
