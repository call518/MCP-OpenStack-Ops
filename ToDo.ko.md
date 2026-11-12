[English](ToDo.md) | **Korean**

# TODO

마지막 검토: 2026-11-13

이 문서는 아직 남은 작업만 관리합니다. 완료된 항목은 제거합니다.

## [Issue #86](https://github.com/call518/MCP-OpenStack-Ops/issues/86) cross-project 조회

1단계는 구현되었습니다. `ALLOW_CROSS_PROJECT_READ`로 켜는 6개 목록 도구의
`all_projects=true`이며, 허용 여부는 OpenStack 정책이 판단합니다.
[cross-project 조회](docs/security.ko.md#cross-project-조회)와
[검증 기록](docs/validation.ko.md)의 2026-11-13 항목을 참고하세요.

- [ ] **남은 cross-project 조회 작업**

| 항목 | 내용 |
|---|---|
| 정책 규칙 이름 | 테스트 클라우드에서 Nova, Cinder, Keystone의 전체 프로젝트 규칙 이름과 기본값 확인 |
| 방식 B 검증 | 전용 Role을 해당 정책 규칙에 추가하고, `admin` 없이 여러 프로젝트를 조회하는지 확인 |
| 방식 C 검증 | 다중 사용자 모드에서 제한된 Application Credential(Role 일부 또는 access rules) 확인 |
| 이후 서비스 | Network, Image, Heat 등 다른 서비스 |
| 다른 프로젝트 상세 | 현재 프로젝트가 아닌 프로젝트에 대한 `get_project_details` 리소스 수 |

## [Issue #73](https://github.com/call518/MCP-OpenStack-Ops/issues/73) 후속 작업

### 선택적 후속 작업

- [ ] **OAuth 또는 브라우저 로그인**
  - 브라우저 기반 초기 설정이 필요할 때 수동 Application Credential 헤더 설정을 대신할
    인증 방식을 제공합니다.
  - 기존 Application Credential 방식에는 필수가 아닙니다.

- [ ] **Claude Desktop 사용자별 커스텀 헤더 검증**
  - 개인 커넥터가 조직 단위 커넥터를 통해 자격 증명을 공유하지 않고, 각 사용자의
    Application Credential 헤더를 보낼 수 있는지 확인합니다.
  - 자격 증명을 노출하지 않고 클라이언트 버전, 헤더 제한과 live 결과를 기록합니다.

