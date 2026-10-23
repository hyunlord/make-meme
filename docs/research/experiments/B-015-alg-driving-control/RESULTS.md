# B-015 결과 — 마지막 ALG 대조군을 채우고 pilot 종료

**COMPLETED / 입력·실행 PASS / 전신 자세 FAIL / 목표 품질 개선 NOT_ESTABLISHED / temporal UNVERIFIED.**

ALG_STILL을 한 번 생성해 CFG/ALG × MOV/STILL 네 셀을 완성했다. 전체17프레임 정적 관측에서 두 STILL은 상대적으로 선명한 정면 착석을 유지했고, 두 MOV는 후반 머리 변화와 눈·귀·주둥이 번짐을 보였다. 네 셀 모두 원본의 뒷발 직립과 들어 올린 앞발 배치를 재현하지 못했다. ALG_STILL의 안정적인 외형은 ALG_MOV의 실패를 뒤집지 않는다. **현재 ratio0.4·초기20% ALG pilot은 종료하며 기본 생성 경로로 승격하지 않는다.**

## 사전 고정과 계보

시작 원격 HEAD `7214ed16e550169d92eaeb5e98a36fc7fc5d5a5a`, 착수 기록 `6475272931f4eff502ccb17ce7bdb8e8fa01af85`, 실행 코드·설정·입력 고정 및 원격 일치 `a2847634d45d6860ea6c0d7d9c42d7dc18781b3f`. [PLAN](PLAN.md)과 [사전 평가](PREREG_EVALUATION.md)를 출력에 맞춰 변경하지 않았다.

B-013 LAB_STILL 조건 캐시를 읽기 전용 재사용했다. 실제16leaf에서 양 CFG의 driving latent/mask4개만 MOV와 다르고, reference·CLIP·text·initial noise·generator state·scheduler 등 나머지12개는 bit-exact다. 동일 seed만 보고 동일 noise를 가정하지 않았다. STILL도 원래 반복 RGB 전체를 VAE encode한 캐시이며 MOV latent 첫 slice 복제가 아니다. [PAIR_AUDIT](PAIR_AUDIT.md), [실측 JSON](PAIR_AUDIT.json).

STILL cache SHA `1e8f065e70bfef8cd723d70575a4a04f472567950a1b2d6ba0c61d189c53e87b`에 연결한 새 filtered sidecar를 만들었다. 같은 reference에서 filtered 값 SHA `40e6a0c2132cfc19f0a211a8cc654b21425e681b58cd45472656f3191454abda`가 B-014와 일치했다. parent SHA 검사를 삭제하거나 MOV sidecar를 그대로 붙이지 않았다. 이전 MOV cache·sidecar와 STILL 원본을 종료 후에도 검증했다.

B-014의 수치 ALG·필터 구현은 byte 그대로 유지했다. 변경은 STILL parent 연결, 실행별 deadline/unit·계보 검사와 CPU 회귀검사다. [정확한 차이](RUNTIME_DIFF.diff), [고정 manifest](PREREGISTERED_CODE.json), [CPU 검사](CPU_VALIDATION.json). 11검사 PASS와 별개로 새 comparator의 타입 경계 진단2errors/7warnings는 **NOT_CLEAN**이며 숨기거나 전수 타입 리팩터링하지 않았다.

## 실제 실행

- P0, PROBE/S/D 각각1회·실패0·재시도0. 기존 CFG_MOV/CFG_STILL/ALG_MOV 재생성0. 새 모델·다운로드·학습·LoRA·imagegen·외부 생성0.
- source f7~23,512×896·17프레임·24fps,seed20261022,UniPC40,shift3,CFG5,negative empty,history=None,replace_flag=False. 기존 mixed loader·FlashAttention·tiny CUDA/anchor·분리 프로세스·안전 가드 유지. 512×896은 기존512×288에서 확대/crop된 입력이며 새 고해상도 정보가 아니다.
- 실제 branch trace는 i0~7의 `u_orig→u_low→c_low`, i8~39의 `c_orig→u_orig`를 확인했다. **40scheduler step·88forward**이며 추가 관측용 forward나 batch3는 없다. ratio0.4·45×26→112×64·bilinear/antialias=True/align_corners=False 고정. 첫 프레임 overwrite/clamp 없음.
- final latent는 finite FP32 `[16,5,112,64]`, 원자적 저장·재읽기 exact, 파일 SHA `b5af6b859f1e634235f1a6354ccdc3ae22df938b54308f7b5e1fab4a8842cd20`. 실제 값은 초기 noise와 다르다. S 정상 종료 후 D를 시작했다.
- raw는 finite `[3,17,896,512]`, MP4는17장·24fps·0.708333초이며 전체 ffmpeg decode PASS. MP4 SHA `ca1ae2335183bb7cbe1c59baa57ab62df358a5b93f551591a33c80c0d2dec16e`. 첫/끝 표본 간격은16/24초다. 24fps 저장은 원본 시간축 정합이며 모델의 학습 시간 prior 변경이 아니다.

