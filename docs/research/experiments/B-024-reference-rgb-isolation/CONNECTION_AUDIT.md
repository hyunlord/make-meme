# B-024 bounded connection audit

Read-only review started18:07UTC, bounded CPU/source audit deadline18:37UTC. Parent HEAD eb9636fd42750e4b2fa350b2c09ce9268dc7f98c. PLAN,decision,CHARTER,ROADMAP,HISTORY,RECORDING_PROTOCOL read. No GPU/model call by reviewer.

## Source path checked

Actual preserved B020 phase_prepare.py hashes named preprocessed inputs before official conditioning; img/reference and pose_video/driving are separate keys, source shape/dtype/hash checked against expected_preprocessed.json. Official scail.py292 encodes ori_img rearranged TCHW->CTHW;342 sends img[:,None] to CLIP. Driving line440–444 selects pose_video segment, bilinear half-resolution and CTHW VAE encode. Arg_c/arg_null separately receive ref_latents and pose_latents and shared clip_context.

WanVAE encode accepts CTHW and applies internal (mu-mean)/std via self.scale=[mean,1/std]. Decode inverses z*std+mean internally. No external scaling is present in preserved P or D. Ref latent[16,1,64,112], pose[16,5,32,56], generated[16,5,64,112] match one-image versus17frame/stride4 and half driving dimensions.

Pinned model_scail2 concatenates reference+generated, embeds ref_masks separately, then appends pose tokens plus driving mask embedding. With no additional ref, ref_length=64*112/4=1792. unpatchify takes offset additional_ref_length+ref_length, selects exactly product(grid_sizes)=5*32*56=8960 generated tokens, reconstructs CTHW. Driving tokens after generated are excluded. B023 phase_decode loads final_latent tree[x0] and invokes official VAE decode directly; no reference slice substitution or additional normalization. Actual prior final shape[16,5,64,112] and raw[3,17,512,896] were independently verified.

## Current conclusion

No concrete swap, stale-cache, duplicate normalization or generated-offset defect found in bounded source/previous artifact inspection. This is not proof of every possible implementation detail. Actual existing-reference/driving VAE reconstructions and original reference reencode checks remain executor-owned pending evidence. Unknown cause alone does not block the authorized single RGB-background comparison.

## Actual reference PNG versus stored preprocessing tensor

Independent CPU-only inspection on Spark used existing Torch/PIL and imported only pinned scail_utils.py. Actual inputs/clip/reference.png is896x512. Pinned load_image_to_tensor_chw_normalized plus same-size center resize is torch.equal to preserved B020 preprocessed_inputs.pt[img]; direct uint8/255*2-1 is also exact with max_abs0. TensorSHA b84f6a98ac68992514c36c5debf07116e933cb5240a8948a5658f1b74cc0d023. CUDA remained uninitialized. Therefore this already-preprocessed uint8 canvas introduces no extra interpolated-float ambiguity when deriving neutralRGB; preserving pixels inside exact RED support preserves normalized source values there. This check does not imply encoder features inside support remain invariant.

## Minimal new code preflight

prepare_rgb preserves exact RED support pixels, replaces only outside with128, preserves canvas and parentassets. phase_reference performs one existingref decode and one existingpose decode, original/neutral VAE encodes onceeach, releasesVAE before CLIP original/neutralonceeach. NoT5/DiT inREF. Originalnormalizedimg SHA is checked against B020producer; originalencoded comparisons record shape/dtype/max/RMS without treating GPU roundoff as strict independent replay gate.

Derived cache expects t2/t3/t8/t9 changed and12otherssame, copies exact parent structure including devices. S hook checks actualref/CLIP/pose objectidentity with verifiedrestoredcache eachmodelcall and records firsttwoCFG bindings without extraDiTforward or observer tensorcopies. Existing oneattempt/open-x, prereg code/input/parent hashes, predecessor-clean-exit,40/80final-latent andDcontract are retained. No blocking preflight defect found. Actual reconstruction visuals and comparisonmetrics must still be reviewed beforeS; CONDITIONS_READY alone is not proof of input semantic correctness.

## Actual REF evidence and bounded final conclusion

Reference worker completed once; receipt counts exactly oldreference/driving decode1each, original/neutral VAE1each, original/neutral CLIP1each. Original VAE shape[16,1,64,112]FP32 and CLIP[1,257,1280]FP16 reencode both have max_abs0/RMS0 and cached/reencoded hashes equal. This observed exactness is not imposed as a general GPU determinism guarantee.

Independently read local oldB023/newB024 safetensor headers/payloads: all16 payload SHA values match metadata in both files; entire structure (including devices/scalars) is equal; only t2,t3,t8,t9 changed.12other leaves unchanged.

Actually viewed reference-all.png and all17frames in driving-all.png: reference reconstruction shows seatedblackLab onbed,curtains,whiteletterbox; driving reconstruction shows standingblackLab ontiles/rug/rope scene with lateheadturntowardsimageleft. Their semantics match expecteddistinctinputs, notswapped. Driving reconstruction is448x256halfresolution, notnewfullresolutionRGB. Staticview does not establish temporalquality or pixel-identicalVAE reconstruction.

BOUNDARY VERDICT: NO_CONCRETE_PIPELINE_DEFECT_FOUND within the authorized bounded connection audit. Originalinput/reencode and sourcecode/actualcachedcondition observations support proceeding with the single controlledRGB intervention. Root owns samplerGO. No additional GPU calls, preprocessing, retries, model/weight audits or asset mutation by reviewer. Audit is complete within18:07–18:37UTC window; unknownremainingmodelbehavior is not itself a newblocker.
