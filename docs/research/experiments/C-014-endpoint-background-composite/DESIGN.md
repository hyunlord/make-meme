# C-014 review design

## Purpose
Offline scientific comparison, actual RAW and CPU POST videos first. No product styling or claim that the generator improved.

## Tokens
Reuse C-013: background #f6f4ef; text #1d1d1b; muted #59564e; white panels; border #d9d4c8; focus/link #2a5ac8; warning #a52f1a. Font system-ui 16px/1.5; note14px; heading24px/18px. Spacing8/16/24px, border1px, radius4px. Main max1280px.

## Components
Three native tab buttons, two-column RAW/POST video and lossless PNG comparison; shared33-frame slider; alpha overlay checkbox; common play/pause. Inputs/plate/source panel is subordinate. Same-scale112px crops and all33/9frame sheets are explicitly derived.

## Layout
Two columns above700px, one below. No clipped text or horizontal scrolling. Images keep their native aspect ratio. Source panels wrap responsively.

## Semantics and state
Visible labels, keyboard focus, tab selected state, media failure message. Native media controls retain individual playback. Shared slider pauses videos and selects PNG index exactly; video seeks are preview only.

## Provenance
RAW original copied bytes; POST CPU composite. Radius28/44/52 rings are QA overlays, not segmentation. PNG exact claims do not apply to lossy MP4. temporal=UNVERIFIED.

## Verification
Parent performs real browser375/768/1280px, tabs, slider, alpha toggle and media playback after guarded build. No new dependencies or Lighthouse installation under the explicit work order.
