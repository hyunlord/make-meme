# 2026-10-24 — B-018 구성요소 학습 검토와 B-019 결정

## 확인 범위와 현재 상태

기준 branch HEAD `19890bea9172db288960de2463b8a9f6c9233140`를 조회하고 B-018 RESULTS, ATTENTION_CONTRACT, component_runner.py, runtime_guard.py, 고정 SCAIL WanAttentionBlock/WanI2VCrossAttention 코드를 읽었다. Spark 재실행은 하지 않았다.

업로드 `make-meme-B-018-20261024-final.zip`은 container와 Python 각각 실제 읽기를 시도했으나 모두 ClientError로 실패했다. 따라서1,588,140bytes·SHA `dce2aebd3812922751c4c82d34b90fefcc6c1ec38149c707283fa186b7d650ee`·CRC·Mac/Spark 일치/추출검증은 실행 담당자 보고값이며 이번 검토의 독립 확인이 아니다. 파일이 없다고 단정하거나 sandbox 링크를 추측하지 않는다.

원격 기록상 B-018은 실제 마지막 self-attention10tensor/104,888,320base parameter에 Q/V LoRA81,920parameter를 붙여36token synthetic MSE3update를 수행했다. FA2 backward와 base 불변, initial/reload/OFF 최대차0,283.63MiB CUDA peak를 확인했다는 기록이다. 첫 A grad0, 이후 A/B finite gradient는 Bzero 초기화의 수학과 양립한다. 작은 검사 결과이며 실데이터/FlowMatching/전체40block/품질 학습은 NOT_RUN이다. runner20errors/135warnings와 helper warnings를 코드 품질 한계로 보존한다.

## 결정

실행자가 제안한 마지막 **전체 block** 확장은 적절하다. 다만 다음을 명시한다.

1. 한 block을 통과시키는 것과 모든 block parameter를 훈련하는 것은 다르다. trainable은 기존 self-attention Q/V LoRA만 유지하고 cross-attention/FFN·norm·modulation은 동결한다.
2. 손실은 block 최종 출력에 걸어 frozen cross/FFN까지의 derivative를 검사한다. frozen은 no_grad/detach와 같지 않다. residual 우회 gradient만으로 후속 경로까지 검증했다고 하지 않는다.
3. 현재 공식 image/text cross-attention은 마지막512context token을 text로 해석한다. 적절한257image+512text의 synthetic projected context와 FP32 time modulation을 제공해야 한다. 개인자료나 T5/CLIP 인코더는 필요하지 않다.
4. 36token 테스트 성공을 실제 영상 길이의 메모리로 과장하지 않는다. 별도 승인 라운드를 불필요하게 반복하지 않도록, 같은 제한 worker에서 소형 검증 후 조건부 실제 토큰 길이12992의 resource-only backward1회까지 제안한다. 실제 영상 activation/전체모델과는 다르며 optimizer update는 추가하지 않는다.
5. 명시한 최대 worker cap16GiB는 B018의8GiB와 다른 제안이다. 시스템72GiB 시작/24GiB 실행 headroom·swap0·다른서비스보호는 유지하고, 실행 담당자의 사용자 지시 전 적용하지 않는다. 추정상 cap 초과면 긴 단계는 NOT_RUN으로 남긴다.

[전체 B-019 PLAN](../experiments/B-019-transformer-block-backward/PLAN.md)

## 연구와 다음 의사결정

B-017의 자료확보·권한·target 부족은 여전히 별도 경로다. synthetic 테스트에 실제Lab target은 필요하지 않으나 그 결과를 동물품질 개선으로 바꾸지 않는다. 현재의 ALG/H120은 채택하지 않는다. 연구 목표는 로컬 이미지·영상 생성의 원리를 이해하고 검증 가능한 품질·일반화 기여로 연결하는 것이다.

B-019는 **PLANNED / NOT_RUN**. 이번 원격 수정은 PLAN/decision 두 문서 추가뿐이며 GPU/backward/optimizer/모델load/새다운로드0회다. 실제 착수·종료 때 실행자가 HISTORY/ROADMAP에 이 결정을 링크하고 단계별 관측·미실행을 갱신한다. B019후 소형 component 단계만 무한 확장하지 않고 자원 실측과 실제 사용 가능한 자료를 대조해 다음 학습 목적 하나를 정한다.
