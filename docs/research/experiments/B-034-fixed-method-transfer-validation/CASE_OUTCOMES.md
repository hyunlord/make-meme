# 과제별 실제 결과

| 과제 | 앵커 | BASE | 최종 latent 혼합+동일POST | STEP+동일POST | 방법 판정 |
|---|---|---|---|---|---|
| rigid_R1: car-turn→classic-car | ELIGIBLE; 외형·전면 배치 정적 근거, 얇은 구조 UNCERTAIN |40/80 final latent 저장; 종료 가드로 decode NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN / 추가 이득 미평가 |
| nonrigid_R1: hike→lady-running | ANCHOR_UNSUITABLE; 큰 뒷모습으로 source 측면 보행·크기 변경 | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN / 앞단 결합 실패 |

차량 source 원본17장과 두 A0는 실제로 검토했다. 생성 영상은0개이므로 raw/post의 외형·동작·경계·접촉에 대한 PASS/FAIL을 만들지 않는다. BASE에서 나와야 할 T_t와 E/M도 미작성이다. source support만을 target support로 바꾸거나 A0 정지영상을 BASE로 제출하지 않는다.

정적 앵커의 외형 반영은 영상 동작 성공이 아니다. 인물 실패를 clean 제약의 실패로 귀속하지 않으며, 차량 latent 보존을 clean 제약의 성공으로 귀속하지 않는다. B033 방법의 강도·스케줄·마스크 정책은 바꾸지 않았다.
