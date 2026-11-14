[English](security.md) | **Korean**

# 보안, 격리, 안전 장치

이 가이드는 서버가 OpenStack에 인증하는 방식과, 볼 수 있고 바꿀 수 있는 범위를
어떻게 제한하는지 설명합니다. 클라이언트별 인증 지원 현황, 프로젝트 격리, 변경
도구의 읽기 전용 기본값, HTTP 접근을 위한 Bearer 토큰 인증을 다룹니다. 사용자별
OpenStack 계정은 [다중 사용자 가이드](multi-user-guide.ko.md)를 참고하세요.

## 클라이언트별 인증 지원 현황

서버 배포 하나는 OpenStack에 다음 두 방식 중 하나로만 인증합니다.

- **Password** (단일 계정 모드, 기본값): 서버가 자신의 환경에서 `OS_USERNAME`,
  `OS_PASSWORD`, `OS_PROJECT_NAME`을 읽습니다. 그 서버의 모든 클라이언트가 이 계정
  하나로 동작합니다.
- **Application Credential** (다중 사용자 모드, `MCP_MULTI_USER=true` 또는
  `--multi-user`, `streamable-http` 전용): 요청마다
  `X-OpenStack-Application-Credential-ID`와
  `X-OpenStack-Application-Credential-Secret` 헤더를 보냅니다. 사용자와 프로젝트는
  credential이 정하고, 서버의 `OS_*` 계정은 쓰지 않습니다.
  [다중 사용자 가이드](multi-user-guide.ko.md)를 참고하세요.

단일 계정 모드는 Application Credential을 받지 않으며,
`OS_APPLICATION_CREDENTIAL_*` 변수도 없습니다. 이 사항은 [TODO](../ToDo.ko.md)에
미결정 항목으로 기록되어 있습니다.

2026-11-13 기준 현황 (소스 `54cb03a`):

