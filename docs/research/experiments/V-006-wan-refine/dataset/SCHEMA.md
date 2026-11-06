# SAMPLE schema v1.1: refinement lineage

Inherit every V-005 schema v1.0 asset, provenance, output and human-review field. Each actual V-006 generation gets one private SAMPLE; CPU full-window and legs-only reinsertion clips are derivatives of that sample, never additional generations.

`parent_sample` is required for refinement outputs. It contains the actual input sample's `sample_id`, `source_run_id`, absolute private `path`, `kind=file`, `bytes`, `sha256`, and `relationship=REFINEMENT_INPUT`. Read and hash the parent record before publishing. The input segment mapping and preserved full input frame inventory remain in the child's `source`/`generation` fields. The child does not modify its parent.

For V-006 the parent is the existing V-004 S2-s1 SAMPLE. Native 33-frame RAW and both 73-frame CPU derivatives have separate output roles and hashes. Actual model inputs, masks, original reference usage, sigma grid, generation receipt and metric artifacts are recorded; unused references or controls are not represented as conditioning inputs.

Human acceptance is always initialized as `PENDING` with null form fields. Prior conversational verdicts are context, not supervised labels. `NOT_SUPPORTED`, `BLOCKED_*` and other stages without an actual output do not receive fabricated samples. Public Git contains only schema/code/non-sensitive summaries; all paths and media inventories stay private.
