# B032 이후: 생성중 제약을 마지막 혼합과 구분한다

B032는 큰 도로 그래픽을 저비용으로 복원했지만 편집 core의 작은 조각과 접촉/그림자 불확실성이 남았다. E=1 안의 오염을 실제 차량 본체 내부라고 확정할 수 없다. 따라서 mask를 좁히거나 새 support를 그리는 대신 기존 정책을 고정한다.

[통합 의뢰](../work_orders/20261027-B033-integrated-work-order-ko.md)와 [B033 PLAN](../experiments/B-033-clean-prediction-constraint/PLAN.md)에 따라 source full-resolution VAE와 같은 latent 지도를 쓰는 마지막 혼합 대조군을 둔다. 생성중 제약은 UniPC clean conversion 반환 뒤 corrector/history 이전에만 적용한다. 동일 RGB 후합성 후 남는 차이와 target회귀를 함께 본다.

원거리 pixel복사만 좋아지거나 마지막 혼합보다 이득이 없으면 추가 sampler비용을 정당화하지 않는다. 기존 동물/사람 앵커실패와 B031 결합FAIL을 소급 변경하지 않는다. 한 비교 후 종료하며 새 mask/strength/seed/model/training을 추가하지 않는다.
