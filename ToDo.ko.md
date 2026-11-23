[English](ToDo.md) | **Korean**

# TODO

마지막 검토: 2026-11-15

이 문서는 아직 남은 작업만 관리합니다. 완료된 항목은 제거합니다.

## [Issue #86](https://github.com/call518/MCP-OpenStack-Ops/issues/86) cross-project 조회

cross-project 조회는 `ALLOW_CROSS_PROJECT_READ`로 켜는 16개 조회 도구에
구현되었고, 허용 여부는 OpenStack 정책이 판단하며, 방식 A, B, C를 라이브로
확인했습니다. [cross-project 조회 가이드](docs/cross-project-guide.ko.md)와
[검증 기록](docs/validation.ko.md)의 2026-11-13, 2026-11-14 항목을 참고하세요.

- [ ] **Octavia 관리 리소스 (미결정)**

`all_projects=true`이면 인스턴스 목록에 service 프로젝트의 Octavia amphora VM도
나옵니다. amphora와 그 포트, 보안 그룹은 운영자가 직접 다루지 않고 Octavia가
관리합니다. 표시할지 여부는 아직 정하지 않았습니다.

| 항목 | 내용 |
|---|---|
| 조회 | `all_projects` 인스턴스 목록에서 amphora를 표시할지 제외할지. 한 가지 안은 기본으로 제외하고, 제외한 개수를 알려 주고, 요청 시 포함하는 방식 |
| 변경 | 변경 도구가 여러 프로젝트를 지원할 때 amphora와 그 포트, 보안 그룹을 거부할지 |
| 판별 | 이름 접두사나 service 프로젝트 이름보다 Octavia API(amphora `compute_id`, VRRP·VIP 포트)를 우선. 테스트 클라우드에서 실제 값 확인 |
| 현재 상태 | 조회 도구는 `openstack server list --all-projects`처럼 amphora를 보여 줌. 변경 도구는 현재 프로젝트만 대상으로 하므로 service 프로젝트의 amphora에는 닿지 않음 |

## 단일 계정 모드의 Application Credential

- [ ] **단일 계정 모드에서 Application Credential 받기 (보류, 미결정)**

단일 계정 모드(MCPB, stdio, `--multi-user` 없는 HTTP)는 `OS_USERNAME`과
`OS_PASSWORD`만 받습니다. Application Credential은 다중 사용자 모드에서 요청
헤더로만 쓸 수 있습니다. `OS_APPLICATION_CREDENTIAL_ID`와
`OS_APPLICATION_CREDENTIAL_SECRET`을 추가해도 바뀌는 것은 Keystone 인증 단계뿐이고,
엔드포인트, 캐시, 도구는 그대로입니다. 사용자가 다른 계정으로 접속했다고 착각할
위험이 이점보다 클 수 있어 보류합니다. 결정된 것은 없습니다.

| 항목 | 내용 |
|---|---|
| 두 세트를 모두 설정 | 미결정: 시작 시 오류, 경고와 함께 Application Credential 우선, `OS_AUTH_TYPE`으로 선택 중 하나. 로컬 확인 결과 `auth_type`이 없으면 openstacksdk는 password 인증을 고르고 Application Credential을 경고 없이 무시함 |
| scope 변수 | 프로젝트는 credential이 정함. `OS_PROJECT_NAME`과 도메인 변수를 보내면 안 됨. 로컬 확인 결과 Application Credential 플러그인은 이를 scope 파라미터로 유지함. 이에 대한 Keystone 응답은 live 미검증 |
| 일부만 입력 | ID나 secret 중 하나만 있으면 password 인증으로 넘어가지 않고 실패해야 함 |
| 프로젝트 조회 | `get_current_project_id`의 `OS_PROJECT_NAME` fallback을 건너뛰고 토큰의 프로젝트 사용 |
| 제한된 credential | Role 일부나 access rules 때문에 일부 도구가 정책 거부(HTTP 403)를 반환할 수 있음. 매핑 Notes에 명시 |
| 만료 | 만료되거나 삭제된 credential을 명확히 보고. 재인증으로 복구되지 않음 |
| MCPB | `os_username`, `os_password`, `os_project_name`이 `required: true`이므로 optional로 바꾸고 조합 검증은 서버가 맡아야 함 |

