# V-006 runtime contract

## Scheduler
Use the preferred existing DiffSynth official A14B example defaults: Euler flow matching,50steps,shift5,CFG5,boundary0.875. The native Wan CLI defaults (UniPC/40/12/3low) differ and are not silently mixed with this path.

The existing scheduler uses u_i=s(1-i/N), then sigma_i=5u_i/(1+4u_i), i=0,...,49. All50steps remain; strength does not truncate a pre-existing50-step schedule. Noise mixing is (1-sigma)*encoded_input+sigma*noise. Final Euler step goes to0. W1-a and W1-b start at0.7291666269302368 and0.859375, both strictly below0.875.

Only the original Wan-AI/Wan2.2-T2V-A14B low-noise expert may be loaded. No Bernini/adapted substitute; no high expert. Use on-disk bf16 conversion if original storage isfp32, bitwise verification and preserved originals. W1 has no structural/reference conditioning. Prompt is frozenS2 prompt with specified sharpness suffix.

## Resource and call accounting
Reuse isolated guarded worker and existing24GiB VRAM/offload cap; hostworker MemoryMax=MemoryHigh100GiB. This cap is a placement limit, not the full unified-memory peak. Require112GiB host available before load, inherited OOM/PSI/NVRM/external-work guards, dropcache helper and expandableallocator. No model import tests during heavy execution.

Count CFGpositive andnegative separately:50schedulersteps normally100modelcalls. First actual denoising step projects total runtime; >60minutes is BLOCKED_TIME, with partialattempt and counts retained. No extra qualityretry or separate probe. Save final latent atomically before decode, then RAW33frames andMP4. Downstream73frame full/legs derivatives remain labeledCPU composites.

## Evidence status
CPU scheduler verified before any download/model execution. Runtime implementation/weight and actualshape evidence are pending. No assertion of a successful video is implied by this contract.
