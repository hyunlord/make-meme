# CONTINUATION_01 delivery

Results basis: `9b5cb57cb67135e1b98c6c613aaa95a03bdbffff` on `docs/b-research-20261022`. This receipt follows archive sealing; no circular archive-hash dependency.

## Private archives

### make-meme-B034-CONTINUATION01-compact-20261027.zip

- Size: **13,511,163 bytes** (12.89 MiB).
- SHA256: `19f1af63fedc3b826de30c710aaa2d7aabdfc608746605827714731ed06eac54`.
- Spark: `/tmp/make-meme-B034-CONTINUATION01-compact-20261027.zip`.
- Mac: `/tmp/make-meme-B034-CONTINUATION01-compact-20261027.zip` (actually transferred).
- 117 payload files plus PAYLOAD_MANIFEST.json; 118 ZIP members.
- Both hosts: CRC PASS, actual extraction PASS, every payload size/SHA256 PASS. Whole archive size/SHA256 equal after transfer.

### make-meme-B034-CONTINUATION01-full-20261027.zip

- Size: **86,416,881 bytes** (82.41 MiB).
- SHA256: `58c2af46a4188decc7bef87bf8d0b564b06d77e0bc8b90a3cd6dd92957014541`.
- Spark: `/tmp/make-meme-B034-CONTINUATION01-full-20261027.zip`.
- Mac: `/tmp/make-meme-B034-CONTINUATION01-full-20261027.zip` (actually transferred).
- 127 payload files plus PAYLOAD_MANIFEST.json; 128 ZIP members.
- Both hosts: CRC PASS, actual extraction PASS, every payload size/SHA256 PASS. Whole archive size/SHA256 equal after transfer.

Compact includes SOURCE/TARGET/A0/R_star, preserved BASE/CONTROL previews, new same-E RGB_POST previews, two comparison videos, full17 and fixed local0/8/16 sheets, support visualization, viewer, reports, code, and failure evidence. It excludes raw/latent/cache/weights.

Full contains the new CONTROL raw/final latent, exact new E/M, S/T support, reproduction and failure evidence. No STEP output exists. Existing 93.6MB BASE raw, old ZIPs, model weights and condition cache are not duplicated. The new CONTROL raw remains lossless FP32. Compact media and full numerical evidence are separate.

Open `review.html` in compact. `post-comparison.mp4` (892,430 bytes) shows SOURCE / BASE_RGB_POST / FINAL_RGB_POST; `raw-comparison.mp4` (931,086 bytes) shows SOURCE / BASE / FINAL. Both are newly CPU-encoded native-size three-panel previews, 2688×512, 17 frames, assumed24fps. Individual existing SOURCE/BASE/CONTROL MP4 files were byte-copied unchanged.

## CPU and delivery costs

| Operation | Measured wall seconds |
|---|---:|
| Manual/agent coarse support annotation and static review | 249.78 |
| CPU E/M freeze | 1.759 |
| BASE RGB_POST + encode/validation | 2.070 |
| FINAL RGB_POST + encode/validation | 1.999 |
| Raw comparison encode/validation | 0.503 |
| Post comparison encode/validation | 0.395 |
| Compact packaging + Spark extraction/hash verification | 0.325 |
| Full packaging + Spark extraction/hash verification | 3.581 |
| Two ZIPs Spark→Mac, 99,928,044 bytes | 117.785 |
| Mac compact extraction/hash verification | 0.079 |
| Mac full extraction/hash verification | 0.545 |

These are measured subcommands, not a total CPU-runtime sum. Preparation/document edits and stage-copy elapsed time were not individually instrumented. GPU costs and failed STEP loading remain in COSTS/MEASUREMENTS; no GPU retry was performed.

Chrome verified five video metadata/playback advancement, local0/16 seek, previous/next, links, keyboard focus and 375/768/1280px overflow. Agent inspected desktop/mobile/matrix screenshots. Own browser exited; file URLs were used without a local server. This does not establish human temporal quality: temporal remains UNVERIFIED.

The first metadata staging copy encountered a remote-path parent symlink not resolvable on Mac. It was retained as link metadata; only regular evidence files were copied. No evidence was invented and no GPU work was repeated.

STEP failed before first forward and remains unassessed. This delivery does not complete the planned three-way visual comparison or convert target appearance FAIL into PASS. Private media remain outside GitHub; DAVIS research attribution/use restrictions are included.
