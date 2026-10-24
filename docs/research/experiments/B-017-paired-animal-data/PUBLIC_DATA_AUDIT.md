# B017 — 공개 후보 접근·권한·pair 적합성

조사 범위는 공식 README/논문/라이선스와 소형 소스뿐이다. **코퍼스 다운로드0, 신청서 제출0, 동의/가입0, 생성0, 학습0**. 공개 링크의 존재와 실제 접근 허가·수령을 구분한다. 이 문서는 법률 판단이 아니라 확인된 문서와 미확인 범위의 기록이다.

## 후보별 근거

| 후보 | 공식 확인 내용 | 접근·권리 상태 | 이번 목적의 한계 |
|---|---|---|---|
| MotionPair | SCAIL 학습 데이터의 큰 subset을 요청 양식과 terms 동의로 제공한다고 명시 | README 확인, 양식은 현재 web 도구로 열리지 않음. 신청/승인/terms 동의 없음. 세부 training/상업/재배포 권리 UNKNOWN | 공개 animal pair 비중·clip별 identity/motion metadata·현재 허가 범위 미확인. 학습-ready 아님 |
| APT-36K | 2400clip, clip당15선택frame, 30종, pose/tracking 주석. YouTube 기반 수집 및 clip별 수동 sampling rate | 공식 README에 project MIT 문구·OneDrive 링크. 파일 수령/링크 payload 접근은 미검증. 제3자 원영상의 별도 training/재배포/상업권리 UNKNOWN | sparse15장은 연속17f24fps 아님. track ID가 clip 밖 생물학적 개체 동일성이나 cross-ID motion-pair를 보장하지 않음 |
| APTv2 | 2749clip×15frame=41235frame, 84611 animal instances; APT 확장 pose/tracking benchmark | 공식 data 링크와 repository Apache2 LICENSE 확인. 코퍼스별 권리·원영상 권리 범위는 별도 미확인 | annotation/instance 증가가 동작 정렬된 다른 개체 target을 추가했다는 뜻 아님 |
| 기존 소유/승인 자료 | private inventory에서 별도 확인 | 사용자 제공 사실과 학습·공개 재배포 허가를 분리 | Lab 사진만 있으면 Lab target motion video는 아직 없음 |

## 고정한 공식 원문

- SCAIL Wan commit `78fe19576bb06be96c2375e088574a262a300edb`: [MotionPair 접근 문구 L490–492](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/README.md#L490-L492), [프로젝트 라이선스](https://github.com/zai-org/SCAIL-2/blob/78fe19576bb06be96c2375e088574a262a300edb/LICENSE). 코드의 Apache2를 데이터 terms나 기초 영상 권리로 대체하지 않는다. 모델 가중치 라이선스 또한 dataset grant와 별개이며 이번에는 새 weight/model card 감사를 반복하지 않았다.
- APT-36K commit `366ba0109bb9586cac793d1b150d5f4261b77cfa`: [공식 정의·sampling L19–22](https://github.com/pandorgan/APT-36K/blob/366ba0109bb9586cac793d1b150d5f4261b77cfa/README.md#L19-L22), [MIT project statement L57](https://github.com/pandorgan/APT-36K/blob/366ba0109bb9586cac793d1b150d5f4261b77cfa/README.md#L57). README의 dataset 배포 문구는 확인했지만 모든 원저작자 권리 정리가 확인됐다고 확대하지 않는다.
- APTv2 commit `77076adde3b4678e6f2cd2758d9cb69684cf6cef`: [규모 L1–7](https://github.com/ViTAE-Transformer/APTv2/blob/77076adde3b4678e6f2cd2758d9cb69684cf6cef/README.md#L1-L7), [data 링크 L71–72](https://github.com/ViTAE-Transformer/APTv2/blob/77076adde3b4678e6f2cd2758d9cb69684cf6cef/README.md#L71-L72), [repository LICENSE](https://github.com/ViTAE-Transformer/APTv2/blob/77076adde3b4678e6f2cd2758d9cb69684cf6cef/LICENSE). 해당 파일은 Open-MMLab 저작권으로 시작하는 Apache2 소프트웨어 라이선스이며 dataset 모든 영상의 blanket permission이라고 쓰지 않는다.

실제 조회 revision과 내려받은 작은 README/LICENSE의 SHA는 private `source_manifest.json`에 기록했다. corpus와 모델은 내려받지 않았다.

## Reverse driving은 기존 방법이며 조건이 있다

[SCAIL-2 §3.2](https://arxiv.org/html/2606.10804v1#S3.SS2)는 생성된 다른 개체 영상을 driving으로 쓰고 원래 영상을 target으로 사용하는 reverse-driving을 제시한다. 따라서 이를 새로운 독창적 학습 아이디어라고 주장하지 않는다. 합성 driving이 motion을 잃으면 원본과 정렬된 pair가 아니므로 채택할 수 없다. 외부 생성 API를 포함한 원논문의 pipeline을 B 트랙에 자동 도입하지 않는다.

현재 공개 후보의 **학습 사용 가능성은 RIGHTS_PENDING**, **실제 cross-ID pair 확보는 NOT_ESTABLISHED**다. pose 주석은 평가/모션 표현 연구에 유용할 수 있지만 R과 Y가 목표 개체이고 D만 다른 개체라는 정답 관계를 자동 만들어 주지 않는다. source/target의 영상 계보·event timing·권한을 확인하기 전까지 training-ready로 올리지 않는다.

## Local-only 대안의 가능성과 비용 — 설계만

| 대안 | 가능한 관계 | 추가 비용·실패 조건 | 이번 상태 |
|---|---|---|---|
| local reverse driving | 허가된 원본Y에서 다른외형D를 생성하고 원본을target으로유지 | 후보pair마다 최소1번전체영상생성과event정합QA가필요하다. 기존17frame14B실행도수십초가아닌분단위였으며 실제pair수율은UNKNOWN; 기존Lab동작실패를유효pair로취급할수없다. D생성모델오류·원본권한·합성분포편향이남는다 | NOT_RUN |
| 허가된rig/asset의동일event render | 두체형에동일motion을retarget해D/Y관계를통제 | rig/asset라이선스·동물관절/발접촉수정·렌더·도메인차이검증비용. 같은event로render했다고실제Labidentitytarget이되는것은아니다 | NOT_RUN |

현재다음한경로는두합성대안이아닌권한있는실제Lab자연동작촬영자료확보다. 새합성/렌더/모델설치는실행하지않았고, 학습메모리는추론실측으로대신하지않는다.
