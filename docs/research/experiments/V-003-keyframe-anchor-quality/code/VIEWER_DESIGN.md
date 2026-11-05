# Offline research viewer

## Intent
Actual media first, equal display size, no automatic quality ranking. Original/generated/derived roles remain visible.
## Tokens
System sans-serif; body 16px, captions14px, heading24px. White background, #171717 text, #555 muted text, #ddd border, #f4f4f4 missing media, #005ea8 focus. Spacing4/8/16/24px. Border-only separation; no shadow or ornament.
## Layout
Horizontal scroll comparison row with minimum256px columns; every video16:9, object-fit contain. Same dimensions for all columns. Controls wrap on narrow screens.
## Components
Media figure (caption/video/state), anchor figure, button, labeled input/select, table, document link. Data determines columns and anchors.
## Interaction
Single play/pause/frame/rate control; RAW/POST switches only generated columns with a supplied derivative. Missing derivatives explicitly shown, never substituted silently. Timeline markers jump to source-relative keyframes and show matching anchor.
## Accessibility
Native controls, visible focus, Korean word-break keep-all, semantic headings and tables. No animation, external fonts or network dependencies.
## Verification
Real browser screenshots375/768/1280px, play/pause/frame/rate/toggle/anchor controls, empty states, document links. Temporal video quality is not inferred from playback QA.

Final packages with POST default to BOTH: RAW and POST appear side by side within each generated column with aligned labels. RAW-only and POST-only remain available. All visible videos share the same timeline; hidden roles are paused. Intermediate packages remain immutable.
