# C-005 사전 계획 — 같은 입력의 VACE 1.3B / 14B 비교

작성 2026-10-30. 작업 시작 2026-10-30T00:58:20Z. 부모 이력 e69f8672722b91c1ad07273060d3cb68ffaf7ef1, 품질 대조군 C-002 853ee952795246648b3a6e46d37d5dead03abef3. 전체 상한 6시간, 마지막 30분은 기록과 전달에 남긴다.

## 질문과 고정 비교

같은 편집 앵커·SAM 동적 윤곽·텍스트·noise·수학적 샘플링에서 공식 VACE 14B가 1.3B보다 외형·동작·장면을 함께 개선하는지, Spark의 추가 비용과 함께 비교한다. 파라미터 수 하나의 순수 인과효과는 아니다. 차량14B → 개14B 순서이며 C-002의 기존 두 LAYOUT_MOV를 재사용한다. C-004 앵커와 C-003 scribble은 사용하지 않는다.

C-001의 원본 네 앵커, C-002 실제 layout33장과 두 prompt/negative를 그대로 쓴다. 832×480·33프레임, 앵커0/32, source_fps=null, preview16fps, timebase_assumed=true. 파일 길이33/16초와 양끝 간격32/16초를 구분한다. G 양끝0/중간255, reference=None, BF16·SDPA·tiled VAE·Euler50·CFG5·shift5·seed20261028·CPU RNG·vace_scale1.0을 유지한다. adapter/TeaCache/근사 가속은 OFF다. 기존 시간 mask 압축·앵커 충돌·중간 배경 RGB 부재는 고치지 않는다.

## 공식 다운로드 사전 고정

모델 Wan-AI/Wan2.1-VACE-14B, immutable revision `539c162b1387eac9dc4c20bd3f74671309e76a4c`. config의 VaceWanModel/5120/40layers/40heads/16입출력/96VACE/8VACEblocks를 확인한다. index의 정확한 7개 diffusion shard만 확보한다. 공식 파일 크기 합계63,252,305,152bytes(약58.91GiB), 상한80GiB. index metadata.total_size는 실제 shard bytes와 다르므로 safetensors header의 dtype/offset과 실제 파일 크기를 따로 기록한다. 기존 약895GiB의 가용 저장 공간에서 파일·부분 전송·출력 공간을 확보한다. 검증된 T5/VAE/tokenizer는 공식 hash와 일치할 때 재사용한다. 전체 저장소·다른 모델·예제 자료·새 패키지를 받지 않는다.

## 적재 전 메모리 결정

기존 설치 loader와 native dtype-preserving offload만 사용한다. 저장 dtype, tensor key/shape, converter, meta 초기화, CPU/GPU transient, T5/VAE를 검사한 뒤 실제 전략을 BACKEND_COMPARISON에 고정하고 코드와 함께 inference 전에 다시 commit/push한다. 현재 후보는 diffusion offload/onload=disk, preparing/computation=BF16 CUDA, 고정24GiB native cache threshold이며 이 값은 hardcap이나 공식 안전 보장이 아니다. T5/VAE CPU 상주·일시 복사·activation을 포함해 기존 worker64GiB와 headroom 계약 안의 계획을 검토한다. 명백히 초과하는 계획을 OOM으로 시험하지 않는다. 1.3B와 다른 memory path는 QUALIFIED 비교로 밝힌다.

## 예산과 중단

정상 영상2개, 각50step/100 model_fn call 예상. heavy 최대3회(기계적 복구 예비1 포함), decode 실패 시 저장latent VAE-only 복구 전체1회. 품질 재시도0, imagegen0, SAM0, 학습0. 최초 forward도 실제 첫 생성에 포함하며 full-model smoke는 없다. 모델 적재 시작 이후 실패는 heavy에 포함한다. 실제 위험·OOM·외부 충돌·관측 실패는 기존 guard로 중단하고 자동 재시도하지 않는다. C-003/C-004의 정상 공통 guard·서비스·신원·swap/headroom 한도를 변경하지 않는다. 다른 작업을 종료하지 않는다.

## 결과를 보기 전 평가

차량: 은색 높은 차체/루프레일/창/후미등, 원본 Mini 회귀, 우측 이동·후면 노출 순서, 크기·위치, 바퀴·접촉, 빨간 전경차와 파란 표지판/배경 보호를 분리한다. C-002는 빨간 전경차가 약8부터 일찍 나타나며 source16의 파란 표지판 누락, source보다 이른 후면 노출이 있었다.

개: 검정/흰 target 외형, 크림색 source 회귀, 접근·머리 높이/방향, 보이는 앞발 배치·겹침, 울타리/풀/잔디, 형태·그림자를 분리한다. C-002는 거친 접근만 개선했고 내부 동작·접촉은 불확실하다. 29–32 원본/종료 앵커 충돌을 별도 표시한다.

전체33장, 고정0/4/8/12/16/20/24/28/32 및 개29–32를 같은 인덱스로 검토한다. 축별 BETTER/SIMILAR/WORSE/UNCERTAIN, 종합 JOINT_GAIN/APPEARANCE_ONLY/MOTION_TRADEOFF/NO_ESTABLISHED_GAIN/WORSE/INCONCLUSIVE를 사용한다. 실제 연속 지각 검수가 없으면 temporal=UNVERIFIED다. 이미지 hash/실행 PASS는 품질 증거가 아니다. 두 사례·한seed 한계를 유지한다.

## 보존과 종료

새 final latent 원자 저장/readback, raw,33 PNG, 원 MP4와 실제 noise/context/mask·단계별 비용을 남긴다. compact는 원본/참조/앵커·기존2/신규2영상·조건preview·뷰어/시트/해설이며 양 host /tmp에 CRC·manifest·추출·SHA 전송 일치를 검증한다. weights와 기존 full은 중복 포장하지 않는다. 공개 GitHub에는 비민감 코드·문서·hash만 기록한다. 완료 후 다음 모델 선택을 제한적으로 결론내고 추가 실험은 시작하지 않는다.

전체 사용자 계약: [work order](../../work_orders/C005_VACE_BACKBONE_COMPARISON_KO.md).
