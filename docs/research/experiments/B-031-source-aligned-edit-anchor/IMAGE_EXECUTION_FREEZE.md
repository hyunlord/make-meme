# B-031 image execution freeze

Status: READY_FOR_PARENT_PREREGISTRATION; image calls 0.

- Official model revision: `6f3ccc0b56e431dc6a0c2b2039706d7d26f22cb9`
- Official files: 35; verified bytes: 57,720,463,453. All LFS SHA256 and non-LFS Git blob hashes PASS.
- SHA verification elapsed: 68.883s (CPU streaming, no model initialization).
- Private freeze manifest SHA256: `88fe084073d448fc22397219eb5914a754432f750bdda79cf875d4101f76cde6`
- Model verification receipt SHA256: `46b032f9b5281a6276a490f85f14317745525d9a3d57b897f4dd572838134fdb`
- Environment lock SHA256: `f20aaa4ec320d1fbda0c6be30bf02694289b0e7a63db1b3769f00ab6e5c82fca`
- Input contract SHA256: `b0c8ead21898e04b9a8739bfe851bad7d33f7cccefcdf13cc3723c3ebcd97bff`

## Fixed execution

- Six cases in animal_R1/R2, human_R1/R2, vehicle_R1/R2 order; one pipeline call each, no retry.
- Official QwenImageEditPlusPipeline; BF16; native PyTorch SDPA; 896×512; 40 steps; true_cfg_scale=4; guidance_scale=1; negative single space; CPU generator seed 20261026 per case.
- Expected 80 transformer forwards per successful image; final packed latent saved before decode. No observed inference yet.
- Local-files-only and offline execution. Tiny CUDA copy/add/synchronize/readback before large CPU weight load. Separate venv reads verified existing package sites; no package installation or environment modification.
- Memory: start72GiB available, run24GiB headroom, swap0, 64GiB own worker cgroup limit; actual fit remains UNKNOWN.
- Heavy-work cutoff 2026-10-26T20:16:41Z; final deadline20:46:41Z. Parent preregistration push must precede image calls.

## Code SHA256

- `qwen_contract.py`: `43ad6db49ef669fd6b459f0a3ef6ee726eb5d7451d965a9d3067252f6dbf692d`
- `qwen_freeze.py`: `9f4f463d08946b53789007bfd5b8c9cc754826452fc86911fd0e006c0457a262`
- `qwen_guard.py`: `e54346f5b92555a0f8af6cd237f1bdab76da836e7790027074d4619779eecb73`
- `qwen_launch.py`: `588066b85ebbc2a4df5821951ccc23380508dfa1ebadd5a83764447d16d6a2d0`
- `qwen_observe.py`: `b950b46a56c55e666d152d25b558eb6a93cf80cb7911481ffc2887fe60a658cc`
- `qwen_preflight.py`: `adc5a1bc85d53b4fa8517deaa182f55114a1978f44d9268b4058c30170d3c276`
- `qwen_runner.py`: `44cd4aa1e98aca7c8d09cf8659d56b32237d94e6a80e037a967815f437ed9077`
- `qwen_seal.py`: `234a99004a428ba900921860aad848e5e61eb8c6c623250ca2b33be67b4e5f56`

## Download boundary

- Final verified files57,720,463,453bytes plus preserved first-transport incomplete13,211,501,446bytes. Exact model-directory bytes including metadata70,931,975,386 (~66.06GiB).
- One Xet stall and one regular-HTTP transport fallback are preserved; no further retry. Prior wire retransmission bytes were not fully measured and remain UNKNOWN. File payload accounting is not an exact network accounting claim.
- CPU pytest contract tests4/4 and py_compile PASS. Mistaken unittest discovery found0 pytest-style tests and was followed by the correct pytest invocation. GPU/quality NOT_RUN at this freeze.
