# 외부 제작 사례에서 가져올 것 — 코드 영상, 외부 MCP, MOSS-Image

작성: 2026-10-23 · 상태: **문헌/코드 검토 완료, 실험 BACKLOG / NOT_RUN**

## 목적·기록 범위

이미지·영상 생성 연구에 참고할 후보를 공개 1차 자료와 실제 코드로 분류했다. 특정 공개 영상의 제작자가 사용한 내부 도구·추론 설정은 확인하지 못했다. 제시된 YouTube 두 영상은 이 검토 환경에서 본문/재생을 확보하지 못했으므로 시청하거나 제작 방식을 역추적했다고 주장하지 않는다. 개인 대화·스크린샷·닉네임·미디어는 이 저장소에 게시하지 않는다.

B-007F 등 현재 실행을 중단/변경하지 않으며, 활성 연구 브랜치에는 쓰지 않는다. 별도 연구 프로그램 문서 브랜치에 후보와 판단만 누적한다. 이번 모델 다운로드·설치·영상 생성·학습·유료 서비스 호출은 모두 0회다.

## 1. 같은 'AI 영상 제작'이라는 말의 서로 다른 의미

| 경로 | 실제 시각 결과를 만드는 것 | 이번 연구와의 관계 |
|---|---|---|
| 코딩 에이전트 + Remotion 등 | 에이전트가 쓴 React/타임라인 코드를 renderer가 영상화 | 실험 시각화·설명/홍보 영상·후반 편집 참고. 실사 동물의 동작 전이 모델을 대체하지 않음 |
| 에이전트 + Higgsfield/영상 API MCP | 외부 서비스의 영상 모델 | 오케스트레이션·UX 참고. 외부 생성 없는 A/B 해법으로 분류하지 않음 |
| 에이전트 + 로컬 모델 | Spark의 공개 가중치·학습/추론 코드 | B의 생성·학습·아키텍처 연구와 직접 연결 |

에이전트, tool protocol(MCP), 실제 generator/renderer, 영상 편집 레이어를 분리해야 한다. MCP 설치는 로컬 영상 생성 능력이나 무료 추론을 자동 제공하지 않는다. 'MCP 없이 생성'도 CLI/Python/HTTP 등을 통해 어떤 엔진을 사용했는지 확인해야 한다.

## 2. Remotion의 실용적 가치와 한계

공식 문서는 Claude Code·Codex 등 coding agent로 프롬프트를 받아 Remotion 영상을 만드는 경로와 Agent Skills를 안내한다. 코드가 화면 요소·시간·좌표를 정해 렌더하는 모션그래픽은 매 프레임 이미지를 독립 생성하는 과제와 다르다. 실제 동물 털·가림·체형 변화의 생성 문제를 이 사례의 성공으로 해결됐다고 보지 않는다.

연구에서의 제안: 동일 source time을 갖는 비교 영상, frame ID/샘플링 step 표시, 관측점·메모리 그래프·수식 애니메이션, 논문 supplementary 영상. 원본/생성 영상 자체를 미화하거나 속도/프레임을 바꾸지 않는 presentation layer로만 사용한다. 현재 ffmpeg로 되는 작업을 위해 의존성을 즉시 추가할 필요는 없다.

현재 공식 Remotion 문서는 예전 documentation MCP가 deprecated이고 Agent Skills 및 /remotion-docs를 권장한다고 명시한다. MCP가 언제나 제품의 필수 중심이어야 한다고 가정하지 않는다. 배포·제품화 시 Remotion 라이선스의 현재 조건을 별도로 확인해야 한다.

근거:
- https://www.remotion.dev/docs/ai/coding-agents
- https://www.remotion.dev/docs/ai/skills
- https://www.remotion.dev/docs/ai/mcp
- https://www.remotion.dev/license

## 3. Higgsfield와 Seedance

Higgsfield 공식 MCP 문서는 외부 생성 도구·여러 모델·기존 자산 이력·credit 과금을 안내한다. 공식 help center는 MCP/CLI 자동화가 크레딧을 사용하고 웹 Unlimited와 구분됨을 명시한다. 따라서 '에이전트에서 만들었다'는 것은 생성 엔진이 에이전트 자체거나 로컬이라는 증거가 아니다.

Seedance 2.0 공식 페이지는 text/image/audio/video 조건의 멀티모달 영상 생성·편집을 설명한다. 단편적 'Seedance MCP'라는 표현만으로 특정 MCP 구현·공식 여부·가중치 로컬 실행 가능성을 확정할 수 없다. 이번에는 특정 Seedance MCP 설치/검증은 하지 않았다.

우리 결정: 외부 모델은 선택적 별도 제품 비교/UX 참고 후보일 뿐, A의 native imagegen 전용 제한과 B의 로컬 모델 제한을 우회하는 fallback으로 도입하지 않는다.

근거:
- https://higgsfield.ai/mcp
- https://higgsfield.ai/creator-hub/help-center/integrations/what-is-higgsfield-mcp
- https://seed.bytedance.com/en/seedance2_0

## 4. MOSS-Image: 이미지 생성·효율화 연구 후보

