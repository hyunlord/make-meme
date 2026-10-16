# make-meme

뮤직비디오나 짧은 영상 속 인물을 **사진 속 사람이나 동물로 바꾼 밈 영상**을 Claude와의 대화만으로 만드는 MCP 서버입니다.
무료 오픈소스(Apache-2.0)이고, 생성은 무료 오픈 모델(MoCha, SAM 3)로 [ComfyUI](https://github.com/comfyanonymous/ComfyUI)에서 돌아갑니다.

> "니온 뮤비 30초부터 5초, 가운데 가수를 우리 집 시바견으로 바꿔줘"

## 할 수 있는 것

- **링크만 줘도 됨**: YouTube, Shorts, TikTok, Instagram 릴스, Threads, X 등 링크에서 영상과 이미지를 가져옵니다.
- **텍스트만 줘도 됨**: 영상이나 사진 없이 텍스트로 검색해서 고를 수 있습니다(`search_media`). 결과는 번호가 붙은 썸네일로 보여 줍니다.
- **영상을 보고 고르기**: `inspect_media`가 스토리보드와 장면 기준 추천 구간을 보여 줍니다.
- **밈 트렌드 분석**: `analyze_meme_usage`가 숏폼·챌린지 영상의 오디오를 원곡과 대조해서, 사람들이 노래의 어느 구간을 몇 초로 쓰는지 알려 줍니다.
- **세로 자동 리프레이밍**: `reframe_video`가 인물을 따라가는 9:16 크롭을 만들어서, 작게 나온 인물도 크게 교체할 수 있게 합니다.
- **여러 명 동시 교체**: 1번 인물은 내 사진으로, 2번 인물은 강아지로 바꾸는 식입니다. 한 대상에 여러 각도의 사진을 줄 수 있습니다(전신 + 얼굴 클로즈업).
- **프롬프트로 연출**: "선글라스 끼고 신나게"처럼 지시할 수 있고, 시드를 바꾼 여러 버전(`variations`)을 만들어 고를 수 있습니다.
- **원본 음악 유지**: 결과 영상에 원본 오디오를 다시 입힙니다.

## 설치

```bash
git clone https://github.com/kwanhyeonpark-ctrl/make-meme && cd make-meme
uv sync
uv run make-meme install       # ComfyUI + 노드 + 모델 (~23GB)
uv run make-meme comfy start   # 밈을 만드는 동안 켜 두기
claude mcp add make-meme -- uv run --directory "$PWD" make-meme-mcp
```

GPU가 부족하면 [`notebooks/remote_comfyui.ipynb`](notebooks/remote_comfyui.ipynb)를 Kaggle이나 Colab(무료 T4)에서 실행하고, 출력된 URL을 `COMFY_URL`로 지정하면 됩니다.

### 성능 (실측)

- M4 Max 36GB: `draft`(512x288) 기준 1초 클립의 샘플링 스텝 하나에 약 50초가 걸립니다. 480p 이상은 다른 앱을 닫아야 할 만큼 메모리가 필요합니다.
- 고화질(720p)은 NVIDIA 20GB 이상이나 원격 GPU를 권장합니다.
- 5초 이하 클립이 가장 빠릅니다. 영상은 81프레임(16fps 기준 약 5초) 단위로 나눠 처리합니다.

자세한 내용과 모델 라이선스: [docs/engine-setup.md](docs/engine-setup.md)

## 도구 흐름

`search_media` / `load_media` → `analyze_meme_usage` / `inspect_media` → (`reframe_video`) → `detect_subjects` → `swap_subjects` → `get_job`

원샷 도구: `make_swap_meme(video_query="...", image_query="...", prompt="...")`

## 확장하기

새 생성 방향(사진→영상, 이미지 편집 등)은 **레시피**(ComfyUI 워크플로 + YAML 하나)를 추가하면 붙습니다. 새 사이트나 검색 백엔드는 **플러그인**으로 추가합니다. → [CONTRIBUTING.md](CONTRIBUTING.md)

## 책임 있는 사용

동의받은 사람이나 내 반려동물 사진만 쓰세요. 결과물 메타데이터에는 AI 생성 표시가 들어갑니다. → [RESPONSIBLE_USE.md](RESPONSIBLE_USE.md)

## 라이선스

코드는 Apache-2.0입니다. 모델 가중치는 각자의 라이선스를 따르며(MoCha는 AGPL-3.0, SAM 3는 SAM License), 사용자가 원 배포처에서 직접 내려받습니다.
