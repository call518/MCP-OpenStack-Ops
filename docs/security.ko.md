[English](security.md) | **Korean**

# 보안, 격리, 안전 장치

이 가이드는 서버가 볼 수 있고 바꿀 수 있는 범위를 어떻게 제한하는지 설명합니다.
프로젝트 격리, 변경 도구의 읽기 전용 기본값, HTTP 접근을 위한 Bearer 토큰 인증을
다룹니다. 사용자별 OpenStack 계정은 [다중 사용자 가이드](multi-user-guide.ko.md)를
참고하세요.

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
여러 프로젝트를 조회만 하려면 [cross-project 조회](#cross-project-조회)를 참고하세요.

### cross-project 조회

서버에 `ALLOW_CROSS_PROJECT_READ=true`(기본값 `false`)가 설정되어 있으면, 일부 목록
도구가 OpenStack CLI의 `--all-projects`처럼 `all_projects=true`를 받습니다.

| 도구 | `all_projects=true`일 때 |
|---|---|
| `get_instance_details`, `search_instances`, `get_instances_by_status` | 조회 가능한 모든 프로젝트의 인스턴스. 각 항목에 `project_id`와 `project_name` 포함 |
| `get_volume_list`, `get_volume_snapshots` | 조회 가능한 모든 프로젝트의 볼륨 또는 스냅샷. 각 항목에 `project_id`와 `project_name` 포함 |
| `get_project_details` | 조회 가능한 모든 프로젝트의 요약(ID, 이름, 도메인, 활성 여부, `is_current`). 리소스 수는 계속 현재 프로젝트만 제공 |

- **조회 가능한 자격 증명**: 대상 OpenStack 서비스의 정책이 해당 자격 증명의 토큰에
  전체 프로젝트 목록 API를 허용할 때만 여러 프로젝트를 조회할 수 있습니다.
  MCP-OpenStack-Ops는 이 판단을 위해 Role이나 Group을 정의·저장·검사하지 않습니다.
- **스위치의 역할**: `ALLOW_CROSS_PROJECT_READ`는 이 서버에서 파라미터의 동작을 켤 뿐
  권한을 부여하지 않습니다. 고정 자격 증명 모드에서는 서버에 접속하는 모든 클라이언트가
  서버 자격 증명의 권한으로 조회합니다. 다중 사용자 모드에서는 요청마다 호출자의
  Application Credential로 판정됩니다.
- **거부**: 정책 거부(HTTP 403)는 오류로 반환되며, 현재 프로젝트 결과로 대체되지
  않습니다. 일부 서비스는 권한 없는 요청을 거부하지 않고 호출자의 프로젝트로 좁힙니다.
  그래서 결과에 현재 프로젝트만 있으면 `scope.warning`이 붙습니다. 각 목록은
  `scope.projects_in_result`를 함께 보고합니다.
- **변경 없음**: `all_projects`가 없으면 모든 도구는 계속 현재 프로젝트만 다룹니다.
  변경 도구와 이름 기반 단건 조회(예: `get_instance_by_name`)는 항상 프로젝트 범위로
  제한됩니다.

cross-project 조회 권한은 이 서버가 아니라 OpenStack에서 설정합니다.

| 방식 | 구성 | 비고 |
|---|---|---|
| A | `admin` Role | 간단하지만 전체 관리 권한을 줌 |
| B | 전용 Role(예: `cross_project_reader`)을 각 서비스 정책의 전체 프로젝트 목록 규칙에 추가 | 최소 권한, 권장 |
| C | 다중 사용자 모드 요청 헤더로 보내는 제한된 Application Credential(Role 일부 또는 access rules) | 다중 사용자 모드 전용 |

관련 정책 규칙에는 Nova `os_compute_api:servers:detail:get_all_tenants`, Keystone
`identity:list_projects`, Cinder의 all-tenants 규칙이 있습니다. 사용하는 릴리스의 규칙
이름과 기본값은 예를 들어 `oslopolicy-policy-generator --namespace nova`로 확인하세요.

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
