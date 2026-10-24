# B-023 결과: 정식 replacement 실행 PASS, 원본 보존 목표 FAIL

## 실제로 달라진 것

같은 실제 Lab 자연동작 f126..142에서 공식 replacement를 **한 번** 실행했다. B020 미학습 adapter-OFF animation의 흰 좌우 영역은 새 바닥·창가·가구로 채워졌지만, 원본의 타일·러그·장난감·촬영 구도는 보존되지 않았다. 중앙에는 참조의 세로 침실 영역과 착석 자세가 남았다. 후반 고개가 화면 왼쪽으로 변하는 방향은 원본과 대략 대응하지만, 얼굴 번짐과 중앙 세로 경계에서의 잘림이 남아 목표 품질 개선은 입증되지 않았다.

**TECHNICAL_EXECUTION=PASS / SOURCE_PRESERVING_TASK=FAIL / QUALITY_IMPROVEMENT=NOT_ESTABLISHED / temporal=UNVERIFIED.** 전체17장과 local0/8/16을 실제 정적 이미지로 검토했다. 영상 디코딩·브라우저 조작 확인은 연속 재생의 지각적 품질 검수가 아니다.

| 항목 | B020 미학습 OFF | B023 정식 replacement | 판정 |
|---|---|---|---|
| 전신 자세 | 침대에 착석 | 착석 유지, 원본의 사족 기립 아님 | FAIL |
| 고개 동작 | 후반 화면 왼쪽 변화 | local9..16에서 왼쪽 변화가 커짐 | 대략 방향 대응, 타이밍·관절 정확도 UNCERTAIN; 개선 미입증 |
| 얼굴·귀·주둥이·목 | 후반 번짐과 잘림 | 후반 매끈하게 뭉개진 표면·형태 변화와 잘림 지속 | FAIL |
| 장면·카메라 | 세로 침실과 좌우 흰 영역 | 중앙 침실 유지, 양옆에 원본과 다른 나무결 바닥·의자·창문 생성 | 원본 보존 FAIL |
| Framing | 참조의 좁은 세로 배치 | 같은 세로 구획, 머리 회전 시 그 왼쪽 경계에서 소실 | FAIL |
| 개체·체형 | 검은 Lab 외형 | 검은 Lab 견종 유사성은 있으나 실제 개체의 얼굴·가슴·사지 정밀 일치 불명확 | UNCERTAIN |
| 발·가림·반사 | 원본 접촉을 평가할 자세 아님 | 침대 위 앞발/하체, 원본 바닥 접촉 재현 아님 | 전신 목표 FAIL, 정확 접촉 UNCERTAIN |
| 시간 품질 | 기존 UNVERIFIED | 프레임 전체 정적 검토만 수행 | UNVERIFIED |

새 결과 오른쪽 상단에는 원본과 무관한 문자처럼 보이는 흔적도 있다. 모든 프레임을 보존했으며 선별·보간·warp·배경 재합성·얼굴복원·업스케일을 수행하지 않았다. 비교 이미지의 보기용 축소/표제 외에 생성 canvas는 변경하지 않았다.

## 입력과 실제 개입

원본 f126..142, PTS4.200000..4.733333, W896×H512·17프레임·30fps, 기존 aspect-fit/letterbox를 유지했다. 표본 간격은16/30초, 파일 지속시간은17/30초다. 기존 seated reference RGB와 support·caption·negative empty·initial noise·RNG·UniPC40/shift3/CFG5·seed20261022를 보존했다. 사용자 편집 의도와 실제 caption은 [EditSpec](EDIT_SPEC.json)에서 구분한다.

참조 마스크의 정확한 WHITE421543픽셀만 BLACK으로 바꾸고 RED37209픽셀을 그대로 유지했다. driving17장 RED/WHITE는 변하지 않았다. 사진 RGB를 검게 칠하거나 새로운 segmentation을 수행하지 않았다. 공식 helper의 이전 prefix를 CPU에서 exact 재현하고 파생 cache를 별도로 만들었다. 양 CFG의 ref_masks 두 leaf만 변경, 다른14leaf와 original device 구조·noise/RNG/scheduler는 exact 유지했다. replace_flag는 양 CFG 모두 True다.

실제 block0의 첫 두 forward에서 공식 replacement 위치 kwargs를 확인했다. ref H120뿐 아니라 generated/driving T0을 포함하는 공식 모드이며 B016 animation+H120 hybrid가 아니다. 모든40block Q/V는 vanilla projection, active LoRA0·ALG OFF·manual RoPE OFF·history/additional_ref None이다. pinned module hash와 실제 warning 파일 경로를 확인했으며 새 in-process 파일 해시 hook이 있었다고 주장하지 않는다.

