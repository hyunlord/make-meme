# B-002 실행 기록

- 시작: 2026-10-21 23:54:58 UTC (2026-10-22 08:54:58 KST).
- 종료 상한: 2026-10-22 01:54:58 UTC.
- parent: B-001. 계획 revision 1과 고정 기준 커밋 `eaca4e217c17f0db326ef71b8a12b5d7791cb7c5`를 유지한다.
- 별도 문서 worktree에서 실행하며 A와 B-001의 코드/출력을 덮어쓰지 않는다.
- Spark 기존 B 가상환경/가중치를 재사용한다. 이번 학습 0, adapter=null, 새 모델 0, 신규 전체 추론 최대 5.
- 시작 자원: MemAvailable 83,246,501,888 bytes; swap 0; 디스크 가용 1,171,261,165,568 bytes. 기존 ComfyUI 프로세스는 유지하며 큐와 자원 경합을 실행 전에 검사한다.
- 원래 질문과 사전 가설, 평가 항목 및 중단 규칙은 [PLAN](PLAN.md)을 따른다. 참고 배경이 줄어도 착석이 남을 수 있으며 동작 성공으로 간주하지 않는다.
- 재사용 검증 전이며, R/첫 seed를 재사용할 수 없으면 PLAN의 5회 대안 순서를 따른다.
- 정적 이미지 관찰과 실제 속도 재생을 구분한다. 연속 재생을 관찰하지 못하면 시간 품질은 UNVERIFIED다.

## 입력 준비 (새 추론 전)

원본 실제1536×2048 RGB에 수동 윤곽과 비학습 GrabCut을 적용했다. alpha는0/1이며 전경595,340픽셀의 원본RGB를 그대로 보존했다. 흰 배경만 대체했고 위치/크기/자세는 바꾸지 않았다. 비교 시트에서 귀·혀·가슴·양 앞발, 다리 사이 침구 제거를 확인했다. hard 경계 수동 오차 및 resize 경계 혼합은 한계다. 수동 작업 시간은 별도 계측하지 않았다. 참조사진과 마스크는 비공개 로컬에만 보존한다.

기존R의17 source/condition RGB와 padded reference가 일치하고 sampler 호출AST 및 noise tensor hash를 확인했다. remote 가중치 재검증이 끝나면 reuse순서를 고정한다. 이전textembedding은 해시 미기록이므로 동일가중치/문자열/코드의 계산적 호환성과 실제 관측을 구분한다.

## 2026-10-22 00:06 UTC — 재사용 확정 및 실행 순서 고정

remote 모델/토크나이저9파일이 B-001 실제SHA와 일치하고 pinned upstream 핵심5파일도 일치했다. 동일prompt/tokenizer/textencoder경로이며 이전texttensor의 직접 해시는 없어 그 점은 미관측 한계로 남긴다. 기존R/20261022를 재사용한다. 신규순서: R-bg/20261022 → P/20261022 → R/20261023 → R-bg/20261023 → P/20261023. 실제NoiseInitializer와 text/VACE입력 해시는 새 read-only hook으로 기록한다. CPU dummy로 실제unit runner의 tuple반환·tensoridentity·RNG보존을 검증했다.

## 첫 신규 추론 완료

R-bg/20261022 정상종료: runner109.758초, pipeline44.106초, peakallocated17,056,366,080bytes/peakreserved17,687,379,968bytes. 실제NoiseInitializer 해시가 기존R의 저장noise와 일치한다. text조건은 positive `(1,512,4096)`, VACEcontext `(1,96,6,36,64)`이며 initializer/prompt/VACE단위 전후 CPU RNG상태가 유지됐다. 이 검사는 입력통제 증거이며 이미지품질 평가는 아직 하지 않았다. 계획대로 나머지4조건을 순차 실행한다.

## 실행 종료

신규5/5 완료, 실패0, 재사용1. 실제 해시/설정/프레임 검증 PASS. 조건명을 가린 시트 관측 후 대응표를 확인했으며 기존R 노출 때문에 완전블라인드가 아니라고 기록했다. 추가 생성 없이 RESULTS와 이론을 정리했다. 시간품질UNVERIFIED.

검토 후 `parameters_unchanged`라는 모호한 검사명을 `parameter_counts_unchanged`로 정정했다. 비교한 것은 개수이며 실행 후 전체 가중치 값 검증을 뜻하지 않는다. 실행/모델은 변경하지 않았다. strict type 검사 미통과는 RESULTS에 따로 남겼다.