OpenMOSS 공식 README와 Hugging Face model cards는 5B image DiT backbone, Qwen3.5 계열 text encoder, FLUX.2 VAE, Base/SFT, 자연어/tag/JSON layout 입력과 Flow-matching Euler sampler를 설명한다. 이미지 생성 모델이며, 해당 공개 경로를 시간적 영상 생성/실제 Lab의 reference-conditioned motion transfer 지원으로 확대하지 않는다. 현재 공개 T2I 인터페이스와 이미지 편집·개체 참조 기능은 구분해야 한다.

실제로 읽은 DiffSynth 문서/코드:
- docs/en/Model_Details/MOSS-Image.md (읽은 blob: fc6c3339196ff65f8bd6c62ed4c79f67bee029a1)
- examples/moss_image/model_inference_low_vram/MOSS-Image-EntroPack.py (읽은 blob: 462aee89cd3999ba6f22c6cc3219be243080dd54)
- README.md의 2026-10-20 항목

DiffSynth의 2026-10-20 공식 안내는 EntroPack 3.5bit 모델을 최소4GB VRAM에서 추론할 수 있다고 주장하며, OPD로 가속한 8step TurboLoRA도 연결한다. 이는 배포팀의 구성별 안내이고 본 연구자가 독립 측정한 Spark 수치가 아니다. 저VRAM 예제는 디스크 offload/onload, CUDA BF16 preparation/computation, 별도 text encoder/VAE, VRAM budget을 사용한다. 현재 예제의 기본 quant package와 3.5bit 최소 구성은 같다고 가정하지 않는다.

중요한 구분:
- '4GB VRAM 추론 가능'은 전체 가중치/CPU RAM/디스크가4GB라는 뜻이 아니다.
- 5B backbone의 BF16 가중치만 단순 계산으로 약10GB이며 text encoder/VAE/activation은 별도다.
- low-bit storage와 실제 GEMM precision·커널 가속은 다르다.
- 이미지1장 저메모리 추론은 영상 생성·학습 메모리·처리 속도 보증이 아니다.
- Spark는 통합메모리이므로 CPU offload가 총 물리 메모리를 자동 절감한다고 가정하지 않는다.
- official current DiffSynth를 기존 VACE/SCAIL 고정 환경에 바로 업데이트하지 않는다. 후속 실험은 격리·commit 고정이 필요하다.

근거:
- https://github.com/OpenMOSS/MOSS-Image
- https://huggingface.co/OpenMOSS-Team/MOSS-Image-Base
- https://huggingface.co/OpenMOSS-Team/MOSS-Image-SFT
- https://github.com/modelscope/DiffSynth-Studio/blob/main/docs/en/Model_Details/MOSS-Image.md
- https://github.com/modelscope/DiffSynth-Studio/blob/main/examples/moss_image/model_inference_low_vram/MOSS-Image-EntroPack.py
- https://github.com/modelscope/DiffSynth-Studio (2026-10-20 announcement)

## 5. 次순위 연구 후보·학습 목표 — 전부 실행 미승인

### H-MOSS-LAYOUT: 구조화된 텍스트가 실제 공간 제어로 작동하는가?

동일 모델/seed/해상도에서 자연어와 JSON layout을 비교한다. box 좌표를 바꿀 때 객체/텍스트가 움직이는지, identity와 무늬가 얼마나 바뀌는지, 객체 수·가림·관계에 대한 추종을 따로 본다. JSON은 hard constraint나 3D geometry 정답이 아니다. 파이프라인의 prompt serialization/text token 처리를 확인하고 사람의 시각 평가·측정 오차를 기록한다. 현재 영상 연구의 reference/structure 역할 분리 문제를 더 작은 정적 과제로 공부할 수 있는 후보이나, 2D layout 성공은 동물 안무 전이의 증거가 아니다.

### H-MOSS-EFFICIENCY: 양자화와 step 증류의 손실을 분리하는 비교

먼저 원정밀도50step 기준선, 그 다음 precision만 변경, 그 다음 student/step만 변경하는 식으로 분리한다. 동일 prompt·일반 구성·글자·세부 무늬·layout control 등 조건별 품질과 wall-clock, model-call count, GPU peak, 시스템 peak, I/O를 함께 본다. 같은 seed 숫자만으로 다른 scheduler/student가 정확히 같은 stochastic path를 공유한다고 가정하지 않는다. 이것은 처음에는 재현/학습 과제다. 논문 기여라면 새로운 발견·방법과 강한 선행 비교·일반화가 추가로 필요하다.

## 6. 현재 결정과 히스토리

- 2026-10-23: 공개 자료/코드를 읽어 세 경로를 구분하고 위 사실·한계를 기록함. 사용자에게 특정 데모를 실제 시청했다고 말하지 않음.
- 우선순위: 실행 중인 SCAIL B-007F와 첫 영상 baseline 확보는 유지. MOSS-Image+layout/quantization/distillation은 작은 이미지 모델 학습 후보 BACKLOG. Remotion은 표현/검토 자동화 후보. 유료 MCP는 UX 참고만.
- 새 실험 지시·다운로드·학습·예산 승인은 없음. 별도 문서 브랜치의 이 노트만 추가하며 연구 실행 브랜치·현재 코드·환경은 변경하지 않는다.
