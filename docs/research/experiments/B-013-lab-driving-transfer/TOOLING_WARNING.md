# codegraph 경고의 범위

B-012 뒤 보고된 `unsupported plugin entry type`의 `node_modules/.bin/codegraph` 항목은 **TOOLING_WARNING**으로 분리한다. 실제 entry 유형·검사 규칙·hook 시점·정확한 원인은 현재 UNKNOWN이다. 지정된 원본 로그/manifest 경로가 확인되지 않아 전체 개인 폴더를 검색하지 않았다.

B-012 원격 완료 기록과 실제 양 case P/PROBE/S/D 종료·출력·전달 receipt는 이 경고와 별개다. B-013 시작 시 문서 fetch, 파일 읽기/복사, CPU 검사와 기록 push는 진행 가능했다. 경고만으로 완료된 sampler를 재실행하지 않는다.

플러그인 삭제, hook 일괄 비활성화, symlink-follow 우회, GPU/드라이버 재설치, 보안 설정 변경은 수행하지 않았다. 이번 실행을 실제 차단하는 오류가 관측되면 모델 실패와 구분해 정확한 단계/오류를 기록하며 생성 예산을 우회하지 않는다.

종료 시 B-013 양쪽 P/PROBE/S/D8개 worker가 모두 정상 종료하고 MP4·최종 latent를 확보했다. 이 경고를 B-013 생성 실패나 결과 무효로 해석하지 않는다. 경고의 정확한 원인 UNKNOWN은 별도로 남기며, 새 codegraph 설치·업그레이드도 이번 실험에 포함하지 않았다.
