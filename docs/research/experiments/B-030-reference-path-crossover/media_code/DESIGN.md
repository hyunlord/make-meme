# B-030 검토 자료

기존 어두운 연구 뷰어의 색·간격·명시적 재생 정책을 재사용한다. 행 VAE+semantic mask와 열 CLIP의 2×2 배치를 유지한다. SOURCE / Y11 / Y12 / Y21 / Y22 프레임 스트립은 17장 전체와 local0/8/16을 같은 full-canvas 50% 크기로 표시한다. 사진별 피사체 확대나 영상 재인코딩을 하지 않는다.

원본 MP4, source MP4, reference PNG는 byte-exact 사본이다. 시트만 MP4 복호화 후 JPEG/PNG 파생물이다. compact에는 중복 개별 프레임 PNG와 raw/latent를 넣지 않고 full에 신규 raw/latent 네 쌍을 보존한다. source의 원래 FPS는 미확인이며 preview24fps를 원래 시간축으로 주장하지 않는다. 플레이어 동시 시작은 편의 기능이고 정밀 동기화는 프레임 스트립으로 확인한다. 자동·반복 재생은 없으며 temporal UNVERIFIED를 표시한다.
