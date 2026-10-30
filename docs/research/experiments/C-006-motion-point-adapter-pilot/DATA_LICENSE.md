# C-006 자료·추적기 사용 근거

비상업 연구 pilot이다. 원본 미디어·학습 cache·weights는 공개 Git에 포함하지 않는다.

DAVIS 2017 TrainVal 480p는 B-027에서 확보한 공식 archive를 재사용한다. 신규 미디어 인터넷 다운로드는0이다. Archive의 `DAVIS/README.md` Credits에는 일반 CC BY 4.0 문구가 있으나 Terms of Use에는 **CC BY-NC 4.0** 링크가 명시돼 있다. 이 불일치를 숨기지 않고 비상업 제한을 적용한다. Sequence별 출처는 함께 보존한 `DAVIS/SOURCES.md`를 따른다. 공개 URL이나 benchmark 코드를 영상의 무제한 이용 권한으로 해석하지 않는다. Compact 전달은 이번 비상업 검토 범위이며 공개 재배포 허가로 확대하지 않는다.

출처: https://davischallenge.org/davis2017/code.html
인용: Pont-Tuset et al., The 2017 DAVIS Challenge on Video Object Segmentation, arXiv:1704.00675; Perazzi et al., A Benchmark Dataset and Evaluation Methodology for Video Object Segmentation, CVPR2016.

CoTracker 공식 source revision `82e02e8029753ad4ef13cf06be7f4fc5facdda4d`의 `LICENSE.md`는 CC BY-NC 4.0이다. 원저작자 Meta Platforms, Inc. 및 affiliates 표기를 보존한다. 공식 `scaled_offline.pth` 한 파일의 배포 revision은 `bf55ea50d4390e1820a267f131cd6587240fb2c5`이다. 실제 크기·SHA256·최소 source 목록은 별도 비공개 provenance receipt에 보존한다. 이 연구 시스템을 상업 배포 가능하다고 분류하지 않는다.

https://github.com/facebookresearch/co-tracker/blob/82e02e8029753ad4ef13cf06be7f4fc5facdda4d/LICENSE.md
https://huggingface.co/facebook/cotracker3/tree/bf55ea50d4390e1820a267f131cd6587240fb2c5

GT instance mask를 사용하므로 MASK_GIVEN / DATASET_MASK_ASSISTED이며 SAM 추론이나 자동 객체 선택 성능을 검증하는 실험이 아니다. Split은 이번 adapter 학습에서의 원본 영상 단위 분리이며 backbone 사전학습과의 중복은 UNKNOWN이다.
