# C-003 결과 — 시작 가드 중단 / 내부 구조 효과 미평가

**INCONCLUSIVE, BLOCKED_SAFETY. DYNAMIC이 OUTLINE_ONLY나 HOLD보다 머리·다리 진행을 잘 따르는지는 평가하지 못했다.** 공식 가중치와 코드·CPU 변환 검사는 준비했지만 기존 시작 가드가 `START_SWAPOUT_OBSERVED`로 중단했다. 새 구조 추출·조건·영상은 모두0이며 CPU 구현을 연구 품질 성과로 세지 않는다. 기본 채택 근거도 없다.

## 실제 경과와 중단 근거

부모 C-002 `853ee952795246648b3a6e46d37d5dead03abef3`에서 기존 C 트랙을 이어 썼다. 실행 전 의뢰서·계획·source 사건표·공식 추출 코드를 `2e115dd7cb2764fbef40f0bd5855c974d3f7d52f`에 공개했다. 첫 실제 CPU systemd 경로는 runpy에서 sibling module 검색 경로가 없어 import에서 실패했다. 가중치 load 전이며 추출/heavy 예산을 사용하지 않았다. 원래 supervisor의 NOT_CLEAN / OBSERVATION_FAILED, REMOVED:exit_not_verified, worker return1·cleanup오류0 기록도 그대로 보존한다. import 원인을 확인했다고 정상 종료 PASS로 바꾸지 않는다. 자체 script directory 추가를 `13aa08489cde3d4fe231664dd24bebb10f7638a7`에 공개한 뒤 같은 보호 경로를 다시 확인했다. 이 기계적 오류와 이후 안전 중단을 구분한다.

수정된 CPU 경로의 시작 관측10.238937초에서 pswpout127→128, 실제 page size4096B로 swap-out4096B가 관측됐다. S0는1,548,288B, 마지막 swap1,806,336B(+258,048B)였다. MemAvailable121,690,972,160B, PSI full ratio0.0037203이었다. 기존 C-002/C-001 가드의 시작 swap-out 규칙이 `START_SWAPOUT_OBSERVED`로 차단했으며 worker를 만들기 전이었다. 작은 안정 잔량만으로 중단된 것이 아니며, 모델 OOM/CUDA 결함으로 재분류하지 않는다. 전역 발생 주체는 UNKNOWN이다.

사용자 지시의 안전 중단 후 자동재시도 금지에 따라 더 실행하지 않았다. 가드 임계값/서비스/전역 설정을 변경하지 않았다. 보조 추출 heavy0, 완료 pass0, 영상 heavy0/정상2예산, 예비0, sampler/forward/decode0이다. 해당 경로가 안전 중단했는데도 CPU 경로만 바꿔 추출을 우회하지 않았다. 당시 외부 GPU는0이고 보호 서비스는 EXPECTED_ABSENT_OBSERVED였다. 최종 읽기에서 자체 활성 unit0/GPU process0을 확인했다. 타 작업을 시작하거나 종료하지 않았다.

## 준비된 것과 검증하지 못한 것

공식 scribble 소형 가중치 한 파일17,173,511B를 immutable revision으로 확보했고 파일 SHA256을 확인했다. [provenance](ANNOTATOR.md). Exact EDT>4, bbox pixel-center,256 공통 bilinear 왕복, 이동하는 HOLD, I 밖 픽셀 불변을 CPU 검사했다. 기존 endpoint/layout 검사는 보존하고 새 internal 모드 검사를 추가했다. 이는 실행 준비의 증거다.

실제 모델 strict load·FP32 추출·polarity·머리/다리 선 유효성·DYNAMIC/HOLD 실제 차이는 NOT_RUN이다. 무손실 조건33장과 새 noise/context hash, final latent/raw/output은 없다. C-002의 noise 해시를 새 관측처럼 복사하지 않았다. 따라서 어떤 부위가 NOT_REPRESENTED인지도 아직 실제 판단할 수 없다.

## 관측·비교의 한계와 다음 판단

[생성 전 표](OBSERVATIONS_PRE.md)는 source와 기존 앵커·C-002 MOV의 실제 정적 관측이다. C-002의 낮은 머리와 미입증 앞발 phase, source와 종료 앵커의 웅크림 충돌을 보존한다. 29–32를 별도 평가할 계획이었지만 새 출력이 없어 개선·회귀·외형 복사·보호 장면 변화는 모두 미평가다. temporal=UNVERIFIED다.

이번 결과는 구조선 정보 부족이나 VACE 조건 활용 실패의 증거가 아니다. 아직 해당 조건을 생성 모델에 넣지 않았다. 객체 내부 대응 연구 전체에 대한 부정 결론도 낼 수 없다. 다음 아키텍처·학습 개입은 제안 근거가 추가되지 않았으며, 이 보류 결과와 기존 C-002를 사용자와 검토한 뒤 결정한다. 자동 재개·추가 실험은 없다.

[비용](COSTS.json)에는 영상/추출0, 한 파일 다운로드, CPU 오류/수정과 안전 차단을 분리했다. Compact는 **기존 자료와 미실행 상태를 보는 보류 검토물**이다. 새 두 영상이나 구조선이 포함됐다고 보고하지 않는다. [전달](DELIVERY.json). C-001 PARTIAL, C-002 차량 TRADE_OFF/개 COARSE_CONTROL_ONLY, A/B 실패·보류는 불변이다.
