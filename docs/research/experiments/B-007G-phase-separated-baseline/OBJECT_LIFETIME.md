# 객체 수명과 사본 구분

아래 `upstream` 위치는 E의 실제 실행 복사본 기준이다. F는 동일 loader/component 생성 경로를 계승했다. Python 참조 수와 tensor storage 수를 구분하며, allocator·page cache 회수 시점은 실측 없이는 UNKNOWN이다.

| 객체 | 생성·보유·종료 | 사본/alias 판단 | 실제 코드 위치 |
|---|---|---|---|
| DiT meta model / expected state_dict | meta 생성 → key/shape 검증 → 실제 assign. expected/parameters는 함수 반환 때 해제 | meta state는 대형 실물 payload가 없다 | E `code/staged_loader.py` L73–89, L120–124 |
| safe_open/get_tensor | context 안에서 tensor별 view 획득 | BF16 cast는 새 CPU payload. FP32 동일 dtype/device는 기존 storage를 alias할 수 있음 | 같은 파일 L83–100 |
| cast_state | cast payload 누적 → strict assign=True → dict 삭제 | model과 cast_state는 assign 후 동일 payload 참조. dict 삭제는 model parameter 삭제가 아님 | 같은 파일 L95–110 |
| mmap backing | FP32 parameter가 view를 유지할 수 있음 | safe_open context 종료만으로 모든 mapped/page-cache 메모리가 즉시 해제된다고 보장하지 않음 | 같은 파일 L69–71, L95–101 |
| T5 model/checkpoint | CPU model 생성, 임시 CPU mmap checkpoint load 후 self.model 보유 | default load_state_dict는 destination model로 복사. 임시 checkpoint dict 수명과 OS page-cache 수명은 다름 | E `upstream/wan/modules/t5.py` L493–508 |
| CLIP model/checkpoint | CUDA 생성 → 임시 CPU mmap state 복사 → visual 후 model.cpu | `.cpu()`는 객체 해제 아님; pipeline이 계속 참조 | E `upstream/wan/modules/clip.py` L503–517; `wan/scail.py` L341–344 |
| VAE model/scale | meta→assign 로드 후 CUDA; mean/std/scale도 self에 보유 | scale의 mean은 self.mean alias; reciprocal std는 별도 작은 tensor | E `upstream/wan/modules/vae.py` L607–645 |
| VAE feature caches | encode/decode 시작과 정상 종료마다 clear_cache | 다음 decode가 이전 encode feature cache를 요구하지 않음. 예외 중단 시 객체는 프로세스 종료까지 살아 있을 수 있음 | 같은 파일 L516–545, L567, L582–588 |
| pipeline components | 생성자에서 T5/VAE/CLIP/DiT를 self 속성으로 보유; generate 중 삭제 없음 | 조건 계산이 끝나도 encoder weight 수명은 유지됨 | E `upstream/wan/scail.py` L92–121, L329–344 |
| context/ref/pose/masks | generate 지역변수 및 arg_c/arg_null이 참조 | 두 dict는 같은 clip/ref/pose/mask storage를 재사용; list wrapping은 tensor 복사 아님 | 같은 파일 L486–512 |
| sample_func closure | self, scheduler, conditions 등의 외부 지역변수 참조 | closure 생성 자체가 weight 복사를 만들지 않음. 실제 device 이동/연산만 따로 추적해야 함 | 같은 파일 L350–389 |
| runtime forward/attention hooks | hook handles 및 wrapper closure가 record와 원래 함수를 보유 | describe는 metadata만 저장. Q/K/V tensor 자체를 record에 넣지 않음 | F `code/runtime_infer.py` L76–101 |
| initial noise observer | 생성 noise를 detach().cpu()하여 hash 및 파일 저장 | 명시적 작은 CPU copy. wrapper 지역 cpu는 반환 시 사라짐; 원래 CUDA noise는 sampling 변수에 남음 | 같은 파일 L111–121 |
| F transition provenance | config/input/model manifest 및 scale 숫자 목록 보관 | GPU model/weights를 전역 provenance에 복제해 넣지 않음 | F `code/runtime_transition.py` L29–48 |
| 최종 latent 저장 | 마지막 update 뒤 x0만 bounded CPU copy 예정 | F에서 NOT_REACHED. 이번 trace에 final latent가 있다고 취급하지 않음 | 같은 파일 preserve_final |

CPU/CUDA tensor가 같은 통합 RAM을 사용한다는 사실은 tensor storage가 zero-copy alias한다는 뜻이 아니다. 반대로 `.to()` 호출 수만으로 항상 새로운 물리 payload가 만들어졌다고 단정할 수도 없다. 정확한 transfer 전후 관측과 dtype/device 조건이 필요하다.
