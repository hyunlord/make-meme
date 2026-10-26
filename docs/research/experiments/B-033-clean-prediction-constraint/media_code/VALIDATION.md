# B-033 delivery media validation

The review build completed in 3.03s on Mac (process maximum RSS 88,375,296 bytes; reported footprint 75,907,600 bytes; swaps0). It copied eight MP4s without transcoding, produced paired all17 and local0/8/16 sheets, and copied the existing B032 support visualization unchanged. RSS and footprint are distinct counters, not additive.

All eight MP4s were inspected with ffprobe: 896×512, 17 decoded frames, 24fps preview, 0.708333s file duration. The original source FPS remains unknown. SHA256 matched each copied origin. Three existing videos were preserved; five new decoded/composite encodes are derived artifacts.

Actual existing Chrome headless/CDP testing completed in 17.22s. All eight videos loaded and advanced with a user-gesture playback call; local0/16 slider, pause, no-loop/no-autoplay behavior, keyboard focus, and local links passed. Viewports 1280×900, 768×1024 and375×812 had no page horizontal overflow. Agent inspection of these screenshots found readable controls/cards and no overlapping text. Browser QA is functional evidence only, not continuous human viewing or temporal quality acceptance.

The byte-preserved source MP4 is GBRP and displays green/magenta in this Chrome path. The viewer explicitly warns about this codec limitation and points to the correct RGB frame sheets/compatible player. That screenshot is not the source color ground truth. The other seven videos are YUV420P. Temporal quality remains UNVERIFIED.

The compact payload excludes raw tensors/latents and duplicate individual PNG frames. Full preserves the three new raw outputs, source/final-only/step latents and actual E/M. Archive CRC, actual extraction, per-file hashes, transfer identity and archive bytes/SHA are recorded only after sealing, in the final delivery receipt. These media checks do not pre-claim archive verification.
