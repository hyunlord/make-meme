# B-030 로컬 검토 뷰어 확인

기존 Chrome headless/CDP로 실제 compact staging의 HTML을 열었다. 신규 설치·영상 재인코딩은 없다.

- 두 과제 프레임 슬라이더의 0→1→16→15 이동, 처음/끝 버튼 상태, 연결 파일 존재를 확인했다. PAYLOAD_MANIFEST는 ZIP 봉인 시 생성되는 예약 파일이며 브라우저 검사 시 존재 검사에서 제외했다. 최종 ZIP 검사에서 실제 멤버/해시를 검증한다.
- 기존 대각4개와 신규 교차4개 MP4 모두 브라우저 metadata가896×512이고 오류가 없었다. 첫 영상 readyState4, duration0.708333초를 확인했다.
- 1280×900 / 768×1024 / 375×812 스크린샷과 두 과제 2×2 영상 배치 스크린샷을 실제 열어 확인했다. 작은 화면의 전체 프레임 스트립은 명시적 가로 스크롤을 사용하며 캔버스를 임의 crop하지 않는다.
- 별도 CPU ffprobe/프레임 decode에서 source2개+output8개가 모두17프레임·24/1임을 확인했다. 이는 preview 규약이며 source_fps=null/timebase_assumed=true를 바꾸지 않는다.
- 원본 MP4와 reference는 byte-exact 사본이다. 시트만 같은 full-canvas50% 파생물이다. compact에는 raw/latent가 없다.

**브라우저 기능 PASS와 시간적 영상 품질은 별개다.** 연속 영상 품질 시청은 수행하지 않았고 temporal=UNVERIFIED다. 자동·반복 재생을 사용하지 않았다. screenshot 관측은 정적 agent 검토이며 독립 인간 평가가 아니다. 대규모 웹 성능/접근성 감사는 이번 범위가 아니다.

검토 파일과 Chrome 로그/스크린샷은 비공개 검토 ZIP에 포함한다. 생성 모델과 무관한 이 뷰어 검사를 영상 품질 성공으로 합치지 않는다.
