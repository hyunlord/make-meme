# B019 공식 full-block 계약 요약

고정 revision과 두 파일 hash는 source-audit.json에 있다. 소스 판독이며 실제 GPU 실행 증거가 아니다.

- model_scail2.py L384–461: norm1→time scale/shift→self_attn→gate residual→norm3→I2V cross-attn→residual→norm2/time scale/shift→FFN(Linear5120→13824/GELU tanh/Linear13824→5120)→gate residual.
- L331–375: context 마지막512=text, 앞=image. image/text FA는 같은Q를 쓰지만 서로 별도 softmax이며 출력합 뒤 o projection. context769이면257+512다.
- norm1/2는 affine 없는 WanLayerNorm, norm3는 cross_attn_norm=true이면 affine norm이다. 실제 state/config에서 flags를 확인해야 한다. modulation은 저장된 [1,6,5120] parameter이고 e FP32를 더한다.
- norm, RoPE, block, FA wrapper에는 no_grad/detach가 없다. autocast(enabled=False) 또는 FP32 autocast 경계는 gradient 비활성화가 아니다. wrapper 추가 코드의 graph는 별도로 검증한다.
- residual 때문에 최종 self-LoRA gradient만으로 cross/FFN branch 미분을 증명할 수 없다. image/text K/V, crossQ 및 FFN 내부 output의 scalar gradient hook과 실제 FA backward node를 함께 확인한다. frozen weight grad=None이어도 input derivative가 있어야 한다.
- 마지막 full block 하나만 가져오는 state 선택과 strict load가 필요하다. self_attn10 tensor로 full block을 검증했다고 하면 안 된다. checkpoint 전체 hash 재검증과 선택값 hash 재검증도 구별한다.
- 한 block forward에는 FA3회(SA,image,text)가 있다. 작은8block forward는24attention forward이며 긴1block forward가 추가되면 총27이다. 실제 call count는 receipt에서 확인하고 이 예상식을 실행 결과로 쓰지 않는다.

근거: [공식 model](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/model_scail2.py#L331-L461), [공식 FA wrapper](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/wan/modules/attention.py#L24-L136).