## 다중 사용자 모드의 도구 동시 실행

- [ ] **도구 호출이 이벤트 루프를 막지 않게 하기 (보류)**

도구 121개 중 114개는 동기식 OpenStack SDK를 직접 호출하는 `async def` 함수라서,
도구 호출 하나가 실행되는 동안 서버의 이벤트 루프가 막힙니다. stdio와 단일 계정
HTTP에서는 도구 호출이 어차피 하나씩 실행되므로 달라지는 것이 없습니다. 다중 사용자
HTTP에서는 한 사용자의 느린 호출이 다른 모든 사용자를 기다리게 합니다. 성능 문제일
뿐이고 정상 동작 확인이 먼저이므로 보류합니다.

| 항목 | 내용 |
|---|---|
| 제안한 변경 | 114개 도구를 `def`로 선언. fastmcp 4.1.6은 `def` 도구를 스레드풀에서 실행하고 contextvars를 전달함. 같은 키의 호출을 도착 순서대로 하나씩 실행하는 middleware 하나 추가(`anyio.Lock`, FIFO). 키는 stdio와 단일 계정 HTTP에서 전역 하나, 다중 사용자 HTTP에서 `project_id` |
| 유지할 보장 | 지금은 모든 호출이 도착 순서대로, 앞 호출이 끝난 뒤 하나씩 실행됨. 잠금은 같은 프로젝트의 다른 사용자 호출까지 포함해 프로젝트 안에서 이 보장을 유지함. 모든 호출을 동시에 실행하는 안은 기각: 서로 이어지는 동기식 호출(network 다음 subnet)을 병렬로 보내면 실패할 수 있음 |
| 기대 효과 | 다중 사용자 HTTP: 서로 다른 프로젝트의 호출이 서로 기다리지 않음. stdio와 단일 계정 HTTP: 도구 호출 측면의 변화 없음 |
| 수정할 테스트 | 테스트 파일 6개에서 도구 함수를 `await`로 호출하는 21곳 |
| 릴리즈 조건 | Claude Desktop과 OpenWebUI에서 3.9.2와 새 빌드로 같은 요청(단순 로드밸런서, network → subnet → router → 보안 그룹 규칙 연쇄)을 실행하고, 다중 사용자 모드에서 프로젝트 두 개로 동시에 호출. 결과가 하나라도 3.9.2와 다르면 릴리즈하지 않음 |

## Neutron QoS 정책 공유

- [ ] **Neutron RBAC로 특정 프로젝트에만 QoS 정책 공유 (미구현)**

`set_network_qos_policies`는 정책을 모든 프로젝트에만 공유합니다(`shared=true`,
Glance의 public 이미지와 비슷). Glance 이미지 member처럼 고른 프로젝트에만 공유하려면
Neutron RBAC(`openstack network rbac create --type qos_policy --action access_as_shared
--target-project <project>`)가 필요하며, 이를 제공하는 도구는 없습니다.

| 항목 | 내용 |
|---|---|
| Action | 프로젝트 소유 정책에 대해 `qos_policy` 유형 RBAC 항목 생성, 조회, 삭제 |
| 범위 | 대상이 다른 프로젝트의 ID라서 변경 도구의 현재 프로젝트 범위를 넘음. 이를 어떻게 받고 검증할지 결정 필요 |
| 영향 | 정책의 규칙을 바꾸면 이를 쓰는 대상 프로젝트의 리소스에 즉시 적용됨. 대상 프로젝트가 정책을 쓰는 동안에는 Neutron이 항목 삭제를 거부함 |

