# B034 delivery interface

Reuses B033 sheet, Chrome/CDP and ZIP integrity code. No media is fabricated for an unrun branch. The builder reads a private JSON manifest (never publish its actual host paths):

```json
{"cases":[
  {"case_id":"rigid_R1","task_root":"${RUN_ROOT}/tasks/rigid_R1",
   "source_image":"${RUN_ROOT}/qwen-inputs/rigid_R1/image1.png",
   "target_image":"${RUN_ROOT}/qwen-inputs/rigid_R1/target-native.jpg",
   "target_model_image":"${RUN_ROOT}/qwen-inputs/rigid_R1/image2.png",
   "anchor_image":null,"reference_image":null,
   "anchor_status":"NOT_RUN","video_status":"NOT_RUN","reason":"Actual stage status",
   "completed_outputs":[],"frozen_crops":[]},
  {"case_id":"nonrigid_R1","task_root":"${RUN_ROOT}/tasks/nonrigid_R1",
   "source_image":"${RUN_ROOT}/qwen-inputs/nonrigid_R1/image1.png",
   "target_image":"${RUN_ROOT}/qwen-inputs/nonrigid_R1/target-native.jpg",
   "target_model_image":"${RUN_ROOT}/qwen-inputs/nonrigid_R1/image2.png",
   "anchor_image":null,"reference_image":null,
   "anchor_status":"NOT_RUN","video_status":"NOT_RUN","reason":"Actual stage status",
   "completed_outputs":[],"frozen_crops":[]}
]}
```

Expand paths locally before use. Parent assigns anchor status after actual inspection. Add actual A0/R_star paths only when files exist. No fallback to a different anchor. ANCHOR_UNSUITABLE forbids completed video outputs.

Each task has `inputs/source/000.png..016.png`, `inputs/driver.mp4` and eligible output directories under `outputs/`: SOURCE_RECON, BASE, BASE_RGB_POST, FINAL_LATENT_ONLY, FINAL_LATENT_ONLY_RGB_POST, STEP_CONSTRAINED, STEP_CONSTRAINED_RGB_POST. A completed output must contain output.mp4 and all17 frames. `completed_outputs` explicitly lists actual files accepted by execution, not inferred from a planned label. Missing methods are visibly NOT_RUN.

`frozen_crops` comes from the pre-STEP case evaluation freeze, never from choosing a favorable STEP result. Empty crops on an unsuitable anchor do not trigger invented detail sheets. All17 source/input observation remains available.

Run `python build_review.py PRIVATE_REVIEW_MANIFEST.json DEST`. The HTML embeds only portable case paths and actual status; absolute roots are omitted. Packaging and `check_viewer.py DEST` are run after final reports exist. Existing MP4 bytes are copied/hash-checked; new generation/composite encodes remain separate derivatives. No video transcoding in this delivery code.

Compact retains source/reference/actual anchors, eligible raw/post videos, sheets, viewer and reports. Full adds new raw/latent, annotation and provenance only. Exclude weights, whole old archives, redundant frame duplicates and duplicate condition caches. Seal only after the research SHA is fixed; validate CRC, actual extraction, payload hashes and Spark/Mac byte identity. Temporal quality remains UNVERIFIED.

Confirmed anchor path: `${RUN_ROOT}/anchors/{case_id}/A0.png`. Eligible R_star: `${RUN_ROOT}/tasks/{case_id}/inputs/anchor/reference.png`; sibling reference-mask.png/support.png/polygon-preview.png/mask-receipt.json are provenance. Task `MASK_FREEZE.json` records frozen support; parent supplies pre-STEP crop windows. Do not infer eligibility from existence of an A0 file.

Minimal final browser verification is one inherited Chrome/CDP pass over the actual branch: two case sections, loaded images and available videos, all local links, no loop/autoplay, shared play/pause/seek and previous/next frame buttons; 1280/768/375 viewport screenshots with one agent inspection. An anchor-failed branch has SOURCE playback only, A0 and explicit video NOT_RUN; it does not need fictional BASE/FINAL/STEP to pass the viewer checks. Only final actual media is inspected; no synthetic visual success fixture or repeated reviewer loop.

Optional private `source_preview` points to an explicitly new PNG-derived yuv420p compatibility preview. This was required after actual Chrome GBRP source color failure. Builder only byte-copies it and records original driver SHA separately. Compact uses preview; full preserves the original driver MP4. Existing source and runtime input remain unchanged. Encoding command, original/preview/frame hashes and wall time are separate private receipts. Do not describe all delivery media as re-encoding zero.
