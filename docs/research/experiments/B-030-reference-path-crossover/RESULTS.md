# B-030 결과 — 조건 경로는 분리된 역할로 해석되지 않았다

**COMPLETED / 실행 계약 PASS / 경로별 역할 분리 PARTIAL·INCONCLUSIVE / temporal UNVERIFIED.** 신규 교차4셀을 각40step·80forward로 생성하고 finite final latent와17프레임 MP4를 보존했다. B-027 대각4출력은 재사용했다. 새 편집 알고리즘이나 품질 개선 실험으로 판정하지 않는다.

## 실제 영상에서 확인한 것

사람은 같은 CLIP을 유지해도 VAE+mask를 R1→R2로 바꾸면 치마의 큰 부피와 높은 배치가 두 열에서 반복됐다. 하지만 Y21의 넓은 원반형 치마와 Y22의 세로 접힘·얼굴 가림은 다르다. Y12에는 상체·팔의 수평 파편이 뚜렷하다. 따라서 VAE+mask 묶음에 대한 제한된 조건부 의존 근거는 있으나, VAE=pose·CLIP=identity라는 분리는 성립하지 않는다.

차량의 도로 위 큰 스포츠카 그림은 Y11에만 있고 Y12/Y21/Y22에는 없다. CLIP1이나 VAE1 어느 하나만으로 유무를 설명할 수 없으며 조합 의존으로 남긴다. 네 셀 모두 은색·밝은 외형에 반응하지만 source의 Mini형 비율이 강하게 남는다. Y21에는 하단 도로의 직사각형 명암 패치도 보인다. 장식이 없어진 것만으로 target 차량 교체 성공은 아니다.

| 과제 | VAE+mask R1 / CLIP R1 (기존) | VAE+mask R1 / CLIP R2 (신규) | VAE+mask R2 / CLIP R1 (신규) | VAE+mask R2 / CLIP R2 (기존) |
|---|---|---|---|---|
| Human | 후기 낮은 치마, 흰 추가 획 | 낮은 치마, 수평 상체 파편·큰 흰 획 | 과도한 원반형 치마, 후기 몸통 가림 | 큰 세로 치마·후기 얼굴 가림 |
| Vehicle | source형 은색 차체 + 큰 별도 차량 그림 | source형 은색 차체, 큰 그림 없음 | source형 밝은 차체, 큰 그림 없음·도로 패치 | source형 밝은 차체, 큰 그림 없음 |

전체17장과 사전 local0/8/16을 정적 agent가 확인했다. 원본의 큰 발 배치 순서와 차량의 우측 진행·후측면 노출은 남지만 정밀 관절·접촉·정확한 identity는 UNCERTAIN이다. 실제 연속 시청을 하지 않았으므로 temporal=UNVERIFIED다. 항목별 전 셀 관측과 행/열 비교는 [MATRIX_REVIEW](MATRIX_REVIEW.md), 생성 전 기준은 [PREGEN_REVIEW](PREGEN_REVIEW.md)다.

## 어떤 비교가 해석 가능한가

- 같은 CLIP에서 VAE+mask를 바꾼 두 비교는 사람의 치마 규모/높이에 반복되는 차이를 보였다. mask·사진 시점·가림도 함께 바뀌므로 VAE 단독 효과는 아니다.
- 같은 VAE+mask에서 CLIP을 바꿔도 치마 형태·상체 파편·부가 획이 변했다. CLIP이 공간·형태에 관여하지 않는다는 설명은 지지되지 않는다.
- 차량 그래픽과 사람의 세부 손상은 단순 행/열 규칙을 따르지 않는다. 교차 조건의 불일치·분포 이탈 가능성과 상호작용을 구분해 식별하지 못했다. 이 부분은 INCONCLUSIVE다.

같은 target track의 두 참조·단일 noise·두 개발 과제다. 미사용 일반화 평가, 프레임별 독립 반복, 성공률 또는 encoder의 순수 인과효과로 확대하지 않는다. B-028/B-029의 기각·CONTROL·비용·한계는 그대로 유지한다.

## 기술 실행과 비용

사전 코드·조건·판별 항목을 `23408cf5f54938a377ed3356e55216efdf0a1573`로 push하고 원격 일치를 확인한 뒤 실행했다. 네 cache 모두 행 부모 대비 양 CFG `clip_fea` 두 leaf만 donor 값으로 바꾸고14leaf·tree/device·noise/RNG/scheduler를 보존했다. 첫 실제 양 CFG forward에서 참조 객체 연결과 hash를 확인했다. 원래 baseline sampler·official forward를 사용했고 B029 gate·LoRA·ALG·수동 RoPE는 OFF다.

| 항목 | 실제 사용/상태 |
|---|---|
| 신규 sampler / decode / PROBE | 각각4/4, 재시도0 |
| 실제 계산 | 각40step·80forward, 합계160step·320forward |
| encoder / 학습 / 다운로드·설치 / 외부 생성 | 모두0 |
| 순차 실행 구간 | UTC08:29:42~09:38:04,68.37분 |
| sampler worker | 셀별997.82~1017.67초, 로딩 포함 |
| decode worker | 셀별15.23~16.22초 |
| 최대 CUDA allocated / 최소 시스템 MemAvailable | 33.847GiB /52.911GiB |
| 최대 cgroup peak / 관측 RSS | 62.585GiB /88.312GiB, 서로 다른 회계이며 합산하지 않음 |
| swap / cgroup OOM / 가드 종료 | 모두0 |

실제 shape `[3,17,512,896]`, preview24fps, source_fps=null, timebase_assumed=true다. 원본 초 단위 시간 보존을 주장하지 않는다. 모든 final latent는 decode 전에 원자적으로 저장됐고 S 종료 후 D를 실행했다. 최종 자체 systemd worker는 inactive/MainPID0이며 자원이 회복됐다. 원시 측정과 출력 SHA256은 [MEASUREMENTS](MEASUREMENTS.json), 단계별 회계와 비용 범위는 [COSTS](COSTS.md), 조건 계보는 [CONDITIONS](CONDITIONS.md), 독립 실행 검토는 [SOURCE_REVIEW](SOURCE_REVIEW.md)에 있다.

## 다음 표적과 종료

다음 연구 가설은 하나다: **참조 VAE+mask 묶음의 공간 배치가 source 구조와 경쟁하는 부분을 외형 전달과 분리할 수 있는가?** 사람의 반복된 행 차이가 이 표적을 검토할 근거지만, 차량 identity 잔존이나 모든 손상의 원인을 설명하는 증거는 아니다. 구체적 gate·lambda·layer·zero-out을 이번 결과만으로 정하거나 자동 실행하지 않는다.

이번은 진단으로 종료한다. 새 방법 채택·추가 모델·학습·seed·긴 영상은 실행하지 않았다. 한국어 수식·실제 함수·질문/해설은 [학습 문서](../../lessons/B-030-reference-path-crossover.md), 재현은 [REPRODUCE](REPRODUCE.md)다. 비공개 compact는8개 원본 MP4와 source/reference·전체17프레임 검토·보고서를 담고, full에는 신규4개 raw/latent 쌍을 추가한다. 영상 재인코딩과 결과 보정은 없다. 압축·전송 검증은 별도 전달 기록의 실제 범위로 보고한다.
