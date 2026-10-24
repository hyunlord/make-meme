# 2026-10-25 — B-022 결과를 본 뒤 B-023을 한 번의 동일입력 replacement로 수정

## 검토 근거와 한계

사용자는 진행중작업결과를본뒤다음지시를정하라고요청했다. B022종료보고후기준commit `6a359ae85f134ca879a2d521d7fd771b401b5d55`의RESULTS, B020 INPUT_AMENDMENT, 기존B023PLAN을읽었다. 원격HEAD도해당SHA였다.

업로드 `/mnt/data/make-meme-B-022-20261025-final.zip`에container와Python으로실제접근을시도했으나도구가ClientError를반환했다. 새영상·414파일CRC/hash·양호스트동일성을독립검증하지못했다. 사용자보고의153,158,583bytes/SHA `9a3dac330b3e317c9b0bbe467b109d25c27d51e6c81fa6088578ba33edf537d6`는이검토의검증값이아니다. Spark에서추가실행도없다.

B022의정확한상태복원·추가80update·두endpoint생성은실행자기록상PASS다. loss20→100은train0 0.1454722583→0.1448749900,train1 0.0506718382→0.0504798330,train2 0.0314944424→0.0308459513,같은clipholdout0.0383793972→0.0382253155다. 두영상의착석·얼굴번짐·잘림은남았다. 이고정3tuple/마지막blockQVrank4구성에서품질이개선됐다는근거는없다. 모든학습이무효/전체모델불가능/학습수렴을뜻하지않는다. 원인UNKNOWN과temporalUNVERIFIED는유지한다.

## 공식 소스와 새로 확인한 차이

고정mainSCAIL revision `78fe19576bb06be96c2375e088574a262a300edb`의gitlink로Pose revision `519c7f54cb972e7f92684213b7ef6c3e05a8f3b2`를확인했다. 그revision의process_animation_aio.py,process_replacement.py,v2_helper.py를읽었다.

| 입력 계약 | replace_flag | reference배경mask | driving배경mask |
|---|---|---|---|
| B020기록/B022재사용 | False | WHITE | WHITE |
| pinned animation전처리 | False | WHITE | BLACK |
| pinned replacement전처리 | True | BLACK | WHITE |

animation은reference white를명시하고drivingwriter의default black을사용한다. replacement는referenceblack/drivingwhite를명시하고원본drivingRGB를그대로복사한다. 일반replacement경로는referenceRGB의실제배경을별도로blackout하지않는다. 색상mask는학습된semantic조건이지hardalpha가아니다.

B020/022의mask픽셀을이번에독립재계산한것은아니고문서상의계약을대조했다. 이차이를확인했다고기존실패원인이증명된것은아니다. 양쪽WHITE가언제나잘못된입력이라고일반화하지않는다. 다만task-aligned baseline보다작은학습량확대를먼저진행한우선순위는수정한다.

## 실제 다음 선택

[개정B023PLAN](../experiments/B-023-task-aligned-replacement/PLAN.md)을다음수행제안으로둔다. 과거후보의meme f7..23/24fps/SELF+LAB2case/ROI합성은이번실행에서제외한다. 과거계획은Git이력에보존한다.

같은Lab자연영상f126..142,17f30fps,896x512,같은참조RGB/support/prompt/noise를고정한다. 학습adapter OFF의원래기반모델에서공식replacement전체계약을적용한새sampler1회만제안한다. B020미학습OFF결과를primary historicalbaseline으로재사용하고B02220/100은별도맥락으로둔다. 모드+mask조합의과제비교이며단일변수인과실험은아니다.

실행원본과참조가동일Lab이므로좋은출력도sourcecopy로설명될수있다. 결과는scene/posture alignment의진단이지실제cross-ID editing성공이아니다. 다음cross-ID나합성/ROI연구는이결과를본뒤결정한다. 이번에는raw결과를합성·SR·warp로고치지않는다.

실험사전조건·안전·데이터계보는유지하되같은권한/커널/optimizer감사를반복하거나200/500update로자동확대하지않는다. 새로운촬영요구없음. 최종판정은loss가아닌서있는전신·고개변화·얼굴/귀보존·원본장면·비용이다.

## 현재 기록 상태

B022 COMPLETED 그대로, B021 FAIL그대로. B023 REVISED/PLANNED/NOT_RUN. 이번원격변경은PLAN개정과이결정문서뿐이며실행코드·가중치·기존결과변경0,GPU·생성·학습0이다. 실행자는사용자의수행지시후HISTORY/ROADMAP에본개정과실제착수·종료를연결한다. 기존개인자료공개금지·A/B독립유지.
