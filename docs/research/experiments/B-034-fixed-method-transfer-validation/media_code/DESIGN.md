# B-032 검토 뷰어

기존 B031의 로컬 HTML 검토 도구를 축소 재사용한다. 목적은 SOURCE / B031 RAW / FIXED_ENVELOPE / MASK_ASSISTED의 같은17프레임 비교이며 제품 UI나 사람 평가 도구를 새로 만들지 않는다.

## 디자인 토큰
배경#10151e,패널#1b2431,선#40516b,본문#edf3fa,보조#c1cddd,링크#8cceff,미디어배경#080b10. system-ui16px/1.6,제목28px/모바일24px,소제목23px. 간격4/8/12/16/24/32/48px,모서리4px,그림자없음. 반복 figure/card/controls/details와명시적7:4미디어비율을사용한다.

## 구성과 동작
네 조건 MP4를 직접 열고 같은local frame으로 seek한다. 자동·반복재생없음. 전체17장,0/8/16의동일고정crop확대,edit support 시각화를 별도링크로제공한다. 정적 PNG/JPEG시트는FFmpeg/기존raw의RGB시각화이며품질점수가아니다.

## 의미와 전달
기존SOURCE/B031 MP4의bytes는그대로복사한다. 새합성두개는새파생물로인코딩했다. Source의기존gbrp영상이브라우저에서오색상으로보일수있어정적시트를대안으로제공한다. temporalUNVERIFIED. 큰raw/latent/weights는ZIP에없다.

## 검증
375/768/1280실제Chrome layout와링크·4영상metadata·seek·focus·overflow를확인한다. 새서버·패키지·GPU worker를실행하지않는다. Lighthouse 설치/성능캠페인은사용자의90분CPU검토범위가아니며실행하지않는다.

## B034 reuse contract
Reuse B033 colors, spacing, media cards and controls without redesign. Two fixed cases: rigid_R1 and nonrigid_R1. Each preserves actual source/reference/anchor images and shows anchor suitability separately from video status. Uncreated outputs remain NOT_RUN text, never placeholder imagery.
Each eligible case compares SOURCE, BASE/FINAL/STEP raw and identical-support post results; SOURCE_RECON is a reconstruction control. All17 and local0/8/16 detail crops use the case-specific window frozen before STEP. No inherited vehicle crop silently applied to a new scene.
Preview24fps with unknown original FPS; no loop/autoplay. Per-case synchronized play/pause and single-frame stepping. Browser playback checks do not establish human temporal review. Keep source GBRP Chrome warning and correct RGB sheets.
