# 공식 scribble provenance

공식 source: [scribble.py](https://github.com/ali-vilab/VACE/blob/48eb44f1c4be87cc65a98bff985a26976841e9f3/vace/annotators/scribble.py), [preprocess config](https://github.com/ali-vilab/VACE/blob/48eb44f1c4be87cc65a98bff985a26976841e9f3/vace/configs/video_preproccess.py). 연산이 같은 모델 클래스만 재사용했다. ContourInference 기본9가 아니라 ScribbleAnnotator가 적용하는 residual blocks3을 쓴다.

기존 bounded local 검사에서 가중치가 없어 허용된 한 파일을 다운로드했다. [공식 immutable 배포](https://huggingface.co/ali-vilab/VACE-Annotators/blob/63512cbbe4e3a98e1636356ef2230da84649f617/scribble/anime_style/netG_A_latest.pth):17,173,511bytes, SHA256 `c686ced2a666b4850b4bb6ccf0748031c3eda9f822de73a34b8979970d90f0c6`. 전체 저장소·다른 모델·패키지는 다운로드하지 않는다.

실제 strict state_dict load와 key/shape는 extraction receipt에 남긴다. weights_only=True, FP32, eval, requires_grad=False, inference_mode, dropout 비활성, input RGB/255, sigmoid×255 clip uint8, 공식 경로의 무반전 출력이다. 추출 결과의 polarity는 생성 전에 실제 확인한다. Full-frame832×480 source33을 한 번 처리하며 SAM crop을 먼저 적용하지 않는다. 구조 추출기 종료/회수 뒤에 VACE를 실행한다.

첫 실제 CPU systemd 경로는 runpy가 script directory를 import path에 넣지 않아 sibling module import에서 실패했다. 모델 load/추출0으로 보존하고, extraction script 자신의 절대 directory를 sys.path에 추가하는 최소 수정 후 같은 경로를 다시 검사한다. 가드/정책은 변경하지 않았다.

승인 재개 후 strict load/FP32 실제 추출33장1pass를 완료했다(2.716827969초). 실제 얼굴 눈·코·귀 선이 어둡고 배경이 밝아 무반전을 유지했다. Source전체에서 나온 배경선은 I밖에서 제거했다. 구조선은 관절만이 아니며 몸통/발 내부는 희박하다. 실제 key/shape 전체는 private extraction receipt, 공개요약은 EXTRACTION.json이다.
