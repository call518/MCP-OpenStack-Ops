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

## 서비스 상태 보고

- [ ] **`get_service_status`가 실제 서비스 상태를 보고하도록 개선**
  - Glance와 Heat 행은 서비스 레코드가 아닙니다. 목록 조회 성공 여부로 만든 행이라
    `host`가 `unknown`이고 `updated_at`은 서버의 로컬 시각입니다. Nova, Neutron,
    Cinder 행은 UTC heartbeat를 씁니다.
  - heat-engine, Octavia, Aodh는 보고하지 않습니다. 2026-11-14 랩 장애에서
    heat-engine이 데이터베이스 연결을 잃었는데도 `heat-api`는 up으로 보고됐습니다.
  - `running_services`가 조회 결과로 만든 행도 실행 중으로 셉니다.

## Barbican과 TLS 리스너

- [ ] **Barbican 도구와 `TERMINATED_HTTPS` 리스너 라이브 검증**
  - 2026-11-15 라이브 확인(admin 계정): `set_secret` `create_self_signed_tls`, 그리고
    `default_tls_container_ref`를 이름으로 지정해 만든 `TERMINATED_HTTPS` 리스너가
    `ACTIVE`/`ONLINE`이 되고 HTTPS를 제공함(`curl -vk`: TLSv1.3, 두 멤버 모두 HTTP 200).
  - 아직 단위 테스트만 수행한 것: 나머지 Barbican 도구와 액션, `sni_container_refs`,
    TLS 참조를 쓰는 리스너 `set`, pool의 backend re-encryption 파라미터(Octavia API로
    직접 보내는 client authentication용 `tls_container_ref` 포함).
  - Non-terminated HTTPS(`HTTPS` 리스너와 pool, `TLS-HELLO` 모니터)와, CA로 멤버를
    검증하는 backend re-encryption을 client authentication이 있을 때와 없을 때 모두
    확인합니다.
  - Barbican이 있는 클라우드에서 확인할 것: 프로젝트 `member`가 시크릿을 만들 때
    필요한 역할, 리스너 생성 시 Octavia가 ACL을 직접 부여하는지(2026-11-15 점검은 admin
    계정으로 수행).

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

