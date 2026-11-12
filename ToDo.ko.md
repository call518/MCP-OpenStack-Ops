[English](ToDo.md) | **Korean**

# TODO

마지막 검토: 2026-11-12

이 문서는 아직 남은 작업만 관리합니다. 완료된 항목은 제거합니다.

## [Issue #86](https://github.com/call518/MCP-OpenStack-Ops/issues/86) cross-project 조회

이 항목은 [Issue #73](https://github.com/call518/MCP-OpenStack-Ops/issues/73)의 필수 후속
작업도 함께 완료합니다.

- [ ] **충분한 권한을 가진 자격 증명으로 여러 프로젝트 조회**

**설계**

| 항목 | 결정 |
|---|---|
| 권한 기준 | 대상 OpenStack 서비스의 정책이 자격 증명 토큰에 전체 프로젝트 목록 API를 허용할 때만 가능합니다. MCP 서버는 Role이나 Group을 정의·저장·검사하지 않습니다. |
| 기능 스위치 | `ALLOW_CROSS_PROJECT_READ`(기본값 `false`)를 추가합니다. 이 서버에서 기능을 켤 뿐 권한을 부여하지 않습니다. |
| 도구 인터페이스 | 새 도구 없이 기존 목록 도구에 `all_projects`(기본값 `False`)를 추가합니다. 기본 동작은 계속 현재 프로젝트만 조회합니다. |
| 결과 | 각 항목에 `project_id`와, 가능하면 프로젝트 이름을 포함합니다. `limit`/`offset` 페이지네이션을 유지합니다. |
| 정책 거부(403) | 실패로 반환하고, 현재 프로젝트 결과로 대체하지 않습니다. |
| 좁혀진 결과 | 성공 응답에 현재 프로젝트만 있으면 정책 때문에 범위가 좁혀졌을 수 있다는 경고를 붙입니다. |
| 토큰 Role | 진단 정보로만 쓰고, 허용 여부 판단에는 쓰지 않습니다. |
| 인증 모드 | 고정 자격 증명 모드와 multi-user Application Credential 모드가 같은 코드 경로를 사용합니다. |

**도구 범위**

| 범위 | 도구 | 동작 |
|---|---|---|
| 1단계 | `get_project_details`(프로젝트 목록), `get_instance_details`, `search_instances`, `get_instances_by_status`, `get_volume_list`, `get_volume_snapshots` | `all_projects` 지원 |
| 이후 단계 | Network, Image, Heat 등 다른 서비스 | 미착수 |
| 변경 없음 | `set_*` 도구, 이름 기반 단건 조회(예: `get_instance_by_name`) | 현재 프로젝트만 조회, `ALLOW_MODIFY_OPERATIONS=false` 기본값 유지 |

**문서화할 운영자 구성 방식** (MCP 서버가 아니라 OpenStack에서 설정)

| 방식 | 구성 | 비고 |
|---|---|---|
| A | `admin` Role | 간단하지만 권한 과다 |
| B | 전용 Role + policy 재정의 | 최소 권한, 권장 |
| C | multi-user 모드 요청 헤더에 넣는 제한된 Application Credential(Role 일부 또는 access rules) | multi-user 모드 |

고정 자격 증명 모드 경고: 서버에 접속하는 모든 클라이언트가 서버 자격 증명의 권한으로
조회합니다.

**검증**

| 구분 | 확인 항목 |
|---|---|
| 단위 테스트 | 스위치가 꺼져 있으면 OpenStack을 호출하지 않음, 403은 실패로 반환, 단일 프로젝트 결과에는 경고가 붙음, 변경 도구는 계속 프로젝트로 제한됨. |
| 실환경 | 대상 클라우드의 실제 정책 규칙 이름과 기본값 확인, `admin`(허용)과 `member`(거부) 비교, 테스트 클라우드의 정책을 바꿀 수 있으면 방식 B도 확인, 서비스별로 거부가 403인지 조용히 좁혀진 결과인지 기록, 실측하지 않은 방식은 Live unverified로 표시. |

**변경과 함께 수정할 문서** (각각 `.ko.md` 포함): README.md(프로젝트 범위 문구,
CLI-도구 매핑), `docs/security.md`, `docs/configuration.md`,
`docs/multi-user-guide.md`, `docs/validation.md`.

## [Issue #73](https://github.com/call518/MCP-OpenStack-Ops/issues/73) 후속 작업

### 전체 요청 범위를 완료하기 위한 필수 작업

- [ ] **관리자 cross-project 조회**: 위의
  [Issue #86](#issue-86-cross-project-조회) 항목에서 추적합니다.

### 선택적 후속 작업

- [ ] **OAuth 또는 브라우저 로그인**
  - 브라우저 기반 초기 설정이 필요할 때 수동 Application Credential 헤더 설정을 대신할
    인증 방식을 제공합니다.
  - 기존 Application Credential 방식에는 필수가 아닙니다.

- [ ] **Claude Desktop 사용자별 커스텀 헤더 검증**
  - 개인 커넥터가 조직 단위 커넥터를 통해 자격 증명을 공유하지 않고, 각 사용자의
    Application Credential 헤더를 보낼 수 있는지 확인합니다.
  - 자격 증명을 노출하지 않고 클라이언트 버전, 헤더 제한과 live 결과를 기록합니다.