## 서비스 상태 보고

- [ ] **서비스 목록 API가 없는 서비스의 상태 보고**
  - 2026-11-23부터 `get_service_status`는 Nova, Cinder, Heat engine 레코드와 Neutron
    agent를 읽고, Glance, Heat, Octavia, Barbican, Aodh, Gnocchi API는 probe만 합니다.
    Octavia(health manager, amphora 상태), Aodh(evaluator, notifier), Gnocchi(metricd)
    워커는 이 서비스들에 서비스 목록 API가 없어서 보고하지 않습니다.
  - `reader`는 오류 없이 빈 Neutron agent 목록을 받으므로, agent 섹션이 비어 있어도
    agent가 없다는 뜻은 아닙니다.

## Barbican과 TLS 리스너

- [ ] **프로젝트 `member` 계정으로 Barbican과 TLS 리스너 확인**
  - 2026-11-15와 2026-11-23에 admin 계정으로 라이브 확인: 모든 Barbican 도구,
    `sni_container_refs`와 리스너 `set`을 포함한 `TERMINATED_HTTPS`, `TLS-HELLO` 모니터를
    쓰는 non-terminated HTTPS, CA 검증·CRL·client authentication을 포함한 backend
    re-encryption([검증 기록](docs/validation.ko.md) 참고).
  - 아직 확인할 것: 프로젝트 `member`가 시크릿을 만드는 데 필요한 역할, `member`의 리스너
    생성 시 Octavia가 자체 ACL을 부여하는지.

## [Issue #73](https://github.com/call518/MCP-OpenStack-Ops/issues/73) 후속 작업

### 검증 후속 작업

#73을 닫을 때 확인되지 않은 것으로 남긴 항목입니다.

- [ ] **프로젝트 범위 자격 증명의 동시 격리**
  - 프로젝트 범위 Application Credential 두 개의 격리는 일회용 프로젝트 두 개로 랩에서만
    확인했고, 실제 배포 환경에서는 확인하지 않았습니다.
- [ ] **자격 증명 폐기 반영 시간**
  - 랩에서 한 번 확인했습니다. 삭제 후 다음 요청이 거부됐습니다. 반영 시간의 상한은
    측정하지 않았습니다.
- [ ] **OpenStack 서비스에 연결할 수 없을 때**
  - 보고되는 오류와, 서비스에 다시 연결되면 서버가 정상으로 돌아오는지 확인합니다.
- [ ] **종단 간 HTTPS**
  - MCP 구간은 HTTPS였지만, 테스트 클라우드의 OpenStack API는 임시 TLS 프록시 뒤의
    HTTP였습니다.
- [ ] **2026-10-28에 보고된 클러스터 상태 문제**
  - 권한 거부된 서비스 점검, availability zone 필드 처리, floating IP 풀 용량 계산.
    이후 코드가 바뀌었지만(2026-10-30, 2026-11-08) live 재확인은 하지 않았습니다.

### 선택적 후속 작업

- [ ] **OAuth 또는 브라우저 로그인**
  - 브라우저 기반 초기 설정이 필요할 때 수동 Application Credential 헤더 설정을 대신할
    인증 방식을 제공합니다.
  - 기존 Application Credential 방식에는 필수가 아닙니다.

- [ ] **Claude Desktop 원격 커넥터의 사용자별 헤더 검증**
  - 사용자별 `claude_desktop_config.json`의 `mcp-remote` 경로는 2026-11-14에
    확인했습니다. 남은 것: 원격 사용자 지정 커넥터가 조직 단위 커넥터를 통해 자격 증명을 공유하지 않고, 각 사용자의
    Application Credential 헤더를 보낼 수 있는지 확인합니다.
  - 자격 증명을 노출하지 않고 클라이언트 버전, 헤더 제한과 live 결과를 기록합니다.

