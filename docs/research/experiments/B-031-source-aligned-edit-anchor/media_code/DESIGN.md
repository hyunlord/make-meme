# B-031 검토 뷰어

## 목적
기존 연구 뷰어를 재사용해 SOURCE → TARGET → B027 → A0 → R_star → 새 영상을 단계별로 읽는다. 모든6앵커의 성공·실패·미실행을 표시한다. 영상은 사전R1만 선택되며R2대체없음, temporalUNVERIFIED다.

## 토큰
배경#10151e, 패널#1b2431, 선#40516b, 본문#edf3fa, 보조#c1cddd, 링크#8cceff. 기본간격4px,8px,12px,16px,24px. system-ui16px/1.55; h1 28px(모바일24),h2 23px,h3 18px. 모서리4px, 그림자없음.

## 구성
동물/사람/차량 section3개. 동일task R1/R2 각각입력crop과rawA0를나란히표시한다. 없음은상태문자이며가짜이미지없음. source와A0는같은fullcanvas비율, targetcrop만고유aspect표시. baselineR1/R2와새R1영상은원본MP4를직접재생한다.

## 상호작용
자동/반복재생없음. 동일task영상시작/정지버튼,17프레임슬라이더와이전/다음으로정적시트를확인한다. 실제속도preview24fps/원본FPS미확인을명시. 재생가능검사는시간품질검수와별개다.

## 재사용 요소
figure+figcaption,media panel,controls,missing status를반복한다. 명시적width/height와object-fit:contain으로crop을숨기지않는다. keyboardfocus3px링크색. 좁은화면단일열,정적비교시트만가로스크롤.

## 전달 정책
compact는입력·6앵커/실패·기준선6MP4·실제새영상·단일전체17시트·보고서/재현. 중복framePNG/raw/latent없음. full에실제새raw/latent추가. MP4재인코딩0. nofakequalitystatus.

## 검증
기존Chrome/CDP로375/768/1280 screenshot,link/media metadata,framecontrols,empty/failure rendering을확인한다. 이검사는generated영상의연속시청품질판정이아니다.
