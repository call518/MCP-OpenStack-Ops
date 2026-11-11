[English](ToDo.md) | **Korean**

# TODO

마지막 검토: 2026-11-11

이 문서는 아직 남은 작업만 관리합니다. 완료된 항목은 제거합니다.

## [Issue #73](https://github.com/call518/MCP-OpenStack-Ops/issues/73) 후속 작업

### 전체 요청 범위를 완료하기 위한 필수 작업

- [ ] **관리자 cross-project 조회**
  - 일반 사용자는 Application Credential이 속한 프로젝트로 계속 엄격하게 제한합니다.
  - OpenStack 정책이 허용하는 관리자만 여러 프로젝트의 리소스를 나열하고 조회할 수 있게
    합니다.
  - cross-project 변경은 허용하지 않고, 전체 쓰기 도구의 기본값
    `ALLOW_MODIFY_OPERATIONS=false`를 유지합니다.
  - 실제 다중 프로젝트 OpenStack 환경에서 일반 사용자 거부와 관리자 조회 동작을
    검증합니다.

### 선택적 후속 작업

- [ ] **OAuth 또는 브라우저 로그인**
  - 브라우저 기반 초기 설정이 필요할 때 수동 Application Credential 헤더 설정을 대신할
    인증 방식을 제공합니다.
  - 기존 Application Credential 방식에는 필수가 아닙니다.

- [ ] **Claude Desktop 사용자별 커스텀 헤더 검증**
  - 개인 커넥터가 조직 단위 커넥터를 통해 자격 증명을 공유하지 않고, 각 사용자의
    Application Credential 헤더를 보낼 수 있는지 확인합니다.
  - 자격 증명을 노출하지 않고 클라이언트 버전, 헤더 제한과 live 결과를 기록합니다.

