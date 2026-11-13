[English](validation.md) | **Korean**

# 검증 기록

이 파일은 도구를 어떻게 검증했는지 기록합니다. 테스트 클라우드에서의 live 점검, Claude
Code 프롬프트 점검, 로컬 단위 테스트가 포함됩니다. README의
[OpenStack CLI와 MCP 도구 매핑](../README.ko.md#-openstack-cli와-mcp-도구-매핑)의
Status 열은 이 결과를 명령별로 요약한 것이고, 이 파일에는 그 근거가 되는 날짜, 소스
리비전, 테스트 조건, 결과 수치를 남깁니다.

live 분류는 도구 단위(중복 없는 도구 수)로 세고, 단위 테스트 결과는 테스트 케이스
수로 셉니다. 부분 점검(partial)이나 대상 점검(targeted)은 명시한 경로만 다루며, 이전의
전체 요약을 갱신하지 않습니다.

## 검증 기록

- **Live 스냅샷 (2026-11-04, `a57b165` 기반 작업 트리):** 이 live 스냅샷은 현재 작업
  트리의 변경보다 앞선 것입니다. 이 live 분류는 과거의 근거로 남아 있으며, 이번
  변경에 대해 다시 실행하지 않았습니다.
- **Live 도구 점검:** 그 리비전에 등록된 도구 105/105개를 실행했습니다. 76개 도구는
  최소 한 개의 live 경로가 통과했습니다. 28개 도구는 테스트 클라우드에 Octavia, Aodh,
  Neutron QoS, floating IP port-forwarding API가 없어 사용할 수 없었습니다. 도구
  하나(`set_server_dump`)는 문서화된 플랫폼 제약에 도달했습니다. `set_snapshot` 상태
  수정은 전체 실행 후 따로 재검증했습니다. 실제 스냅샷이 `available`에 도달했고, 격리된
  테스트 프로젝트는 삭제했습니다. 이 수치는 개별 호출 수가 아니라 도구 단위 분류입니다.
- **Claude Code 프롬프트 점검:** 문서화된 예시 118/118개를 실제 MCP 서버에 요청했습니다.
  99개가 도구 작업을 완료했으며, 처음에 잘못된 자리표시자로 실패한 뒤 재시도로 성공한
  두 건을 포함합니다. 그 99개 중 두 건은 밝혀 둔 테스트용 대체 값을 써서 요청과 정확히
  같지는 않습니다. 복합 보고서 5개는 선택 API가 없어 부분 결과였고, 직접 요청 7개는
  해당 클라우드 서비스나 확장 기능이 없어 실행하지 못했으며, 조회성 요청 7개는 비대화형
  Claude 권한 정책 때문에 제한되었습니다.
- **후속 대상 점검:** `/mcp/.well-known/openid-configuration`은 인증 없이 404를
  반환했습니다. 실제 Nova action 목록은 목록에 완료 시각이 없다고 명시적으로 보고했고,
  선택적인 이벤트 상세 조회는 이벤트 결과를 반환해 마지막 완료 시각을 계산했습니다. 새로
  추가된 HTTP 전용 다중 사용자 테스트 예외는 **Live unverified**입니다. 안전하게 실패하는
  기본값, 명시적 opt-in, endpoint 생성, 시작 시 경고만 로컬에서 테스트했습니다.
- **텔레메트리 대상 점검 (2026-11-08 UTC, 부분 점검, `d954eba` 기반의 커밋되지 않은
  작업 트리):** 테스트 클라우드에 Ceilometer, Gnocchi, Aodh를 추가한 뒤
  `set_alarms`와 새 `get_gnocchi_*` 도구 4개만 MCP 서버로 다시 실행했습니다. 이 부분
  점검은 위의 105개 도구 live 요약을 갱신하지 않습니다. 다섯 도구 모두 최소 한 개의
  live 경로가 통과했습니다. metric UUID만으로 조회할 때의 metric 소유권 수정은 MCP
  서버를 다시 만든 뒤 live로 재검증했습니다. 테스트 클라우드의 ceilometer-compute
  agent가 시작 시 libvirt에 연결하지 못해 처음에는 polling metric이 없었고, 그 agent를
  재시작한 뒤 `cpu`, `memory.usage`, 디스크 I/O, 네트워크 I/O 측정값을 도구로 읽었습니다.
  Aodh는 `cpu` `rate:mean` 알람을 예상대로 `ok`와 `alarm` 상태로 평가했습니다. 테스트
  알람은 삭제했습니다.
- **집계 대상 점검 (2026-11-09 UTC, 부분 점검, `a5115d3` 기반의 커밋되지 않은 작업
  트리):** 새 `get_gnocchi_aggregates` 도구만 MCP 서버로 실행했습니다. 테스트 프로젝트에
  인스턴스가 하나뿐이어서 순위와 그룹화는 각각 시계열 하나를 반환했습니다. 그 실행 후
  null 구간 출력, metric 이름 검증, 실패 힌트를 바꿨고, 이 변경과 핵심 집계 경로를 현재
  작업 트리로 시작한 두 번째 streamable-HTTP MCP 서버로 다시 실행했습니다.
- **openstacksdk 사용 대상 점검 (2026-11-10 UTC, 부분 점검, PR #83을 병합하고
  openstacksdk 4.22.0을 고정한 커밋 `c2de34c`):** 그 병합으로 바뀐 경로만 실행했습니다.
  in-process MCP 클라이언트로, 변경 도구를 켜고, 관리자 계정으로, 고정된 의존성
  (openstacksdk 4.22.0, fastmcp 3.4.10)을 사용했습니다. 테스트 클라우드는 단일 노드
  배포(compute microversion 최대 2.100)로 Nova, Neutron, Cinder(백업 포함), Glance,
  Heat가 있었고 Octavia, Neutron QoS, port forwarding은 없었으며 compute 호스트는
  하나뿐이었습니다. 비동기 작업은 openstacksdk로 최종 상태까지 확인했습니다(상태당
  300초, 백업은 600초). 점검 73개 중 68개가 통과했고, 실패 5개는 테스트 스크립트에서
  비롯된 것이었습니다(출력 파싱, 문자열로 넘긴 metadata 인자, 잘못된 도구를 대상으로 한
  점검). 해당 경로를 재검증한 결과 lock/unlock 보고, metadata 설정, rebuild 후 metadata
  유지가 통과했습니다. `get_project_details`는 quota가 아니라 리소스 개수를 보고하므로,
  어떤 등록된 도구도 호출하지 않는 `get_project_info()`의 quota 필드 수정은 확인하지
  못하며 그 수정은 단위 테스트만 했습니다. 테스트 리소스는 모두 삭제했습니다. 이 부분
  점검은 위의 105개 도구 요약을 갱신하지 않습니다.
- **fastmcp 4 의존성 점검 (2026-11-10 UTC, 부분 점검, `aa668de` 기반의 커밋되지 않은
  작업 트리):** `uv.lock`을 fastmcp 4.1.6과 mcp 2.3.0으로 올렸고, `mcp-server` 이미지가
  이제 `uv.lock`의 패키지를 정확히 그대로 설치합니다. 위와 같은 대상 점검을 이 의존성으로
  in-process MCP 클라이언트를 통해 다시 실행했으며, 테스트 스크립트 오류 3개를 고치고
  `get_project_details` 점검은 뺐습니다. `get_gnocchi_service_info`와
  `get_gnocchi_metrics`도 조회했습니다. 점검 74/74개가 통과했고 테스트 리소스는 모두
  삭제했습니다. 로컬에서 빌드한 `mcp-server` 이미지가 Streamable HTTP로 도구 110개를
  제공했고, 위에 이름이 나온 Gnocchi 조회 도구 두 개와 `get_gnocchi_resources`를 포함한
  조회 도구 13개가 결과를 반환했습니다. 로컬에서 빌드한 `mcpo-proxy` 이미지(mcpo 0.0.20,
  mcp 1.30.0, FastAPI 0.128.0)가 그 서버에 연결해 도구 110개를 노출했고,
  `get_service_status`, `get_gnocchi_resources`, `get_volume_list`가 결과를
  반환했습니다. 두 이미지 모두 배포하지 않았습니다. 이 부분 점검은 위의 105개 도구
  요약을 갱신하지 않습니다.
- **볼륨 부팅 targeted check (2026-11-10, `set_instance` 볼륨 부팅 변경이 들어간
  `84c346d` 기반 작업 트리를 로컬에서 다시 빌드한 `mcp-server` 이미지로 제공):**
  `boot_from_volume`과 `volume_size=10`을 준 `set_instance` 생성 호출 한 번으로
  `private-net`에 서버 3대를 만들었습니다. `get_instance`는 세 대 모두 ACTIVE로
  보고했고, `get_server_volumes`는 각각 `/dev/vda`에 연결된 부팅 가능하고 in-use인
  `__DEFAULT__` 타입 10 GB 볼륨을 보고했습니다. 기존 볼륨으로 부팅(`boot_volume`)과
  서버 삭제 시 볼륨 삭제는 확인하지 않았습니다. 서버 3대는 사용자를 위해 실행 상태로
  두었습니다. 이 부분 점검은 위의 105개 도구 요약을 갱신하지 않습니다.
- **OpenStack 2026.1 live 점검 (2026-11-10 UTC, 일회용 OzarLand
  openstack-quick-lab 클라우드, Kolla-Ansible 22.2.0 all-in-one, compute
  microversion 최대 2.103, 관리자 계정):** 수정 도구를 켠 채
  `scripts/live_tool_check.py`를 openstacksdk 4.22.0과 4.9.0으로 in process 실행했고,
  PyPI 패키지를 서버로 써서 Streamable HTTP로도 실행했습니다. 최종 상태는
  openstacksdk로 폴링했으며 테스트 리소스는 남지 않았습니다.
  - **릴리스 3.7.3 (`aa668de`), Cinder가 없는 클라우드:** 수정 실행마다 호출
    238/242개와 최종 상태 점검 54/54개, 읽기 전용은 호출 72/76개였습니다. 57개 도구가
    통과했고, 5개는 Cinder 부분을 사용할 수 없다고 보고하며 통과했고, 40개는 없는
    서비스가 필요했고, 3개는 오류 경로만 실행했습니다. 실패 4건은 Gnocchi가 없는
    클라우드에서의 `get_gnocchi_*` 호출이었고, `get_gnocchi_measures`는 호출하지
    않았습니다(110개 중 109개). 호출한 Cinder 도구 13개는 약
    0.01초 만에 엔드포인트 URL 없이 "Block Storage (Cinder) service is not
    available"을 보고했습니다.
  - **릴리스 3.7.6 (`f528b03`), Cinder 추가 (LVM, NFS 백업):** 수정 실행마다 호출
    248/253개와 최종 상태 점검 59/59개였습니다(PyPI 설치는 fastmcp 4.1.7을 받음).
    74개 도구가 통과했고, 27개는 없는 서비스(Octavia, Aodh, Neutron QoS)가 필요했고,
    3개는 오류 경로만 실행했습니다. `set_volume_backups`는 partial이었고
    `get_gnocchi_*` 도구 4개는 실패했는데, 둘 다 다음 기록에서 고친 테스트 스크립트
    오류 때문이었으며, 다음 기록에서는 `get_gnocchi_measures`도 호출합니다(여기서는
    110개 중 109개 호출).
  - **3.7.6의 Cinder 및 볼륨 부팅 대상 점검** (openstacksdk 4.22.0과 4.9.0): 연결과
    분리, 연결된 볼륨의 전체 및 증분 백업, 새 볼륨과 원본 볼륨으로의 복원, 스냅샷,
    transfer, Cinder가 포함된 종합 보고서가 통과했습니다(호출 30/30개, 점검 24/24개).
    `volume_type`을 지정한 새 1 GB 루트 볼륨, 부팅 가능한 기존 볼륨, 한 번의 호출로
    만든 서버 2대의 `set_instance` 생성이 ACTIVE에 도달했습니다. `boot_source`는 요약
    모드와 상세 모드에서 모두 맞았고, 루트 볼륨은 서버와 함께 삭제되었으며
    `delete_on_termination=false`이면 유지되었습니다. 잘못된 옵션 조합 6개는 서버를
    만들지 않고 거부되었고(호출 19/19개, 점검 20/20개), 사용 중인 부팅 볼륨을 준 별도
    호출도 같은 방식으로 거부되었습니다.
  - **Gnocchi 오류 및 live 스크립트 수정 (`f528b03` 기반 작업 트리):** openstacksdk
    4.22.0과 4.9.0에서 호출 256/256개와 최종 상태 점검 61/61개였고, 110개 도구를 모두
    호출했습니다. 75개가 통과했고, 32개는 없는 서비스가 필요했으며(이제 "Metric
    service (Gnocchi) is not available"을 보고하는 `get_gnocchi_*` 도구 5개 포함),
    3개는 오류 경로만 실행했고, partial이나 실패는 없었습니다.
  - **멀티 유저 HTTP 모드 (PyPI 3.7.6 서버, HTTP 전용 테스트 override):** 프로젝트
    2개에 각각 관리자가 아닌 `member` 사용자와 Application Credential을 두었습니다.
    서버의 관리자 `OS_*` 변수가 설정된 상태에서도 없거나 틀리거나 짝이 맞지 않는
    자격 증명은 401을 반환했습니다(fallback 없음). OAuth discovery 경로와
    `/register`는 404를 반환했습니다. 각 사용자는 자기 프로젝트의 서버와 네트워크만
    보았고, 다른 프로젝트의 서버를 찾거나 중지하지 못했으며, 자기 서버는 중지하고
    시작했습니다. 두 사용자의 동시 요청 20개도 각자의 신원을 유지했습니다. 공유
    Bearer 인증에서는 토큰이 없거나 틀리면 401을 반환했습니다. 삭제한 자격 증명은
    다음 요청에서 거부되었고 다른 사용자는 계속 동작했습니다. 서버 로그에는 자격
    증명 secret이 나타나지 않았고 `INSECURE TEST MODE` 경고가 기록되었습니다(점검
    28/28개).
  - **Docker:** 게시된 이미지 `call518/mcp-server-openstack-ops:1.0.5`(`uv.lock`과
    같은 fastmcp 4.1.6, mcp 2.3.0, openstacksdk 4.22.0)에 `docker-compose.yml`처럼
    3.7.6 소스를 마운트했습니다. 다음 기록의 live 스크립트로 읽기 전용은 호출
    78/78개, 수정 도구를 켜면 호출 256/256개와 최종 상태 점검 61/61개였습니다. 테스트
    네트워크의 프록시가 Rocky Linux 미러를 막아 `Dockerfile.MCP-Server`는 다시
    빌드하지 못했습니다.

  이 점검은 Octavia, Aodh, Neutron QoS, port forwarding, 데이터가 있는 Gnocchi, 두
  번째 컴퓨트 호스트가 필요한 경로에 대해서는 부분 점검이며, 위의 105개 도구 요약을
  갱신하지 않습니다.
- **로컬 단위 테스트 (2026-11-10, Gnocchi 오류 및 live 스크립트 수정을 넣은
  `f528b03` 기반 작업 트리):** fastmcp 4.1.6과 openstacksdk 4.1.0, 4.9.0, 4.22.0에서
  479/479 (100%)이며, 실패나 건너뛴 테스트는 없습니다. 새 Gnocchi 회귀 테스트 3개는
  이전 코드에서 실패합니다.
- **로컬 단위 테스트 (2026-11-10, `prompt_template.md`의 깨진 제목 2곳을 고친
  `f528b03` 기반 작업 트리):** fastmcp
  4.1.6과 openstacksdk 4.1.0, 4.9.0, 4.22.0에서 `python -m pytest -q tests`로 실행해
  476/476 (100%)이며, 실패나 건너뛴 테스트는 없습니다. 이 테스트에는 `set_instance`
  생성의 루트 디스크 회귀 테스트(로컬 디스크, 이미지로 만드는 새 볼륨, 부팅 가능한 기존
  볼륨, 거부되는 옵션 조합), 인스턴스 `boot_source` 회귀 테스트,
  `services.core.get_service_status`의 identity 엔드포인트 fallback 회귀 테스트, MCP
  action 설명과 고급 파라미터 전달 회귀 테스트, 안전하지 않은 HTTP opt-in 회귀 테스트,
  Gnocchi 프로젝트 범위와 집계 입력 회귀 테스트, Claude Desktop 번들 manifest와 릴리스
  자산 점검, 실제 openstacksdk 리소스 객체로 만든 회귀 테스트, 모든
  `conn.<service>.<method>()` 호출과 키워드가 설치된 openstacksdk에 있는지 확인하는 정적
  검사가 포함됩니다. 이 테스트가 live 서비스 검증을 대신하지는 않습니다.
- **보안 그룹 규칙 로컬 테스트 (2026-11-11, `e522451` 기반의 커밋되지 않은 작업
  트리):** fastmcp 4.1.6과 고정된 openstacksdk 4.22.0에서
  `python -m pytest -q tests`로 실행해 492/492 (100%)이며, 실패나 건너뛴 테스트는
  없습니다. 새 보안 그룹 규칙 회귀 테스트 16건은 정확한 create/delete SDK 호출, 단일
  포트 정규화, 명시적인 CIDR 또는 프로젝트 소유 원격 그룹 선택, 프로토콜, 포트 범위와
  IPv4/IPv6 검증, 다른 프로젝트의 그룹이나 다른 보안 그룹에 속한 규칙의 거부를
  다룹니다. 기존 등록 테스트에서도 새 도구의 읽기 전용 쓰기 차단을 확인합니다. 실제
  OpenStack 규칙은 생성하거나 삭제하지 않았으므로 `set_security_group_rules`는 **Live
  unverified**로 유지합니다.
- **로컬 통합 테스트 (2026-11-11, PR #85를 `c8d4f51`에 커밋 없이 병합하고 live
  harness 통합 수정을 포함한 작업 트리):** fastmcp 4.1.6과 고정된 openstacksdk
  4.22.0에서 `python -m pytest -q tests`로 실행해 497/497 (100%)이며, 실패나 건너뛴
  테스트는 없습니다. 새 harness 회귀 테스트 2건은 Gnocchi, Aodh, Heat, Cinder와
  Cinder Backup의 선택형 서비스 routing을 검증합니다. harness는 이제 111번째 도구인
  `set_security_group_rules`를 호출하고 제한 CIDR 규칙의 생성과 삭제를 확인하지만, 이번
  통합에서는 해당 harness 경로를 실제 클라우드에서 실행하지 않았으므로 기존 live
  상태는 바뀌지 않습니다.
- **Octavia 대상 읽기 점검 (2026-11-12, 부분 점검, `05dfd12` 기반의 커밋되지 않은
  작업 트리):** Octavia GET 응답은 풀과 헬스 모니터의 관계를 `listeners`,
  `loadbalancers`, `healthmonitor_id`, `pools`로만 보고하며, 생성 전용인
  `listener_id`와 `pool_id`는 `None`이었습니다. 또한 Octavia는
  `GET /v2.0/lbaas/pools?listener_id=...`를 400으로 거부했고, 이 때문에
  `get_load_balancer_details`가 실패했습니다. 수정 후 실행 중인 `mcp-server`
  컨테이너(소스 마운트, openstacksdk Octavia proxy)에서 서비스 함수를 호출했습니다.
  대상은 리스너 1개, 멤버 2개인 풀 1개, TCP 헬스 모니터 1개로 구성된 HTTP
  로드밸런서 1개입니다. `get_load_balancer_details`, `get_load_balancer_pools`
  (전체 및 리스너별), `set_load_balancer_pool` (show),
  `get_load_balancer_health_monitors` (전체 및 풀별),
  `set_load_balancer_health_monitor` (show)가 모두 기대한 관계 정보를
  반환했습니다(읽기 호출 7/7). 호출은 MCP 전송 계층이 아닌 서비스 계층을 거쳤습니다.
  `mcp-server` 컨테이너를 재시작한 뒤에는
  `get_load_balancer_details`도 같은 로드밸런서에 대해 OpenWebUI와 MCP 서버를 거쳐
  성공했습니다. 리소스를 생성하거나 변경하지
  않았습니다. 이 부분 점검은 위의 105개 도구 요약을 갱신하지 않습니다.
- **로컬 로드밸런서 관계 필드 테스트 (2026-11-12, 같은 작업 트리):** fastmcp 4.1.6과
  고정된 openstacksdk 4.22.0에서 `uv run pytest -q`로 실행해 500/500 (100%)이며,
  실패나 건너뛴 테스트는 없습니다. 새 회귀 테스트 2건은 풀과 헬스 모니터를 Octavia
  GET 응답 형태로 구성하고, 기존 테스트는 풀 목록 조회에 `listener_id` 필터를 보내지
  않는지 확인합니다. 새 회귀 테스트 2건은 이전 코드에서 실패했습니다.
- **cross-project 조회 대상 점검 (2026-11-13 UTC, 부분 점검, `3882adc` 기반의 커밋되지
  않은 작업 트리):** issue #86의 `all_projects` 파라미터를 Kolla-Ansible 단일 노드
  OpenStack Epoxy 클라우드(compute microversion 최대 2.100)에서 openstacksdk 4.22.0,
  fastmcp 4.1.6으로 실행했습니다. 테스트 프로젝트에는 `member` 사용자 1명과 서버,
  1 GB 볼륨, 스냅샷이 있었고, 관리자 프로젝트에는 서버 2대와 볼륨 2개, `service`
  프로젝트에는 Octavia amphora 1대가 있었습니다. `get_instance_details`,
  `search_instances`, `get_instances_by_status`, `get_volume_list`,
  `get_volume_snapshots`, `get_project_details` 6개 도구를 고정 자격 증명 모드(프로세스
  안에서 도구 함수 호출, 관리자와 `member`, 스위치 on/off, 36회)와 다중 사용자
  모드(HTTP 전용 테스트 설정을 켠 로컬 Streamable HTTP 서버, 사용자별 Application
  Credential, 14회)에서 호출했습니다. 50회 호출 모두 기대한 결과를 반환했습니다.
  스위치가 꺼져 있으면 모든 `all_projects=true` 호출이 "Cross-project reads are
  disabled" 오류를 반환했습니다. 스위치를 켜면 관리자는 세 프로젝트의 서버, 두
  프로젝트의 볼륨, 다른 프로젝트의 스냅샷, 프로젝트 3개를 각 항목의 프로젝트 이름과
  함께 나열했습니다. `member`의 요청은 Nova와 Keystone이 거부(HTTP 403)했고 도구는 정책
  거부 오류를 반환했습니다. Cinder는 거부하지 않고 `member` 자신의 볼륨과 스냅샷만
  반환했으며, 이 결과에는 `scope.warning`이 붙었습니다. `all_projects`가 없는 호출은
  계속 현재 프로젝트만 다뤘습니다. 다중 사용자 서버 로그에는 자격 증명 secret이
  나타나지 않았습니다. 다루지 않은 범위: 방식 B(전용 Role + policy 재정의), 제한된
  Application Credential(방식 C), 이 클라우드의 정책 규칙 이름과 기본값. 테스트
  프로젝트, 사용자, Application Credential, 리소스는 추가 점검을 위해 남겨 두었습니다.
  이 부분 점검은 위의 105개 도구 요약을 갱신하지 않습니다.
- **로컬 cross-project 조회 테스트 (2026-11-13, 같은 작업 트리):** fastmcp 4.1.6과
  고정된 openstacksdk 4.22.0에서 `uv run pytest -q`로 실행해 523/523 (100%)이며,
  실패나 건너뛴 테스트는 없습니다. 새 테스트 23건은 스위치가 꺼져 있을 때(OpenStack에
  연결하지 않음), 정책 거부의 오류 처리, 좁혀진 결과의 경고, 프로젝트 이름을 못 얻을
  때 ID로 대체, 다른 프로젝트 서버의 부트 볼륨 이미지 확인, 프로젝트 요약, 목록과 이름
  조회의 현재 프로젝트 기본 동작을 다룹니다.
- **로컬 server instructions 테스트 (2026-11-13, `86ac7f6` 기반의 커밋되지 않은 작업
  트리):** fastmcp 4.1.6과 고정된 openstacksdk 4.22.0에서 `uv run pytest -q`로 실행해
  526/526 (100%)이며, 실패나 건너뛴 테스트는 없습니다. 이제 서버는
  `server_instructions.md`를 MCP server instructions로 보내고, `prompt_template_*`
  prompt 3개는 더 이상 등록하지 않습니다. 새 테스트 3건은 instructions가 4,096자
  이하인지, 그리고 기존(`initialize`) 프로토콜 모드와 현재(`server/discover`) 프로토콜
  모드의 in-process FastMCP 클라이언트가 instructions와 빈 prompt 목록을 받는지
  확인합니다. Claude Code, Claude Desktop, Open WebUI가 instructions를 모델에
  보여 주는지는 live로 확인하지 않았습니다.
- **cross-project 정책·방식 C 대상 점검 (2026-11-13 UTC, 부분 점검, 소스 `cb2ae87`,
  코드 변경 없음):** 같은 Kolla-Ansible 클라우드의 컨트롤러에서
  `oslopolicy-policy-generator`로 Nova, Cinder, Keystone의 기본 정책을 읽었고, 정책
  override는 없었습니다. 규칙은 [cross-project 조회](security.ko.md#cross-project-조회)에
  정리했습니다. 이어서 관리자의 Application Credential 두 개를 로컬 다중 사용자
  Streamable HTTP 서버(HTTP 전용 테스트 override, `ALLOW_CROSS_PROJECT_READ=true`,
  `ALLOW_MODIFY_OPERATIONS=true`)로 사용했습니다.
  - Role을 `reader`로 제한: `all_projects=true`로 호출한 `get_instance_details`,
    `search_instances`, `get_instances_by_status`, `get_project_details`는 정책 거부
    오류를 반환했고, `get_volume_list`와 `get_volume_snapshots`는 `scope.warning`과
    함께 현재 프로젝트만 반환했습니다. 프로젝트 범위의 `get_instance_details` 호출은
    성공했습니다. `set_volume` 생성 시험도 성공했는데, Cinder 2025.1의
    `enforce_new_defaults` 기본값이 `false`이기 때문입니다. 시험 볼륨은 삭제했습니다.
  - `admin` Role에 compute, identity, image, network, `volume`의 `GET`만 허용하는
    access rules: 인스턴스 도구 3개와 `get_project_details`는 세 프로젝트를
    조회했고, `set_keypair` 생성 시험은 HTTP 401로 거부되어 키페어가 만들어지지
    않았습니다. Cinder는 조회를 포함한 모든 요청을 HTTP 401로 거부했습니다.
    Kolla-Ansible이 Cinder의 `[keystone_authtoken] service_type`을 카탈로그에 없는
    `volume`으로 설정하기 때문입니다. 규칙 서비스를 `block-storage`로 만든 첫
    credential도 같은 이유로 실패해 교체했습니다.

  다루지 않은 것: 방식 B, 그리고 `service_type`을 바꾼 뒤의 Cinder 방식 C. 두
  credential은 추가 점검을 위해 남겨 두었습니다. 이 부분 점검은 위의 105개 도구
  요약을 갱신하지 않습니다.
