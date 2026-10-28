# 실행 계보와 재현 범위

기존expected_absent코드의새attempt복사본에memory.py를추가하고safety.py의decide/lifecycle_decision이같은memory verdict를읽게했다. supervisor에는10초시작관측·공유S0원장·자체cgroup관측·OOM로그판정을연결했다. worker는기존bootstrap을그대로재사용하며preflight가시작swap상한도확인하고10초window만실제supervisor에위임한다. bootstrap.py/policy.py는기존과byte동일하다. prepare.py는기존layout준비방식의새root/config/freeze구성일뿐새launcher나관리자가아니다.

모델·방법·조건·noise·source/M/E·prompt·평가crop·B033clean_constraint는기존freeze로검증했다. actual input/code freeze와실제설정은비공개evidence에포함한다. weights/조건tensor자체는포장하지않는다.

양stageCPUpreflight는절대경로로성공했다. 실제supervisor호출은stage root를상대경로로주어실패했다. 이는완료된실험의재현명령이아니며같은attempt를재실행하는절차를제공하지않는다. 향후별도승인하의코드변경자는기존supervisor의절대root호출전제를확인해야한다. 실패한root·receipt·freeze를덮어쓰지말아야한다.

CPU만검사하는명령: `python -m unittest discover -s code -p 'test_*.py'`. 이명령은새GPU실행허가가아니다.
