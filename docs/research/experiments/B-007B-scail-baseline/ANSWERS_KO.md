# B-007B 해설

1. 아니다. q/k 순서나 transpose가 틀려도 shape가 같을 수 있다. dtype는 표현 정밀도, 값과 byte hash는 실제 배열 내용, key는 들어갈 module을 확인한다. 서로 다른 safetensors header 순서 때문에 파일 전체 hash는 달라도 각 tensor 의미가 같을 수 있다.
2. 아니다. mmap resident pages·output dirty cache·runtime·metadata가 추가된다.8MiB는 한 write slice의 상한이다. 변환은 원본 저장 dtype 보존이고 runtime은 실제 연산 parameter를 BF16/FP32로 배치하는 별도 수치 변경이다. meta construction도 최종 resident와 activation을 없애지는 않는다.
3. σ=1−t이면 dσ=−dt라서 target 부호가 뒤집힌다. 코드의 v=ε−x와 음수 Δσ는 data 방향을 만든다.40 step×2 prediction은80 DiT 평가 예상이며 영상 frame 수와 무관하다. 실제 중단·segment·guidance 조건까지 trace로 확인해야 한다.
