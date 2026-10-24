# B-022 실제 실행 자원

아래 wall은각supervisor기록이다. 각단계는freshworker로순차실행했고종료·자원회복후다음으로이동했다. 메모리단위는GiB(2^30bytes),값은서로다른회계라합산하지않는다.

| 단계 |wall s|min MemAvailable|peak RSS|peak RssAnon|peak RssFile|cgroup peak|CUDA peak allocated|CUDA reserved max|
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|TRAIN|107.220|80.644|4.729|2.755|2.981|4.946|4.521|5.842|
|PROBE|6.080|88.794|1.002|0.511|0.448|0.678|0.017|0.027|
|STEP20_S|1137.253|52.122|62.144|31.541|41.161|62.004|33.832|33.895|
|STEP20_D|14.211|75.340|1.814|1.399|0.369|2.122|8.908|11.562|
|STEP100_S|1124.265|52.560|71.403|31.623|43.760|62.006|33.832|33.895|
|STEP100_D|16.223|76.305|1.829|1.399|0.384|2.165|8.908|11.562|

모든 단계의 peak가 동시에 발생한 것은 아니다. 각 단계·회계의 실측을 별도로 보존한다.

전단계swap0, guard reason=`service_exit`, returncode0, terminalMainPID0/inactive와resultCOMPLETED를확인했다. cgroup high reclaim event는별도원시자료에보존하며OOM과동일시하지않는다. RSS/RssAnon/RssFile 최대값도같은시점이라는보장이없다. 파일mmap·sharedstorage·CUDA를중복합산해통합메모리사용량이라고보고하지않는다.

TRAIN의allocator peak4,854,839,808bytes는한tail+head의값이며전체40block학습가능성을보증하지않는다. TRAINcap16GiB와기존72GiB시작/24GiB실행headroom/swap0를유지했다. 기존환경·가중치·다른서비스는변경하지않았다.

실제TRAIN33비학습forward·3진단backward·80추가update. 두fullsampler는각40step80forward. 최종latent2개와raw/MP4를각각보존했다. 상세모든sample/phase기록과단계별cgroup event는비공개ZIP에있다.

최종 event 검토: STEP20_S `high=3533`, STEP100_S `high=2553`; 두경우 `max=oom=oom_kill=0`이다. high이벤트를삭제하거나OOM이라고단정하지않는다.