[실제 장부](RUN_LEDGER.md)와 [JSON](RUN_LEDGER.json)에 단계·출력·실패 및 해시를 남겼다. 기술적 완료는 아래 품질 수용과 별개다.

## 정성적 2×2 비교

| guidance | MOV | STILL |
|---|---|---|
| CFG | 전신 **FAIL**: 착석·지지 앞발. 후반 머리 변화 **PARTIAL**, 얼굴·귀 번짐으로 깨끗한 roll 수용 불가 | 착석 유지, 원본 후반 roll 대응 부족. 상대적으로 선명한 정면 외형 |
| ALG | 전신 **FAIL**: 착석·지지 앞발. 후반 머리 변화와 얼굴·귀 손상 지속, 목표 동시 개선 **NOT_ESTABLISHED** | 착석 유지, 원본 후반 roll 대응 부족. 두 MOV 수준의 후반 번짐은 정적 관측에서 나타나지 않음 |

주 관측은 source·실제 Lab 참조·네 셀 전체17장을 같은 canvas에 놓은 정적 검토다. 동일 에이전트 계열의 검토이며 독립 인간 ground truth·통계적 반복으로 부르지 않는다.

- **local0/source f7:** source는 뒷발 직립·앞발을 가슴 옆에 든 상태지만 네 출력은 참조 사진의 착석과 내려놓은 앞발에 가깝다. 처음부터 전신 목표와 다르다.
- **local1~11:** 두 STILL은 정면 착석 부근이다. 두 MOV에서는 입·혀·머리의 작은 변화가 보인다. 입 닫힘은 새로운 필수조건이 아니다.
- **local12/source f19:** 두 MOV에서 얼굴 번짐이 뚜렷해지고 두 STILL은 상대적으로 선명하다.
- **local14/source f21·local16/source f23:** source의 몸통 대비 head roll이 커진다. 두 MOV도 후반 머리 기울임이 커지지만 눈·주둥이·귀의 형태가 훼손돼 정확한 방향·증가 순서·각도를 수용하지 않는다. ALG_STILL에는 같은 규모의 후반 roll이나 번짐이 보이지 않는다.

검은 짧은 털·처진 귀·넓은 주둥이·가슴·굵은 앞다리라는 견종/체형 인상은 두 STILL에서 참조와 가깝다. 그러나 참조와 유사한 정적인 착석 외형은 새로운 자세에서의 **실제 반려견 정체성 보존**을 입증하지 않는다. MOV 후반 얼굴 손상을 포함해 개체 일치는 **UNCERTAIN**이다. 원본의 옅은 털·가는 전신이 그대로 나타나는 뚜렷한 누수는 관측되지 않았으나 국소 변형 원인은 식별하지 못했다.

앞발은 침대 지지 상태로 남고, 숨은 관절·발끝 접촉·꼬리·반사 및 mask 결함의 정량 영향은 **UNCERTAIN**이다. 기존 얇은 발·꼬리·바닥 경계는 **PARTIAL_UNRESOLVED**로 유지한다. 침실 배경 보존 자체는 animation 모드의 실패가 아니다. 작은 표정·픽셀 변화 가능성이 있으므로 STILL을 프레임 복제 영상이라고 단정하지 않는다.

이 한 입력·한 seed에서는 심한 후반 손상이 ALG에만 필요한 현상은 아니며, 동적 driving 조건의 두 셀에서 나타난다는 근거를 얻었다. reference가 유일한 원인인지, 특정 attention 경로가 원인인지는 식별되지 않는다. ALG 전체 무효·상용 품질·일반화도 주장하지 않는다. 보정된 q가 없으므로 interaction/gain/유의성을 만들지 않았고17프레임을 독립17시행으로 세지 않았다.