| 클라이언트 | Password | Application Credential | 비고 |
|---|---|---|---|
| Claude Desktop, 확장 번들 (`.mcpb`) | ✅ | ❌ Not implemented | 번들은 서버를 stdio로 실행하고 credential 입력 항목이 없음. 다중 사용자 모드는 `streamable-http`가 필요함 |
| OpenWebUI, Docker Compose | ✅ | ⚠️ Live unverified | Password: 모든 OpenWebUI 사용자가 OpenStack 계정 하나를 씀. Application Credential: 헤더에 사용자 한 명의 credential만 담긴 개인용 또는 소유자 제한 연결에서만 사용. 공유 연결 하나로는 사용하지 않음. [클라이언트 호환성](multi-user-guide.ko.md#클라이언트-호환성) 참고 |
| Claude Code CLI | ✅ | ✅ | 서버는 `streamable-http`로 실행. Password: 계정은 서버 환경에만 있고 Claude Code는 Bearer 토큰만 보냄. Application Credential: 버전 2.1.312로 실제 HTTPS MCP 서버에 등록해 테스트함 |
| Claude Code IDE 확장 | ⚠️ Live unverified | ⚠️ Live unverified | CLI와 같은 등록 방식이며 별도로 테스트하지 않음 |

## 프로젝트 격리

MCP-OpenStack-Ops는 `OS_PROJECT_NAME` 환경 변수가 정하는 프로젝트 안에서
동작합니다(다중 사용자 모드에서는 각 요청의 Application Credential이 정합니다).

- **프로젝트 범위 리소스**: 작업은 지정한 프로젝트 안의 리소스로 제한되며, 프로젝트
  소유권을 확인합니다.
- **다른 프로젝트 접근 방지**: 리소스 조회는 프로젝트 범위 안에서 이루어지고
  소유권을 확인하므로, 다른 프로젝트에 있는 이름이 비슷한 리소스를 실수로 다루지
  않게 합니다.
- **서비스 단위 필터링**: 각 서비스가 현재 프로젝트 ID로 리소스를 필터링합니다.
- **공유 리소스 접근**: 프로젝트가 쓸 수 있는 공유·공개 리소스(네트워크, 이미지)는
  포함됩니다.

클라우드 전체를 다루는 관리 API(예: 하이퍼바이저, 서비스, agent)는 프로젝트
리소스가 아니므로, 결과는 계정의 OpenStack 정책에 따라 달라집니다.

**프로젝트별로 필터링되는 리소스:**

| 서비스 | 프로젝트 범위 리소스 | 비고 |
|---------|-------------------------|-------|
| **Identity** | 사용자(역할 할당 기준), 역할 할당 | 현재 프로젝트에 역할이 있는 사용자만 |
| **Compute** | 인스턴스, Flavor(내장 데이터), 키페어 | 프로젝트 범위의 모든 인스턴스 |
| **Image** | 비공개 이미지(소유), Public/Community/Shared 이미지 | 이미지가 0개로 보이는 문제를 막는 필터링 |
| **Network** | 네트워크, 서브넷, 보안 그룹, Floating IP, 라우터 | 접근을 위해 공유·외부 네트워크 포함 |
| **Storage** | 볼륨, 스냅샷, 백업 | 프로젝트 안의 모든 스토리지 리소스 |
| **Orchestration** | Heat 스택, 스택 리소스 | 프로젝트 안의 모든 orchestration |
| **Load Balancer** | 로드밸런서, 리스너, 풀 | 프로젝트 안의 모든 로드밸런싱 |
| **Monitoring** | 리소스 사용량, 프로젝트 quota | 프로젝트별 모니터링 데이터 |

여러 프로젝트를 쓰려면 프로젝트마다 서버 인스턴스를 하나씩 실행하세요.
[다중 프로젝트 구성](configuration.ko.md#다중-프로젝트-구성)을 참고하세요.
여러 프로젝트를 조회만 하려면 [cross-project 조회 가이드](cross-project-guide.ko.md)를 참고하세요.

### cross-project 조회 (고급)

OpenStack CLI의 `--all-projects`처럼 여러 프로젝트를 조회하는 것은 관리자와 운영자를
위한 선택 기능이며 기본으로 꺼져 있습니다(`ALLOW_CROSS_PROJECT_READ=false`). 켜면 일부
목록 도구가 `all_projects=true`를 받습니다. 여러 프로젝트를 조회할 수 있는지는 이
서버가 아니라 OpenStack 정책이 판단하며, 변경 도구는 계속 프로젝트 범위로 제한됩니다.
[cross-project 조회 가이드](cross-project-guide.ko.md)를 참고하세요.

### 프로젝트 격리 테스트

클라우드에서 프로젝트 격리를 확인하려면, 대상 프로젝트의 `OS_*` 변수로 포함된
테스트를 실행하세요.

```bash
uv run python test_project_isolation.py
```

**출력 예:**
```
🔒 OpenStack Project Isolation Security Test
==================================================
📋 Testing project isolation for: your-project

1️⃣ Testing Connection and Project ID...
✅ Connection successful
✅ Current project ID: abc123-def456-ghi789
✅ Project name 'your-project' matches project ID

2️⃣ Testing Resource Ownership Validation...
✅ Found 5 compute instances
   Instance web-server-01: ✅ Owned
   Instance db-server-01: ✅ Owned
✅ Found 3/8 owned networks
✅ Found 10/10 owned volumes

3️⃣ Testing Service-Level Project Filtering...
✅ Compute service returned 5 instances
✅ Network service returned 3 networks
✅ Storage service returned 10 volumes

4️⃣ Testing Secure Resource Lookup...
ℹ️  Network 'admin' not found or not accessible in current project
ℹ️  Instance 'demo' not found or not accessible in current project

🎯 Project Isolation Test Results
========================================
✅ All security tests passed!
✅ Project 'your-project' isolation verified
✅ Cross-project access prevention confirmed

🔒 Your OpenStack MCP Server is properly secured!
```

이 테스트는 프로젝트 ID 확인과 일치 여부, 리소스 소유권 검증, 서비스 단위 프로젝트
필터링, 다른 프로젝트 접근을 막는 안전한 리소스 조회를 확인합니다.

## 변경 작업 보호

기본적으로 OpenStack 리소스를 바꾸거나 지울 수 있는 작업은 안전을 위해 모두
**꺼져** 있습니다.

```bash
# Default setting - Only read-only operations allowed
ALLOW_MODIFY_OPERATIONS=false
```

**보호되는 작업(`ALLOW_MODIFY_OPERATIONS=false`일 때):**
- 인스턴스 관리(start, stop, restart, pause, unpause)
- 볼륨 작업(create, delete, attach, detach)
- 키페어 관리(create, delete, import)
- Floating IP 작업(create, delete, associate, disassociate)
- 스냅샷 관리(create, delete)
- 이미지 관리(create, delete, update)
- Heat 스택 작업(create, delete, update)

**항상 사용 가능(읽기 전용 작업):**
- 클러스터 상태와 모니터링
- 리소스 목록(인스턴스, 볼륨, 네트워크 등)
- 서비스 상태 점검
- 사용량과 quota 정보
- 검색과 필터링

**⚠️ 변경 작업을 켜려면:**
```bash
# Enable all operations (USE WITH CAUTION)
ALLOW_MODIFY_OPERATIONS=true
```

**도구 등록 동작:**
- `ALLOW_MODIFY_OPERATIONS=false`: 읽기 전용 도구만 MCP 서버에 등록됩니다.
- `ALLOW_MODIFY_OPERATIONS=true`: 모든 도구(읽기 전용 + 변경 작업)가 등록됩니다.
- 사용 가능한 도구는 서버 시작 시 정해지므로, 이 설정을 바꾸면 재시작해야 합니다.

**권장 사항:**
- 운영 환경에서는 `ALLOW_MODIFY_OPERATIONS=false`를 유지하세요.
- 변경 작업은 개발·테스트 환경에서만 켜세요.
- 환경마다 설정을 분리하세요.
- 변경 기능을 켜기 전에 어떤 작업이 가능한지 검토하세요.
- `ALLOW_MODIFY_OPERATIONS` 설정을 바꾼 뒤에는 MCP 서버를 다시 시작하세요.

## Bearer 토큰 인증

`streamable-http` 모드에서 이 MCP 서버는 원격 접근을 보호하는 Bearer 토큰 인증을
지원합니다. 운영 환경에서 서버를 실행할 때 특히 중요합니다.

### 설정

**인증 켜기:**

```bash
# In .env file
REMOTE_AUTH_ENABLE=true
REMOTE_SECRET_KEY=<REMOTE_SECRET_KEY>
```

비밀값은 예를 들어 `openssl rand -hex 32`로 만드세요.

**또는 CLI로:**

```bash
uv run python -m mcp_openstack_ops --type streamable-http --auth-enable --secret-key <REMOTE_SECRET_KEY>
```

### 보안 수준

1. **stdio 모드**(기본값): 로컬에서만 접근하며 인증이 필요 없습니다.
2. **streamable-http + REMOTE_AUTH_ENABLE=false/미설정**: 인증 없이 원격 접근 ⚠️ **운영 환경에 권장하지 않음**
3. **streamable-http + REMOTE_AUTH_ENABLE=true**: Bearer 토큰 인증을 거친 원격 접근 ✅ **운영 환경에 권장**
4. **streamable-http + MCP_MULTI_USER=true**: 각 요청이 호출자의 프로젝트 범위 Keystone Application Credential로 인증하며, 기본적으로 HTTPS OpenStack endpoint가 필요합니다. HTTP는 `MCP_MULTI_USER_ALLOW_INSECURE_HTTP=true`로 격리된 개발·테스트 환경에서만 쓸 수 있습니다.
5. **streamable-http + MCP_MULTI_USER=true + REMOTE_AUTH_ENABLE=true**: 각 요청은 먼저 공유 Bearer 인증을, 그다음 사용자별 Application Credential 인증을 통과해야 합니다. [다중 사용자 가이드](multi-user-guide.ko.md)를 참고하세요.

> **🔒 기본 정책**: `REMOTE_AUTH_ENABLE`과 `MCP_MULTI_USER`는 모두 기본값이 `false`입니다. `REMOTE_SECRET_KEY`를 설정해도 `REMOTE_AUTH_ENABLE=true`일 때만 쓰이며, 두 모드를 함께 켜면 두 인증을 모두 통과해야 합니다.

### 클라이언트 설정

인증을 켜면 MCP 클라이언트는 Authorization 헤더에 Bearer 토큰을 넣어야 합니다.

```json
{
  "mcpServers": {
    "mcp-openstack-ops": {
      "type": "streamable-http",
      "url": "http://your-server:8000/mcp",
      "headers": {
        "Authorization": "Bearer <REMOTE_SECRET_KEY>"
      }
    }
  }
}
```

### 보안 권장 사항

- 운영 환경에서 streamable-http 모드를 쓸 때는 **항상 인증을 켜세요**.
- **무작위로 생성한 강한 비밀 키**를 쓰세요(32자 이상 권장).
- 가능하면 **HTTPS를 쓰세요**(SSL/TLS를 적용한 리버스 프록시 구성).
- 방화벽이나 네트워크 정책으로 **네트워크 접근을 제한하세요**.
- 보안을 위해 **비밀 키를 주기적으로 교체하세요**.
- 무단 접근 시도가 있는지 **접근 로그를 모니터링하세요**.

### 오류 처리

인증에 실패하면 서버는 다음을 반환합니다.
- 토큰이 없거나 잘못되면 **401 Unauthorized**
- 디버깅을 위한 JSON 형식의 **상세 오류 메시지**
