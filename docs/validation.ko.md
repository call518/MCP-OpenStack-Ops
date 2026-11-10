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
