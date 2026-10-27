# B-034 생성 전 고정 공개 과제

2026-10-27 입력만 보고 선정했다. B-027~033의 dog→dog-gooses, dance-twirl→dance-jump, car-roundabout→car-shadow와 다른 두 source/target 조합이다. 새 출력 확인 뒤 이 두 입력도 개발 사례가 되며 최종 미사용 test로 재분류하지 않는다. 사전학습 중복 여부는 UNKNOWN이다.

| case | source | target | 생성 전 구분 특징 | source 사건 | 보호 장면 |
|---|---|---|---|---|---|
| rigid_R1 | car-turn track1 f0..16 | classic-car track3 f0 | 어두운 긴 노출 후드·큰 외부 바퀴·낮은 열린 운전석. source의 은색 높은 SUV와 구별 | 도로 곡선을 따라 접근하며 화면 왼쪽으로 이동하고 커짐; 앞면에서 측면 노출이 증가 | 산·초원·나무·도로 경계 기둥과 도로 |
| nonrigid_R1 | hike track1 f0..16 | lady-running track1 f0 | 짧고 밝은 머리·빨강/초록 무늬 상의·검은 하의. source의 회색 상의·큰 배낭과 구별 | 오른쪽으로 걷고 양 다리의 지지/진행 단계가 바뀜; 몸통은 대체로 직립 | 바위·산비탈·길과 주변 지형 |

두 source 모두 연속17장의 실제 DAVIS frame과 indexed GT mask를 사용한다. RGB Lanczos / mask nearest의 B-027 aspect-fit으로896×512를 만들고 같은 좌표를 유지한다. source_fps=null, preview_fps=24, timebase_assumed=true이며 초 단위 원본 타이밍을 주장하지 않는다. mask-given 평가이지 자동 추적 성공이 아니다.

## 실제 mask와 참조 한계

classic-car의 label1/2는 탑승자이고 **label3이 차량**임을 overlay로 확인했다. target support는 label3만 사용한다. 탑승자 pixel은 회색 처리되므로 열린 운전석에 불규칙한 빈 영역이 남는다. 이를 새 segmentation으로 메우지 않는다. 기존 B-031 crop helper에는 선택한 label을1로 변환한 binary support를 전달하며, 원래 palette mask와 track3 계보는 별도 보존한다.

lady-running은 뒤/옆모습이며 아래쪽 다리가 원본 사진에서 잘려 있다. 보이지 않는 얼굴·발 형태를 사전 특징으로 지어내지 않는다. 사람이 다른 공개 sequence라는 사실과 생체 신원 인증은 다르다. source의 배낭은 GT support에 포함되어 교체 대상과 함께 처리된다. 자연스럽게 걷는 전신을 만들 수 있는지는 앵커 단계에서 검토하며, 부적합하면 다른 사진으로 바꾸지 않는다.

Qwen Image1은 source 첫 frame 전체896×512이다. Image2는 원천 target의 GT bbox에 각 방향10% margin을 더하고 외부 pixel을128로 만든 native crop이다. rigid crop621×332, nonrigid crop372×466이며 강제로 같은 크기/자세로 맞추지 않는다. B-031 template과40step/seed20261026/trueCFG4/guidance1/negative 단일 공백을 유지한다. 원본 support 안의 pixel exact, 밖128을 CPU에서 확인했다.

## 사전 caption 및 선택 범위

정확한 image template의 실현 문자열과 video caption은 [selection.json](selection.json), 모든 입력·geometry·hash는 [INPUT_CONTRACT.json](INPUT_CONTRACT.json), 전체 준비 파일 hash는 [INPUT_HASHES.json](INPUT_HASHES.json)에 고정했다. 두 영상 분기의 caption/negative는 같은 task 안에서 동일하다.

총5개의 후보 조합을 입력 수준에서 검토했다. libby→lady-running은 실제 범주 불일치, walking→lady-running은 전신 잘림·다른 사람 겹침으로 제외했다. libby→dogs-jump는 울타리 가림과 다중 개체 target 때문에 선택하지 않았다. dogs-scale은 occlusion 확인용 sequence 문맥 열람이며 생성 후보로 승격하지 않았다. 출력 선택이나 best-of는 없고 추가 다운로드도0이다.

사전 관측은 agent의 정적 이미지 검토다. 독립 사람 주석이나 연속 재생 평가가 아니다. 앵커 적합성은 target 특징·source 자세/위치·중복/형태·보호 장면을 분리해 판정한다.

## 데이터 사용 범위

기존 DAVIS-2017 trainval480p ZIP을 재사용하며 [B-027 데이터 이용 기록](../B-027-public-reference-robustness/DATA_LICENSE.md)을 따른다. CC-BY-NC4.0의 연구용 비상업 범위와 attribution을 유지한다. 공개 GitHub에는 미디어를 올리지 않고 별칭·hash·코드만 남긴다. 공개 데이터라는 이유로 상업 이용이나 무조건 재배포 허가를 주장하지 않는다.
