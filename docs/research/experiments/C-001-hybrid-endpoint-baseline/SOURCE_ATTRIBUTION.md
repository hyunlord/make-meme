# 입력 계보와 공개 범위

기존 로컬 DAVIS2017 TrainVal480p 자료를 재사용했다. 이번 추가 미디어 다운로드는0이다. 공식 배포 페이지는 [DAVIS2017 Downloads](https://davischallenge.org/davis2017/code.html)이며, 연구용 이미지·annotation 배포와 인용 정보를 확인했다. 원본 JPEG/annotation의 정확한 선택과 해시는 `INPUTS.json`에 있다.

- source: `car-roundabout` 프레임30..62, target reference: `car-shadow` 프레임0.
- source: `dog` 프레임0..32, target reference: `dog-gooses` 프레임85.
- source33장 각각은 실제로 다른 원본 프레임이다. 기존17장을 복제해 늘리지 않았다.
- reference crop은 기존 RGB에서 target bbox와 고정 margin으로 추출한 보조 입력이며 새 외형을 합성한 reference가 아니다.

공식 인용: Jordi Pont-Tuset 외, [The 2017 DAVIS Challenge on Video Object Segmentation](https://arxiv.org/abs/1704.00675),2017; Federico Perazzi 외, [A Benchmark Dataset and Evaluation Methodology for Video Object Segmentation](https://openaccess.thecvf.com/content_cvpr_2016/html/Perazzi_A_Benchmark_Dataset_CVPR_2016_paper.html),CVPR2016.

이번 확인만으로 각 사진·영상·파생 생성물의 공개 재배포 허용을 확정하지 않는다. 공개 GitHub에는 코드·비민감 manifest·한국어 결과 문서만 게시하고, 입력·앵커·생성 영상은 요청된 사적 검토 ZIP과 연구 저장소에 보존한다. 완전 로컬 생성 시스템 성과가 아니라 native imagegen과 로컬 VACE를 연결한 hybrid 기준선이다.
