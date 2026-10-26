# 종료 결정과 다음 가설 하나

## 이번 고정 방법은 채택하지 않는다

사전 기준은 적어도 두 과제의 외형·동작·장면 결합 개선과 나머지 과제의 큰 회귀 부재였다. METHOD6에서 동물 target 교체가 실패했고, 사람 R1의 의상 형태 부분 개선은 R2에서 이어지지 않았다. 차량 R2는 기준선에 없던 큰 그래픽이 생겨 보호 장면이 악화됐다. animal CONTROL은 METHOD보다 큰 배지를 남기지만 vehicle CONTROL은 오히려 METHOD의 큰 장식을 남기지 않는다. 따라서 source 대상 위치에 맞춘 이미지 출력 재가중이 일관된 개선 원인이라는 설명은 미입증이다. [결과](RESULTS.md), [대조](ABLATIONS.md).

판정은 **이번 고정 설정 NOT_ADOPTED / 결합 개선 NOT_ESTABLISHED**다. 모든 공간 가중이나 CLIP 경로가 무용하다는 일반 결론은 아니다. CONTROL을 사후 기본 경로로 채택하지 않는다. lambda·layer·schedule·seed sweep과 후속 생성은 실행하지 않는다.

## 제안만 하는 다음 한 가설

**reference VAE 토큰의 joint self-attention 경로에서 generated query로 전달되는 공간 정보를 제한하면, CLIP 출력만 조절했을 때 남은 참조 자세·보호 장면 누수가 줄어드는가?**

다음 방법 후보는 CLIP gate를 OFF로 돌리고, generated query가 reference VAE key/value를 읽는 경로만 source의 편집 지지 영역에 따라 분리 제어하는 것이다. reference 자체의 RGB·VAE 값이나 driving·text·noise를 바꾸는 실험과 섞지 않는다. source 내부의 외형 반영과 외부의 보호 장면을 동시에 평가하고, 위치를 바꾼 대조로 단순 약화 효과와 구분해야 한다. 후속 attention의 간접 확산이 남으므로 hard pixel protection이나 identity-only 표현으로 부를 수 없다.

이는 현재 모델 코드에 reference VAE joint 경로가 남는다는 사실과 이번 실패에서 고른 **미검증 가설**이다. 이번 결과가 그 경로를 원인으로 식별한 것은 아니다. 기존 FlashAttention을 보존하는 좁은 구현 가능성과 추가 attention 비용을 먼저 확인해야 하며, dense attention·새 backend·학습·새 모델로 조용히 우회할 수 없다. 현재 구현·추론·설치는 모두 NOT_RUN이다. 사용자가 결과를 검토한 뒤 별도 범위를 결정한다.
