# B-014 ALG → SCAIL 이식 감사

상태: **공식 수식·코드 확인 완료 / CPU_CONTRACT_PASS / 실제88forward·영상 출력 완료 / 전신 개선 미확인·시간 UNVERIFIED**. 이 문서는 실행 승인이나 영상 품질 판정이 아니다. 기존 B-013 결과와 실패 기록을 보존한다. 작은 공식 소스만 읽었으며 모델·데이터 다운로드, 새 모델 실행은 하지 않았다.

## 고정 근거와 적용 경계

- [ALG 논문 v2, Eq.(2)](https://arxiv.org/html/2506.08456v2#S3.E2), 2026-02-24.
- ALG commit `3657bfd0d408631db2443b491498c44e1cb2e5c6`의 [Wan pipeline](https://github.com/choi403/ALG/blob/3657bfd0d408631db2443b491498c44e1cb2e5c6/pipeline_wan_image2video_lowpass.py#L850-L927), [lp_utils](https://github.com/choi403/ALG/blob/3657bfd0d408631db2443b491498c44e1cb2e5c6/lp_utils.py#L8-L98), [Wan YAML](https://github.com/choi403/ALG/blob/3657bfd0d408631db2443b491498c44e1cb2e5c6/configs/wan_alg.yaml).
- SCAIL commit `78fe19576bb06be96c2375e088574a262a300edb`의 [조건 dictionary](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/scail.py#L480-L506), [reference/generated/driving 결합](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L741-L803).

비공개 `reports/official-audit/sources.json`에 실제 HTTP URL·수집 시각·원문 파일 bytes/SHA256을 보존했다. 아래 line anchor는 저장한 원문 파일의 실제 줄 번호다. 브라우저가 정규화한 표시 줄 번호와 혼동하지 않는다.

## 1. 공식 구현에서 확인한 사실

초기 활성 구간에서 branch 순서는 original-negative, filtered-negative, filtered-positive다. [L888–924](https://github.com/choi403/ALG/blob/3657bfd0d408631db2443b491498c44e1cb2e5c6/pipeline_wan_image2video_lowpass.py#L888-L924)의 실제 결합은 `u_orig + w*(c_low-u_low)`다. 원래 CLIP image embedding은 [L804–812,904–914](https://github.com/choi403/ALG/blob/3657bfd0d408631db2443b491498c44e1cb2e5c6/pipeline_wan_image2video_lowpass.py#L904-L914)에서 유지·반복된다. 비활성 구간은 원래 reference의 negative/positive 두 branch다.

논문 Eq.(2)와 코드는 일치한다. 다만 Eq.(2) 다음의 “equivalent” 재표현에는 `w-1`이 적혀 있어, 표시된 식을 그대로 더하면 Eq.(2)와 일치하지 않는다. 이번 구현 기준은 Eq.(2)와 실제 코드다. 올바른 대수적 분해는 `u_low+w*(c_low-u_low)+(u_orig-u_low)`다. 논문의 해당 재표현을 복제하거나 CFG 값을 바꾸지 않는다.

공식 latent 경로 [prepare_lp L541–558](https://github.com/choi403/ALG/blob/3657bfd0d408631db2443b491498c44e1cb2e5c6/pipeline_wan_image2video_lowpass.py#L541-L558)는 mask와 latent가 연결된 Wan condition을 공간 필터에 전달한다. SCAIL은 별도 reference prefix와 semantic mask 구조이므로 이번에는 **ref_latents만** 바꾸고 mask는 보존한다. 이것은 명시적 이식 차이이며 공식 Wan pipeline 전체 재현이 아니다.

## 2. 이식 계약

| 항목 | B-014 고정 선택 | 검사 대상 |
|---|---|---|
| 원본 negative | 원래 `arg_null`, 원래 R | original 기준항 유지 |
| low negative | `arg_null`의 ref_latents만 L(R) | text와 나머지 visual 조건 보존 |
| low positive | `arg_c`의 ref_latents만 L(R) | positive text 및 다른 조건 보존 |
| 후반 | 원래 두 branch | 기존 순서·계산 경로 유지 |
| 계산 방식 | 3회 순차 single-sample | 공식 batch3의 의미를 옮김; bit-identical 보장 아님 |
| 출력 | scheduler 결과 그대로 | 첫 프레임 overwrite/clamp 없음 |

text-negative도 CLIP·reference·mask·driving을 받으므로 visual-unconditional이 아니다. 두 filtered dictionary를 만들 때 원본 list/storage를 in-place 수정하지 않는다. CLIP·mask·driving·text·history·noise/RNG·scheduler·dtype/weights는 변경 대상이 아니다.

논문 부록은 후처리 first-frame overwrite와 low-pass 시작 지연을 추가 기법으로 설명한다. 이번 계획에는 둘 다 없다. pinned Wan loop의 scheduler 뒤에도 해당 overwrite가 없음을 확인했다. SCAIL reference는 출력 첫 프레임 강제 조건이 아니므로 다른 모델의 기법을 자동 추가하지 않는다.

## 3. 필터·시간·비용

공식 YAML의 latent down/up ratio0.4·interval[0,0.20]만 첫 pilot 설정으로 옮긴다. 공식 YAML의50steps·81frames·480×832·16fps를 이번 출력 설정으로 복사하지 않는다. SCAIL은 기존40steps·17frames·512×896·24fps다.

`R=[16,1,112,64]` FP32를 `[1,16,112,64]`로 permute하고, [lp_utils L49–54](https://github.com/choi403/ALG/blob/3657bfd0d408631db2443b491498c44e1cb2e5c6/lp_utils.py#L49-L54)와 같은 bilinear·antialias=True·align_corners=False로45×26까지 축소 후112×64로 복원한다. signed latent에 clamp나 재정규화를 하지 않는다. 일반5D는 `[B,C,T,H,W]→[B,T,C,H,W]→[B*T,C,H,W]`를 명시한다. upstream의 직접 view는 의미상 축 이름이 맞지 않지만 동일한 평면별 필터만으로 실제 채널 혼합이 발생했다고 단정할 수는 없다. 이번 fixture로 평면 독립성과 원본 불변을 확인한다.

[정규화 step과 inclusive interval L81–98](https://github.com/choi403/ALG/blob/3657bfd0d408631db2443b491498c44e1cb2e5c6/lp_utils.py#L81-L98)에 따라 `i/39≤0.20`: i0..7만 활성, i8..39는 비활성이다. 예상 single-sample NFE는 `8×3+32×2=88`, scheduler update는40회다. 기존80회 대비10% 많지만 시간·피크 메모리가 정확히10% 늘어난다는 뜻은 아니다.

## 4. 아직 검증하지 않은 것

공식 감사와 CPU 계약은 아래 근거까지 완료됐다. 아래 실제 runtime receipt까지 확보했다. 얼굴·전신 자세·시간 품질은 별도 시각 판정이다. 공식 ALG의 I2V 동적 정도 개선과 이 과제의 cross-identity 자세 충실도는 다른 질문이다. SCAIL 적용 효과는 미검증이며 저주파 착석 실루엣·CLIP·mask는 남는다. 개체 단서 약화나 source 외형 누출도 가능한 위험이다. 한 pilot은 ALG 전체의 유효성·고주파 원인·일반화를 판정하지 못한다.


## 5. 실제 CPU 검증과 구현 위치

[CPU_VALIDATION.json](CPU_VALIDATION.json)의 최종 결과는 **9 passed / 0.69초**다. 이전8개 기록 대신 parent binding을 포함한 최종9개를 따른다. 사전 red는 미구현 함수에 대한5개 실패로 기록됐으며 없애지 않는다. 실제 부모 cache16개 leaf hash, 원본 reference·receipt 불변, RNG 불변, 각 branch의 reference 교체 범위와 다른 kwargs 보존을 확인했다.

- [alg.py](code/alg.py)의 `low_pass_reference`: CTHW/BCTHW를 명시적으로 permute해 평면별 필터, dtype/shape와 signed 값 보존.
- `AlgSettings.active/expected_calls`: i0..7·88회 산출; `guided_prediction`: 활성3항, 비활성 기존 positive→negative 순서.
- `branch_condition`: 새 dictionary의 ref_latents list만 교체. 원래 reference/mask/driving을 수정하지 않는다.
- [alg_extract.py](code/alg_extract.py): pinned prediction block의 단일 일치를 검사하고, 치환을 되돌린 AST가 baseline과 같음을 확인한다.
- [alg_runtime.py](code/alg_runtime.py): sidecar의 parent cache/reference 해시를 실제 복원 tree와 비교하며 branch별 reference 출처를 기록한다.
- [test_alg.py](code/test_alg.py): no-op, 식 구분, schedule 경계, tensor isolation, 실제 부모 binding을 검사한다.

실제 원본 reference hash는 `0ad957276e89e5692743ee9d8438044fe37daa48500c311746ccd949e93703c0`, CPU filtered hash는 `40e6a0c2132cfc19f0a211a8cc654b21425e681b58cd45472656f3191454abda`다. 중간45×26과 활성0..7은 receipt에 실측·기록됐다. helper critical Ruff와 compileall은 PASS다. exhaustive match 뒤로 `assert_never`를 옮긴 뒤 helper typecheck도 **0 errors / 0 warnings**로 통과했다. 전체 legacy runtime의 strict typing까지 통과했다는 뜻은 아니다. 최종 manifest SHA256은 `71be87d69e5e10d6e7ac52219123413aa4582a3f5c4b8ec6b0816b96dc8965cb`다. CPU mock·실제 cache 검사는14B OFF/ratio1 재생성의 bit-identical 결과나 GPU 영상 품질을 증명하지 않는다.


## 6. 실제 runtime 관측

[RUN_LEDGER](RUN_LEDGER.json)와 [MEASUREMENTS](MEASUREMENTS.json)를 확인했다. 사전 commit `3cd90e196307fe1f663e8533124a0cbe42f8f41e` 이후 PROBE/S/D 각1회 정상 종료, sampler1/1·실패0·재시도0, encoder P 재실행0이다. 실제40step·88forward, i0..7 ALG8step과 후반 baseline32step을 기록했다. branch hash는 CPU 생성 및 device restore/readback에서 검증된 reference를 실제 kwargs가 선택했다는 증거이며 매 forward마다 GPU bytes를 다시 해시했다는 뜻은 아니다.

final latent `[16,5,112,64]` FP32 finite/readback exact, raw `[3,17,896,512]` finite 및17f24fps MP4를 확보했다. final file SHA는 `3d76cbc4f95e881346da2500c037d413e05e79e360f8b3ef3001d0ad2ee24594`다. S guard1266.471초, sampler loop1116.131초, D guard16.184초다. 기존 B-013 MOV loop1020.890초와 비교하면 관측 조건이 다른 단일 실측이며 보장된10% walltime 증가로 해석하지 않는다.

S 최소 가용 메모리49,936,060,416bytes, CUDA allocator peak36,343,418,880bytes, cgroup peak62,941,532,160bytes다. 이 셋은 같은 메모리 지표가 아니다. cgroup high3518·OOM0·swap0, 자체 worker 종료 후 PID0를 확인했다. 모든 자산 해시를 새로 전수검증했다는 주장은 하지 않으며 대형 weights는 기존 SHA와 현재 stat/mtime 보존 근거다. 현재 감사는 실행 성공까지이며 동작·개체·시간 품질 수용을 대신하지 않는다.


## 7. 출력 관찰과 수용 경계

두 관찰자가 전체17장과 고정 local0/12/14/16을 A/B 패널로 확인하고 각각 기록을 저장한 뒤 mapping을 공개했다. A=B013 LAB_MOV, B=LAB_MOV_ALG다. 양쪽 모두 침대 착석과 지지 앞발이 유지되어 원본의 직립·앞발 들기는 FAIL이다. ALG도 후반 head/body 기울임 반응은 PARTIAL이지만 눈·주둥이·귀의 심한 번짐이 남아 충실한 roll 수용이나 전신·개체 동시 개선은 확인하지 못했다.

보조 관찰자는 ALG의 일부 초중반 코/눈 경계가 덜 번져 보인다고 기록했다. 이는 후반 손상 해소나 전체 품질 우위로 승격하지 않는다. 실제 개체와 체형 수용은 UNCERTAIN, 배경 침실 유지 자체는 실패가 아니며 접촉·그림자는 별도 미해결이다. 독립 인간 평가나 정량 유의성 검증이 아니고 실제 연속 재생을 보지 않아 temporal=UNVERIFIED다.

CPU 검토 렌더는 한 번만 실행했고, 기존 B013 PNG34장의 파일 해시 완전 일치를 확인해 그대로 재사용했다. 새 raw는 기존 양자화만 적용했다. 비교 영상17f24fps와 browser 기능·desktop/mobile CJK 표시는 PASS지만 영상 품질 수용은 아니다. 모델·threshold·강도·추가 seed를 바꾸거나 재실행하지 않았다.
