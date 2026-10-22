# B-007B 재현과 보존 경계

실제 모델 결과는 없다. 다음 명령은 공개 코드와 사용 권한이 있는 비공개 입력·고정 가중치를 갖춘 격리 환경을 전제로 한다. 개인 경로는 `${RUN_ROOT}`로 대체한다. 기존 A/VACE 환경에 설치하지 않는다.

1. [download_manifest.json](download_manifest.json)의 revision·파일 길이·SHA를 확인한다. 이번에 확보한 파일을 재사용하며 다시 다운로드할 필요가 없다.
2. 실제 차단은 다음 CPU metadata 검사로 재현된다. 오류를 성공으로 바꾸려고 allowlist나 unsafe loader를 켜지 않는다.

```sh
CUDA_VISIBLE_DEVICES='' timeout 120 python code/converter_metadata.py \
  "$RUN_ROOT/models/model/1/fsdp2_rank_0000_checkpoint.pt" \
  "$RUN_ROOT/source-original/convert.py" \
  "$RUN_ROOT/reports/new-metadata-check.json"
```

예상 결과는 NumPy globals3개의 `ConversionError`, exit1이다. 검사가 거부되므로 결과 JSON은 만들어지지 않을 수 있으며 stderr와 exit code를 보존해야 한다. 실제 B-007B는 위 검사를 추가로 systemd cgroup·메모리·시간 guard 아래 실행했다.

3. 합성 변환 비교는 아래와 같다. 실제 큰 checkpoint 성공을 대신하지 않는다.

```sh
SCAIL_CONVERT_SOURCE="$RUN_ROOT/source-original/convert.py" \
  CUDA_VISIBLE_DEVICES='' timeout 120 python -m pytest code/test_conversion.py -q
```

4. `runtime_infer.py`와 두 config는 실행 전 고정했지만 **NOT_RUN**이다. 변환·전체 모델 header 계약이 통과하기 전 호출하지 않는다. reader는 FFmpeg RGB24이며 공식 resize/정규화와 `pipeline.generate/cache_video`를 쓴다. 전체 upstream CLI의 무변경 실행은 아니다. noise/scheduler/tensor 관측 hook의 복사·기록 시간도 실행 시간에 포함된다.
5. `runtime_guard.py`는 이 실험의 고정 종료시각을 가진 역사적 실행 코드다. 만료된 deadline을 자동 연장하지 않는다. 새 실행 범위와 시간·시도 예산을 별도로 고정해야 한다. inference 장부가 없는 이번 결과는0/2이며 두 개의 실패 추론으로 잘못 집계하지 않는다.

비공개 ZIP에는 입력·writer 검증·실패 로그·opcode 문맥·환경/자원/보존 증거와 공개 코드를 넣는다. 대형 weights, 환경, 전체 원본 source checkout은 제외하고 제외 자료의 경로·크기·해시 또는 명시적 범위를 기록한다. 개인 미디어는 GitHub에 업로드하지 않는다.
