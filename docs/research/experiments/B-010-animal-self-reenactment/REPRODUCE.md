# B-010 재현 계약

최종 **DIAGNOSTIC_INSUFFICIENT**이며 GPU P/PROBE/S/D는 모두0회 **NOT_RUN**이다. [PLAN](PLAN.md)의 source-first-frame 자기 재현과 비생성 정적 대조군만 다룬다. 준비한 코드와 생성 전 평가를 보존한다. 실행하지 않은 GPU 명령을 실제 재현 이력으로 제시하지 않으며 이 문서로 자동 replay를 시작하지 않는다.

## 입력과 비교군

reference는 B-009에서 사용한 처리된 source f0 RGB를 lossless PNG로 저장한다. 같은 f0의 RED support와 WHITE background를 reference mask로 사용하고 새 윤곽을 추정하지 않는다. driving RGB/mask는 B-009와 동일하다. positive prompt는 실제 source 외형·장면·관측 동작을 묘사하고 사전 고정한다. Lab/침실 cache를 새 이름으로 재사용하지 않는다.

STATIC COPY는 source 첫 프레임17장 반복의 CPU 대조군이다. 새 생성0회이며 명확히 표기한다. 생성 결과의 프레임 복제나 smoothing과 혼동하지 않는다. B-009는 맥락 비교이며 단일요인 대조군이 아니다.

## 고정 실행

기존 pinned SCAIL `78fe19576bb06be96c2375e088574a262a300edb`, mixed dtype·FA·staged loader·tiny64-byte anchor 경로를 유지한다.512×896·17프레임·24fps·seed20261022·UniPC40·shift3·CFG5·history=None·animation·LoRA OFF·empty negative다. P→PROBE→S→D 각 최대1회, retry0. 원본 변환·모델 다운로드·학습·ALG 적용·다른 동물 생성은0이다.

먼저 source17장의 사전 표면점과 고정 좌표계에서 static copy 대비 관측 가능한 변화를 확인한다. 변화가 불확실성보다 작으면 DIAGNOSTIC_INSUFFICIENT이며 더 긴 구간·새 seed를 자동 선택하지 않는다. 관측점 null/UNKNOWN·coverage와 고정 정규화 크기를 보존한다.

P에서는 reference/CLIP/mask/positive 변경과 driving·negative·noise/RNG/schedule 보존을 새 계약으로 검증한다. B-009의 mask-only gate를 삭제해 무조건 통과시키지 않는다. S80forward/40step 및 final latent finite/hash/readback, D17장24fps·raw/MP4를 별도 확인한다. 각 worker 종료·회복 뒤 다음을 실행하고 실패하면 중지한다.

## 검토와 제한

source/STATIC COPY/self output을 같은 canvas·시간에서 비교한다. 초기 자세와0 이후 displacement를 별도 보고하고, source 움직임이 작은 경우 gain은 UNDEFINED/INCONCLUSIVE다. 대응점 누락을 숨기거나 frame별 warp·lag 탐색으로 점수를 개선하지 않는다. 직접 연속 재생이 없으면 temporal=UNVERIFIED다.

공개에는 비민감 code/hash/집계만, 원본·출력·mask·관측 좌표·latent는 비공개로 남긴다. [학습 문서](../../lessons/B-010-self-reenactment-and-static-shortcut.md)의 ALG 관련 검토는 문헌 연구뿐이며 새 알고리즘을 실행하지 않는다. 이번에 실행된 GPU launch 명령은 없다.

## 실제 종료 근거

사전20개 평가 항목의 E_copy15.5107px가 평균 전파 관측 불확실성19.4222px보다 작았다. 코·눈 끝점 변화는 보이지만 전역 translation/scale의 영향이 남았고 모든 앞발 변화는26.8889px 경계보다 작았다. 시트·crop 독립 검토에서도 현재 관측의 articulated motion 판별력이 충분하지 않았다. 원본 무동작이나 모델 FAIL로 바꾸지 않는다.

[RUN_LEDGER](RUN_LEDGER.json): P/PROBE/S/D attempts0, sampler0, model loads0, generation failures0, retries0, training0, generated artifacts0. 자체 unit은 inactive/MainPID0이며 남은 자체 프로세스가 없다. CPU8개 계약 fixture는0.91초에 PASS했지만 실제 모델 실행이 아니다. 준비물540개 보존 검사는 PASS, targeted typecheck81errors는 NOT_CLEAN이다.08:00UTC deadline은 실행되지 않은 예산의 자동 재사용 근거가 아니다.

다음 제안은 같은17프레임의 native-resolution 수동 표면점 주석 감사(CPU-only) 한 가지이며 미실행이다. 클립을 본질적으로 무용하다고 단정하거나 새로운 구간/seed로 자동 생성하지 않는다.
