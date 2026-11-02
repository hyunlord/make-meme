# C-013 local review design
## 1. Identity
C-012 research viewer conventions: compact evidence, actual videos first, unambiguous provenance.
## 2. Color
--bg #f6f4ef, --fg #1d1d1b, --muted #59564e, --card #fff, --line #d9d4c8, --request #2a5ac8, --measured #c8462a. No decorative imagery.
## 3. Typography
system-ui sans-serif; body16, caption14, heading24 and card18 pixels. Korean word-break keep-all; overflow-wrap anywhere for identifiers.
## 4. Layout
4px base; gaps/padding16; maximum width1280; two columns down to700 then one. Images preserve416:240 aspect. Sheets and plots are marked derived.
## 5. Components
Reusable video card: label/provenance, original MP4 controls, frame-index image, target/measurement SVG, derived sheet link. Tab buttons for new paths/parent/seed2; native keyboard controls and labeled slider.
## 6. Interaction
No automatic playback or animation. Global frame slider updates exact PNG frame and pauses/seeks videos; play button starts visible videos together. Visible focus outline. Media failure prints error text.
## 7. Surface
Borders only, radius4; no shadows. Standard document headings and semantic main/nav/section.
