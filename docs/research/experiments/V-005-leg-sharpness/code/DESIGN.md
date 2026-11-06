# Offline research review design

## 1. Purpose
Actual video comparison and frame inspection; no quality ranking or visual decoration. Reuse the V004 plain offline DOM surface.
## 2. Tokens
White background #fff; text #171717; muted #555; border #ddd; empty #f4f4f4; focus/link #005ea8; error #a00000. Space unit8px; body16px; caption14px; heading24px; video column256px. Charts use distinguishable categorical colors, not quality scores.
## 3. Typography
System sans-serif, Korean keep-all with long provenance labels allowed to wrap anywhere. Labels remain readable at375px.
## 4. Layout
Controls wrap. The requested ten comparison columns scroll horizontally inside their container. Actual media comes before metric tables. No page-wide overflow. Equal column display sizes.
## 5. Components
Shared buttons/selects/range; actual video pairs; empty technical-state cells; anchor cards; SVG per-frame plots with labelled axes and legend; reference-only metric table. RAW lower-body zoom uses decoded video canvas and real per-frame Lab boxes, never synthesized images.
## 6. Interaction
One clock controls play/pause/seek/rate/window loop. RAW/POST/BOTH explicitly labels derivatives. Zoom only affects RAW display and cannot modify media bytes. All numerical scene choices come from scene config or measured runtime data.
## 7. Verification
Real-browser actual media at375/768/1280; playback, rates, seek, loop, RAW/POST, RAW zoom and missing boxes; screenshots and errors retained. Browser QA is not continuous perceptual quality acceptance.
