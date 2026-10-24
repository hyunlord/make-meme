# B-024 결과 — RGB 배경 분리 뒤 원본 자세·장면에 가까워짐

**COMPLETED / 기술 실행 PASS / 정적 시퀀스의 자세·장면 보존 개선 관측 / 실제 reference 교체 효과 미입증 / temporal UNVERIFIED.** 기존 B-023의 기술 PASS와 착석·침실·후기 얼굴 손상 실패를 수정하지 않는다.

## 1. 실제 비교에서 달라진 것

원본·B023·B024 전체17프레임과 local0/8/16을 root와 별도 검토 에이전트가 정적으로 확인했다. 사람의 독립 검수나 실제속도 연속시청으로 보고하지 않는다.

| 항목 | B-023 원래 reference RGB | B-024 비객체 RGB128 | 판정 범위 |
|---|---|---|---|
| 침실·세로구획 | 중앙 침실/침대와 좌우 다른 방, 세로경계 | 중앙 침실·세로구획·흰letterbox 복사가 보이지 않음 | 배경누수 감소 관측 |
| 원본 장면 | 원본 타일·가구·배치 미보존 | 타일,러그,로프,의자,창가,전경팬과 구도가 원본에 가까움 | 단순 회색/임의배경 대체를 넘어 장면 보존 개선 |
| 전신 자세 | reference 착석 유지 | 원본처럼 사족으로 서 있음 | 이 입력의 정적 자세 목표 관측 PASS |
| 고개 방향·순서 | 후기 왼쪽 머리 변화와 번짐·잘림 | 후기 image-left 고개돌림 순서가 원본과 대응 | 거친 시점별 방향·순서 개선; 정밀각도/접촉 UNCERTAIN |
| 얼굴·귀·목·사지 | 후기 얼굴 번짐과 중앙구획 잘림 | 해당 심한 번짐·잘림이 보이지 않고 형태가 더 원본에 가까움 | 상대 개선 관측; 다소 매끈한 얼굴·세부형태는 완전보존 아님 |
| 개체·체형 | 검은Lab 유사성,실제일치 불확실 | 원본Lab와 닮은 외형·몸통·사지 | 같은개체/source-copy로 설명 가능; reference 사용 입증 아님 |
| 시간 품질 | UNVERIFIED | UNVERIFIED | 파일 재생·프레임 확인과 연속 품질 관찰 구분 |

이번 결과는 '침실만 사라지고 임의 배경이 생김'보다 강한 원본 보존 근거다. 다만 reference와source가같은개체이므로,모델이driving의개체까지복사했을가능성과참조개체치환을분리할수없다. cross-ID·reference필요성·일반화·상용품질·긴영상은미입증이다. 배경제거를자세제거나identity-only표현으로부르지않는다.

## 2. 출력 계보와 파일 혼동 확인

새출력이원본과매우비슷해raw→PNG계보를추가로CPU확인했다. 실제`raw_output.pt`는finiteFP32[3,17,512,896]이고SHA256은`e33ac003e663f3e2a32c7740f116d4d0dfd6259eff379cc30906e9b6d2562f3b`다. 전체17개PNG가이raw의기록된uint8변환과정확히같으며sourcePNG와동일한프레임은없다. [검증](comparison-raw-provenance.json)의RGB차이는파일대체여부참고이며품질점수나통계적효과크기가아니다.

실제final latent는FP32[16,5,64,112],40step/80forward완료후저장됐다. initial noise와다르며drivinglatent[16,5,32,56]·referencelatent[16,1,64,112]를출력으로잘못쓰지않았다. D는공식VAE로이finalx0만decode했고ROI합성·source파일대체·warp·복원·보간·SR는없다. 모델자체source-copy가능성은이검사로제거되지않는다.

## 3. 통제와 실제 연결 확인

사전고정코드commit `460a5d212548552d304fff63f66e320a4014cbc2`. 같은f126..142/17f30fps/896×512·caption·noise·RNG·UniPC40shift3CFG5·replacementTrue,adapter/ALG/manualRoPE OFF를유지했다. source표본간격16/30초,파일지속17/30초다.

REDsupport37,209pixel은RGBexact보존,밖421,543pixel은128이며semanticmask·bbox·위치·크기·착석자세불변이다. 침실과whitepadding을함께바꾸므로침실단독효과는아니다. 기존thinfur/ear/paw support한계는그대로다.

짧은연결감사와실제조건복원에서reference는착석침실,driving은사족자연동작으로확인했다. 원본reference재인코딩VAE/CLIPmax_abs/RMS는0으로관측됐다. 이를새byte-identical필수gate로만들지않았다. 새RGB를두encoder에각각전달해양CFGref/CLIP4leaf만변경,나머지12와device구조를보존했다. 첫실제forward에서새조건객체전달을확인했고관측용추가forward는없었다. 구체적입력교환·stalecache·중복정규화·generatedoffset결함은발견하지못했으나모든잠재오류배제를주장하지않는다. [조건](CONDITIONS.md),[연결감사](CONNECTION_AUDIT.md).

## 4. 실제 사용량·안전·한계

REF/PROBE/S/D 각1회,신규sampler1회40step80forward,finaldecode1회,재시도0. 기존조건ref/driver복원각1회,원본/중립VAE+CLIP인코딩각1세트다. 새학습/모델/패키지설치/다운로드/imagegen/외부생성은0이다.

REFworker9.40초,Sworker1074.82초(샘플링device이동포함986.33초),Dworker13.03초였다. S CUDApeak33.85GiB,cgrouppeak62.02GiB,최소시스템가용52.79GiB다. 서로다른회계를합산하지않는다. cgroup.high3031은보존하며max/OOM/kill0,swap0,headroom위반종료0이다. 자체pipeline/watchdog종료와보호서비스유지를확인했다. [실측](MEASUREMENTS.md),[실행원시요약](runtime-summary.json).

CPU4개계약검사와compile검증은PASS다. 기존동적runner타입진단은NOT_CLEAN이며사용불가능한linter를새로설치하지않았다. 이를실행·시각PASS와혼동하지않는다.

## 5. 바로 볼 비공개 자료와 다음 하나

비공개run의`reports/review.html`, `reports/comparison-final/comparison-30fps.mp4`, `comparison-local0-8-16.png`, `comparison-all17.png`에서원본/B023/B024를볼수있다. 원래·중립참조및기존latent복원도별도로제공한다. 개인미디어·cache·latent는GitHub에없다. 최종ZIP에는실물·최종latent·조건복원·재현·실패/불확실성기록을포함하고weights/중복prefix를제외한다. 위치와무결성은최종전달기록에명시한다.

**다음가설하나:** 같은중립배경reference전처리와정식replacement를고정한짧은cross-identity교체에서,원본동작·장면을보존하면서reference개체의외형이실제로반영되는지검증한다. 이번개선이단순driving개체복사로설명되는지구분하는것이병목이다. 이번에추가생성·sweep·학습을실행/예약하지않는다.