연속 재생의 지각적 품질을 직접 관찰하지 못했으므로 **temporal=UNVERIFIED**다. viewer의 재생 기능과 MP4 디코딩 성공은 시간 품질 수용이 아니다. 후처리 warp·보간·SR·얼굴복원·선별·시간 맞춤은 없다.

## 계산비용과 보존

| 셀 | forward | S guard 초 | sampler 초 | CUDA peak allocated GiB |
|---|---:|---:|---:|---:|
| CFG_MOV | 80 | 1181.602 | 1020.890 | 33.832 |
| CFG_STILL | 80 | 1149.802 | 1013.345 | 33.832 |
| ALG_MOV | 88 | 1266.471 | 1116.131 | 33.847 |
| ALG_STILL | 88 | 1264.928 | 1119.280 | 33.847 |

같은 정의의 실측을 비교했다. NFE10% 증가가 시간10%나 품질 향상을 의미하지 않는다. 캐시 상태와 시스템 상황을 통제한 성능 benchmark가 아니다. 신규 S 최소 시스템 가용46.226GiB, cgroup peak56.806GiB, high4674·max/OOM0·swap0. high는 reclaim 압력이며 OOM과 구분한다. 시스템가용·RSS·cgroup·CUDA 회계를 중복 합산하지 않는다. [실측](MEASUREMENTS.md), [상세](MEASUREMENTS.json).

종료 후149개 hash 검사로 부모·입력·코드·설정·sidecar 보존을 확인했다. 대형 모델8개는 이전 fullSHA와 fresh stat/mtime 일치로 확인했으며 새65GB 전체 재해시를 주장하지 않는다. 자체 worker/unit은 inactive/PID0, 기존 서비스는 보존했다.

## 보기·재현·전달

비공개 `reports/output-review/review.html`과 native24fps 비교 MP4, 모든17장·사전4시점·원본 PNG를 제공한다. 기존 세 셀의51장 PNG는 byte 그대로 재사용하고 새 raw만 같은 양자화 규칙으로 변환했다. 실제 참조와 source도 포함한다. 비교 MP4는3072×928·17f24fps·0.708333초다. 브라우저 이전/다음·slider·끝점·한 번 재생 종료·loop/autoplay OFF와 desktop/mobile 표시를 검증했다. 모바일6열은 개요용이며 세부 판독은 desktop/원본PNG가 필요하다. [재현 명령](REPRODUCE.md), [한국어 수식·코드 해설과 질문/답](../../lessons/B-015-guidance-driving-interaction.md)을 연결한다. private ZIP에는 새 raw·MP4·final latent·STILL parent 캐시·새 sidecar·기존 세 셀 비교·실패/불확실성·재현을 포함하고 weights는 제외한다. 공개에는 개인 미디어·tensor·개인 절대경로를 넣지 않는다. [전달 검증](DELIVERY.md)에 양 호스트 CRC·471개 payload SHA·전송 동일성과 제외 항목을 기록했다.

## 다음 검증 가능한 가설 하나 — NOT_RUN

**animation 모드에서 reference token의 RoPE H offset만0→120으로 바꾸면, reference와 출력의 공간적 대응을 바꿔 착석 유지와 얼굴 손상 양상이 달라지는가?** [고정 SCAIL 코드](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L844-L865)는 reference H offset을 animation0/replace120으로 나눈다. 향후 검증은 replace_flag=False와 T/W offset·모든 조건·CFG·noise를 유지하고 이 값 하나만 바꾸는 가설이다. 공식 replace 모드 전체로 전환하는 제안이 아니다.

이는 자세만 제거하거나 참조 영향을 반드시 약화하는 방법이 아니다. reference와 video/pose Q/K의 상대 phase를 바꾸므로 외형·배경·동작 전체에 영향을 주며, 학습 때 없던 혼합 위치 규약이 되어 더 망가질 수도 있다. 데이터만으로 원인이 확정됐다는 주장도 아니다. 먼저 no-op와 변경 token 범위·frequency bounds를 CPU에서 검증한 뒤 별도 승인된 한 실행으로 원본 사건/전신/얼굴 보존을 비교할 수 있다. **이번에는 구현·추론·학습을 실행하지 않고 현재 ALG pilot을 종료한다.**