주 기준선은 실제 B020 BASE_S/BASE_D의 미학습 adapter-OFF 출력이다. raw SHA256 `50579b6aa7739de4d4b65d959255d1ba71c980248ad7f52fd91e26ea0dc9d00e`를 확인했다. B02220/100 영상으로 대신하지 않았고 기준선을 재생성하지 않았다.

## 실행과 실패 기록

- 사전 코드·config 고정 및 원격 확인: `9bdae0b665beca1b78b07022626bc526770ff7b5`.
- CPU4계약 검사 PASS, compile PASS. ruff/basedpyright는 기존 환경에서 사용 불가여서 새 설치하지 않았다. 새 정적 타입 검사 NOT_RUN, 기존 NOT_CLEAN을 숨기지 않는다.
- CPU 준비 중 helper package import가 eager CUDA 접근으로 한 번 실패했다. GPU 없는 CPU 준비에서 발생했고 P/PROBE/S 시도는 아니었다. 같은 pinned helper 파일을 직접 import하는 최소 변경 후 사전 검증을 완료하고 이를 실행 전에 고정했다.
- P0, PROBE1, sampler1, decode1. 실제40step/80forward, finite final latent F32[16,5,64,112] 저장·readback 검증 후 S 종료, fresh D에서 finite raw F32[3,17,512,896]·17f30fps MP4 확보.
- 학습/target 인코딩/prefix 추출/새 설치·다운로드/외부 생성/재시도0. 모델·정밀도·attention·가드 변경0.
- 자체 unit 두 개 inactive/MainPID0. 기존 서비스는 유지했다. 종료 관측 MemAvailable89.29GiB·swap0.

자원·단계 시간과 서로 다른 메모리 회계는 [MEASUREMENTS](MEASUREMENTS.md), 실행 범위/명령은 [REPRODUCE](REPRODUCE.md), 공식 코드 의미는 [OFFICIAL_CONTRACT_AUDIT](OFFICIAL_CONTRACT_AUDIT.md), 독립 기술 검증은 [INDEPENDENT_REVIEW](INDEPENDENT_REVIEW.md)에 있다.

## 수용 범위와 다음 병목 하나

이는 mode와 semantic mask를 함께 맞춘 묶음 비교다. 단일 flag의 인과효과, 일반적인 replacement 성능, 참조 사용 자체를 식별하지 못한다. source/reference가 같은 Lab이므로 개선됐더라도 source-copy와 실제 identity-changing 편집을 구분할 수 없다. cross-ID·다중 객체·긴 영상·일반화·상용 품질은 NOT_RUN이다. B021 FAIL/B022 결과와 사전 B023 후보는 보존한다.

관측은 사용자 분기 C에 가깝다. 정식 replacement 적용만으로 착석·침실·잘림을 해결하지 못했다. 이번 검사에서 의도한 mode/mask/noise/adapter 실행 불일치는 발견하지 않았지만, 모든 전처리·조건 경로의 잠재 오류를 배제하거나 모델 한계로 확정하지는 않는다.

**다음 가설 하나:** reference의 세로 배치·침실 공간 정보가 객체 외형과 분리되지 않아 출력의 공간 구획까지 지배하는가? 다음에는 공식 replacement의 reference/driving 전처리·조건 주입에서 공간 배치가 연결되는 지점을 한정해 검증하는 연구를 제안한다. 입력 구현 오류와 모델의 참조 의존성을 구분할 수 있는 근거를 먼저 정한다. 이번에 추가 생성·offset/마스크 sweep·학습·ROI 합성은 실행하지 않았으며 다음 연구를 예약하지 않는다.

## 비공개 검토 자료

비공개 실행 폴더의 `review.html`, `reports/comparison-final/comparison-30fps.mp4`, `comparison-all17.png`, `comparison-local0-8-16.png`에서 같은 시간축의 SOURCE/OFF/REPLACEMENT와 원본 reference를 볼 수 있다. 전체17장 슬라이더와 반복 경계 표시를 제공한다. 공개 GitHub에는 개인 미디어·마스크·cache·latent·adapter·개인 절대 경로를 올리지 않는다. 단일 검토 ZIP에는 raw·MP4·전체 프레임·final latent·입력 계보·비교·재현·실패 기록을 넣고 weights/중복prefix는 제외한다. ZIP 전송/CRC/hash 실측은 별도 최종 전달 receipt로 남긴다.
