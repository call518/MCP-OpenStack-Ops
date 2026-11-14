[English](multi-user-guide.md) | **Korean**

# 다중 사용자 HTTP 설정과 사용 가이드

이 서버는 직접 켜야 하는 실험 기능으로 다중 사용자 HTTP 모드를 제공합니다. 기존
프로젝트 소유권 확인과 기본 쓰기 제한은 그대로 유지됩니다. 이 옵션 없이도 일반
단일 계정 HTTP 모드와 stdio 모드를 그대로 쓸 수 있습니다.

## 인증

클라이언트는 **모든 요청**마다 전용 HTTP 헤더 두 개에 자신의 Keystone Application
Credential ID와 secret을 담아 보냅니다. 서버는 운영자가 설정한 Keystone으로 인증한 뒤,
그 사용자의 프로젝트 범위 연결로 요청을 실행합니다. 인증에 실패해도 서버 환경의
계정으로 대신 실행하지 않습니다. 이것은 사용자 지정 헤더 인증이며, OAuth 서버나
Keystone 토큰 전달 방식이 아닙니다.

공유 Bearer 인증은 선택 사항이며 별개로 동작합니다. `REMOTE_AUTH_ENABLE=true`이면
서버는 Keystone 인증을 시도하기 전에 `Authorization: Bearer <token>`을 요구합니다.
이때 모든 요청은 공유 Bearer 관문과 호출자의 Application Credential 인증을 모두
통과해야 합니다. `Authorization`은 OpenStack으로 전달되지 않습니다. Bearer 인증이
꺼져 있으면 설정된 `REMOTE_SECRET_KEY`는 무시됩니다.

Application Credential은 LDAP 비밀번호를 쓰지 않으며, 프로젝트와 위임된 역할이 이미
정해져 있습니다. Keystone 토큰을 그대로 쓰는 방식, 브라우저 로그인, 프로젝트 전환은
지원하지 않습니다. 다른 프로젝트에는 별도의 Application Credential과 클라이언트 항목을
쓰세요. `ALLOW_CROSS_PROJECT_READ=true`이면 지원하는 목록 도구가 `all_projects=true`를
받고, 요청마다 호출자의 Application Credential과 OpenStack 정책에 따라 허용 또는
거부됩니다. [cross-project 조회 가이드](cross-project-guide.ko.md)를 참고하세요.

HTTP 전송은 상태를 유지하지 않으며(stateless) JSON으로 응답합니다. HTTP 요청마다
Keystone 인증과 SDK 연결을 새로 만들며, 요청 사이에 인증이나 연결 캐시는 없습니다.
도구가 실패한 경우를 포함해 응답이 끝나면 연결과 HTTP pool을 닫습니다. SDK keyring
캐시는 꺼져 있습니다. 자격 증명을 일부러 파일이나 데이터베이스에 쓰지 않습니다.
연결을 닫으면 참조가 해제될 뿐, Python 프로세스 메모리가 암호학적으로 지워진다고
보장하지는 않습니다.

이 방식은 인증 트래픽이 늘어나는 대신 초기 보안 경계를 작게 유지합니다. Keystone이
내부적으로 자격 증명 검증 결과를 캐시할 수 있습니다. **폐기(revocation) 반영 시간에
대한 검증된 수치 보장은 아직 없습니다.** Keystone이 폐기된 자격 증명을 거부하면 다음
HTTP 요청부터 거부됩니다. 이미 인증되어 진행 중인 작업은 끝까지 진행될 수 있으며,
취소되거나 되돌려지지 않습니다. 지원 범위를 문서화하기 전에 대상 클라우드에서 실제
간격을 측정하세요. 요청 검증은 이미 제출된 비동기 OpenStack 작업을 취소하는 것과
다릅니다.

## 클라이언트용 Application Credential 만들기

각 클라이언트 사용자는 클라이언트가 관리할 OpenStack 프로젝트로 인증한 상태에서
Application Credential을 만듭니다. 예를 들어 그 프로젝트의 OpenRC 파일을 불러온 뒤:

```bash
source /path/to/project-openrc.sh
openstack application credential create mcp-openwebui \
  --description "MCP OpenWebUI access"
```

생성 응답에는 `id`와 `secret`이 들어 있습니다. 각각
`X-OpenStack-Application-Credential-ID`와
`X-OpenStack-Application-Credential-Secret`으로 설정하세요. secret은 생성 응답에서만
보이지만, 자격 증명이 만료되거나 삭제될 때까지 계속 쓸 수 있습니다. 잃어버렸다면
자격 증명을 지우고 새로 만드세요.

```bash
openstack application credential delete mcp-openwebui
```

`openstack application credential list`와 `show`로 ID는 다시 확인할 수 있지만 secret은
절대 확인할 수 없습니다. 생성 출력은 비공개로 두세요. 채팅에 붙여 넣거나, 커밋하거나,
공유 OpenWebUI/MCPO 설정에 저장하지 마세요. 최소 권한의 전용 OpenStack 사용자를 쓰고,
생성 출력에서 위임된 역할을 검토하며, 클라우드 정책과 운영 요구 사항을 알고 있다면
`--role`과 `--expiration`을 사용하세요. 관리자 동작이 명시적으로 필요하지 않다면
관리자 범위의 자격 증명을 만들지 마세요.

공식 [OpenStack Application Credential CLI 문서](https://docs.openstack.org/python-openstackclient/latest/cli/command-objects/identity/v3/index.html#application-credential)를
참고하세요.

## 서버 설정

서버에 Git과 uv가 설치되어 있으면, 이 모드를 소스로 쓰기 위해 `main`을
복제하고 설치하세요. 필요하면 uv가 Python 3.12를 자동으로 설치합니다.

```bash
git clone --branch main --single-branch \
  https://github.com/call518/MCP-OpenStack-Ops.git
cd MCP-OpenStack-Ops
uv sync --locked --extra dev
```

`uv sync`는 체크아웃한 소스와 고정된 의존성을 프로젝트 환경에 설치하므로 별도의
`pip install -e .`는 필요 없습니다. `dev` extra에는 아래 검증 테스트에 필요한 의존성이
들어 있습니다.

그 디렉터리에서 서버를 설정하고 시작하세요.

```bash
export OS_AUTH_HOST=cloud.example.com
export OS_AUTH_PORT=5000
export OS_AUTH_PROTOCOL=https
export OS_REGION_NAME=RegionOne
export ALLOW_MODIFY_OPERATIONS=false
export MCP_MULTI_USER=true
export REMOTE_AUTH_ENABLE=false
export REMOTE_SECRET_KEY=
# Optional for a private CA:
# export OS_CACERT=/path/to/cloud-ca.pem
uv run --locked python -m mcp_openstack_ops \
  --type streamable-http --host 127.0.0.1 --port 8080
```

`--multi-user`를 넘기는 대신 `MCP_MULTI_USER=true`를 설정해도 됩니다. 이 값들은
프로세스 환경 변수입니다. 새 모드는 서버 자격 증명용 `.env`나 `clouds.yaml`을 읽지
않습니다. `OS_USERNAME`, `OS_PASSWORD`, `OS_PROJECT_NAME`은 사용자 인증에 쓰이지
않습니다. 인증 통신 내용이 로그로 쏟아지는 것을 막기 위해 DEBUG 로그 수준은
거부됩니다.

사용자별 인증 전에 공유 Bearer 인증을 요구하려면 다음과 같이 설정하세요.

```bash
export MCP_MULTI_USER=true
export REMOTE_AUTH_ENABLE=true
export REMOTE_SECRET_KEY='<strong-random-secret>'
```

두 검사는 AND로 동작하며, 대체(fallback)나 OR로 동작하지 않습니다. Bearer 토큰이 없거나
잘못되면 Keystone에 접속하지 않고 401을 반환합니다. Bearer 토큰이 유효하면 이어서
일반 Application Credential 검사를 합니다. `MCP_MULTI_USER=false`이면 Bearer만 쓰는
단일 계정 HTTP 모드와 인증 없는 단일 계정 HTTP 모드를 그대로 쓸 수 있습니다.

지원하지 않는 OAuth metadata 경로(`/.well-known/oauth-protected-resource`,
`/.well-known/oauth-authorization-server`, `/.well-known/openid-configuration`과 그
하위 경로)와 `/register`는 Keystone 인증 없이 404를 반환합니다. 이 모드는 OAuth
discovery나 registration을 제공하지 않습니다. `/mcp`에는 여전히 두 application
credential 헤더와, 켜져 있다면 공유 Bearer 헤더가 필요합니다.

MCP 전송 계층의 HTTP 400 응답은 서버가 만든 `request_id`와 고정된 `reason` 분류를
담은 INFO 진단 로그를 남깁니다. 분류는 `invalid_json`, `invalid_jsonrpc`,
`unsupported_protocol`, `missing_session_id`, `unclassified` 중 하나입니다. 요청 본문,
헤더 값, 원본 오류 메시지는 이 진단에 들어가지 않습니다. 알 수 없거나, 너무 크거나,
JSON이 아닌 오류 응답은 분류되지 않을 수 있습니다. 400만으로는 인증 실패라고
단정할 수 없고, 보고된 첫 연결 동작을 설명하지도 못합니다. 결론을 내리기 전에 request
ID를 클라이언트 응답과 맞춰 보세요. 클라이언트가 더 새로운 프로토콜 버전으로 먼저
시도했다가 `unsupported_protocol`을 받고, 지원되는 버전으로 정상 협상할 수도
있습니다. 그 거부를 연결 실패로 보기 전에 초기화와 이후 요청이 성공하는지 확인하세요.
첫 400 응답을 없애려고 프로토콜 검증을 우회하지 마세요.

`/mcp`는 HTTPS 리버스 프록시를 통해 노출하세요. 평문 백엔드 포트를 클라이언트에
노출하지 마세요. 프록시는 두 자격 증명 헤더와 `Authorization`을 로그에서 가리고,
요청/헤더 덤프를 남기지 않으며, 인증 시도를 전달하기 전에 요청 수와 동시 접속 수를
제한하도록 설정하세요. APM, 크래시 덤프, swap, 외부 로그 수집기는 따로 검토하세요.
애플리케이션의 정리 작업은 그런 시스템을 통제하지 못합니다. 클라이언트는 자기 설정이나
secret 저장소에 자격 증명을 보관할 수밖에 없으며, 서버의 비저장 규칙은 클라이언트
저장소에는 적용되지 않습니다.

이 모드는 기존의 설정된 호스트 배포 방식을 따릅니다. compute, network, volume, image,
placement, Heat endpoint는 `OS_AUTH_HOST`와 기존 `OS_*_PORT` 변수를 쓰며, 기본적으로
인증서 검증을 하는 HTTPS를 사용합니다. identity URL은 `/v3`로 끝납니다. 다른 SDK
서비스는 Keystone catalog를 쓰며, 그 endpoint도 같은 프로토콜을 써야 합니다. 아래의
테스트 전용 예외를 명시적으로 켜지 않는 한 평문 SDK 요청은 거부됩니다. 리다이렉트된
요청은 항상 거부됩니다. 기존의 수동 Heat/Octavia 점검도 검증된 설정 프로토콜을 쓰며
리다이렉트를 따르지 않습니다. 내부 서비스가 HTTP만 지원하는 배포에서는 HTTPS endpoint
없이 이 모드를 안전하게 쓸 수 없습니다. CA 경로를 설정하지 않으면 표준 시스템 신뢰
저장소가 적용되며, 암묵적으로 `verify=False`로 대체되지 않습니다.

HTTP만 지원하는 OpenStack 클라우드에서 격리된 개발이나 기능 테스트를 할 때는 HTTPS
보호 장치를 명시적으로 끌 수 있습니다.

```bash
export MCP_MULTI_USER=true
export MCP_MULTI_USER_ALLOW_INSECURE_HTTP=true
export OS_AUTH_PROTOCOL=http
```

이렇게 하면 Application Credential secret과 발급된 토큰이 평문으로 전송됩니다. 격리된
테스트 네트워크와, 만료 기간이 짧고 버려도 되는 최소 권한 자격 증명만 쓰고, 테스트가
끝나면 지우세요. 이 옵션의 기본값은 `false`이고, 시작 시 `INSECURE TEST MODE` 경고를
출력하며, 운영 환경에서는 절대 켜면 안 됩니다. 두 모드 모두에서 리다이렉트는 계속
꺼져 있습니다.

## 클라이언트 호환성

| 클라이언트 | 초기 상태 |
| --- | --- |
| Claude Code CLI | 버전 2.1.312를 등록하고 실제 HTTPS MCP 서버로 테스트함 |
| Claude Code IDE 통합 | 따로 테스트하지 않음 |
| Claude Desktop, 사용자마다 자기 `claude_desktop_config.json`의 `mcp-remote` | 2026-11-14에 Windows에서 `mcp-remote@0.15.2`로 테스트함. 각 사용자의 컴퓨터에는 자기 credential만 있음. [Claude Desktop 방법 4](claude-desktop-guide.ko.md#다중-사용자-모드-사용자별-application-credential) 참고 |
| Claude Desktop 원격 사용자 지정 커넥터 | 요청 헤더 기능을 쓸 수 있고 각자 소유한 자격 증명 설정이 가능할 때만 조건부로 가능. 검증하지 않음 |
| Claude Desktop 조직 공유 고정 헤더 | 사용자별 계정에는 맞지 않음. 한 사람의 자격 증명을 공유하지 말 것 |
| OpenWebUI 기본 MCP, 비공개 또는 소유자 전용 연결 | 사용자 지정 헤더에 그 사용자의 Application Credential만 담으면 호환. 검증하지 않음 |
| OpenWebUI 기본 MCP, 여러 사용자가 공유하는 연결 하나 | 맞지 않음. 고정된 사용자 지정 헤더 때문에 모든 UI 사용자가 같은 OpenStack 계정을 쓰게 됨 |
| OpenWebUI/MCPO, 사용자마다 독립 인스턴스 | 고정된 upstream 헤더에 그 사용자의 Application Credential만 담으면 호환. 검증하지 않음 |
| OpenWebUI/MCPO, 여러 사용자가 공유하는 연결 하나 | 맞지 않음. 고정된 upstream 헤더 때문에 모든 UI 사용자가 같은 OpenStack 계정을 쓰게 됨 |
| OAuth가 필요한 클라이언트 | 이 사용자 지정 인증 모드에서는 지원하지 않음 |

Claude Code 예시(사용자 설정, 자리표시자만 사용):

```json
{
  "mcpServers": {
    "openstack-personal": {
      "type": "http",
      "url": "https://mcp.example.com/mcp",
      "headers": {
        "Authorization": "Bearer <shared-mcp-token>",
        "X-OpenStack-Application-Credential-ID": "<your-application-credential-id>",
        "X-OpenStack-Application-Credential-Secret": "<your-application-credential-secret>"
      }
    }
  }
}
```

`REMOTE_AUTH_ENABLE=false`이면 자리표시자 `Authorization` 헤더를 남겨 둬도 서버가
무시합니다. 인증을 켜면 자리표시자를 바꿔서, 모든 클라이언트가 자기 Application
Credential과 별도로 공유 MCP 토큰을 받게 하세요.

### OpenWebUI 기본 MCP

OpenWebUI 0.6.31 이상은 MCPO 없이 서버의 Streamable HTTP endpoint에 직접 연결할 수
있습니다. **Settings → Admin → Tools → Integrations**에서 다음 값으로 외부 도구 서버
연결을 추가하세요.

| 항목 | 값 |
| --- | --- |
| Type | `MCP (Streamable HTTP)` |
| URL | 로컬 Compose 네트워크에서는 `http://mcp-server:8000/mcp`, 운영 환경에서는 HTTPS URL |
| Authentication | `REMOTE_AUTH_ENABLE=false`이면 `None`, 아니면 `REMOTE_SECRET_KEY`를 쓰는 `Bearer` |

**Advanced**를 펼치고 **Headers**에 다음 JSON 객체를 입력하세요.

```json
{
  "X-OpenStack-Application-Credential-ID": "<APPLICATION_CREDENTIAL_ID>",
  "X-OpenStack-Application-Credential-Secret": "<APPLICATION_CREDENTIAL_SECRET>"
}
```

OpenWebUI는 이 사용자 지정 헤더를 모든 MCP 요청에 합쳐서 보냅니다. Bearer 인증을
선택하면 `Authorization`은 따로 들어가므로 위 JSON에 넣지 마세요. 연결을 저장하고
확인한 뒤, 채팅의 **Integrations** 메뉴에서 켜세요.

OpenWebUI의 MCP 연결은 관리자가 관리합니다. 연결마다 고정된 Application Credential
하나가 저장되므로, OpenWebUI Access Control로 그 자격 증명의 소유자에게만 노출하거나
독립된 OpenWebUI 인스턴스를 쓰세요. 여러 사용자가 쓸 수 있게 하지 마세요. `{{USER_ID}}`
같은 헤더 템플릿은 호출자를 식별할 수는 있지만, 그 사용자의 OpenStack Application
Credential을 찾아 넣지는 못합니다. 이 OpenWebUI 직접 연결 경로는 지원되는 설정 동작을
근거로 문서화했으며, 이 저장소에서 live 검증하지 않았습니다.

공식 [OpenWebUI MCP 사용자 지정 헤더 문서](https://docs.openwebui.com/features/extensibility/mcp/#custom-headers)를
참고하세요.

### MCPO를 거치는 OpenWebUI

Docker Compose 빠른 시작은 인증 없는 단일 계정 접근을 위해 `mcp-config.json.http`의
사본인 `mcp-config.json.http.local`(Git이 무시)을 씁니다. 독립된 다중 사용자
OpenWebUI/MCPO 인스턴스용으로는 저장소에 다음과 같은 별도 템플릿이 있습니다.

```json
{
  "mcpServers": {
    "mcp-openstack-ops": {
      "type": "streamable-http",
      "url": "http://mcp-server:8000/mcp",
      "headers": {
        "Authorization": "Bearer <REMOTE_SECRET_KEY>",
        "X-OpenStack-Application-Credential-ID": "<APPLICATION_CREDENTIAL_ID>",
        "X-OpenStack-Application-Credential-Secret": "<APPLICATION_CREDENTIAL_SECRET>"
      }
    }
  }
}
```

이것이 `mcp-config.json.multi-user`의 내용입니다. 기술적으로는 이 파일을 직접 고쳐서
지정할 수도 있지만, 자리표시자를 바꾸면 재사용 가능한 비밀값이 버전 관리되는 파일에
들어가 Git diff나 실수로 한 커밋으로 노출됩니다. 권장 절차는 추적되는 템플릿을 그대로
두는 것입니다.

```bash
cp mcp-config.json.multi-user mcp-config.json.multi-user.local
chmod 600 mcp-config.json.multi-user.local
```

Git이 무시하는 `.local` 사본에 그 사용자의 Application Credential ID와 secret을
넣으세요. `REMOTE_AUTH_ENABLE`에 따라 `Authorization` 항목을 남기거나 지운 뒤, 비공개
`.env` 파일에 다음 값을 설정하세요.

```dotenv
MCP_MULTI_USER=true
MCPO_CONFIG_FILE=mcp-config.json.multi-user.local
```

`docker compose up -d --force-recreate mcp-server mcpo-proxy`로 해당 서비스를 다시
만드세요. 공유 OpenWebUI 연결에는 이 방식을 쓰지 마세요. 모든 UI 사용자가 같은
OpenStack 계정을 물려받게 됩니다. 로컬 파일에는 재사용 가능한 비밀값이 들어 있으니
비공개로 두고 절대 커밋하지 마세요. 빠른 시작의 평문 로컬 MCP 구간은 격리된 평가용일
뿐입니다. 운영 환경에서는 클라이언트/프록시와 MCP 서버 사이에 TLS를 쓰세요.

실제 값은 비공개 사용자 설정에만 두고, 커밋되는 `.mcp.json`이나 이슈 댓글에는 절대
넣지 마세요. 헤더 값은 initialize, discovery, 도구 요청에 모두 보내야 합니다. 사용자와
프로젝트는 Keystone이 정하며, 클라이언트가 보낸 역할이나 프로젝트 헤더로 정해지지
않습니다. 클라이언트 컴퓨터에는 로컬 OpenStack SDK, CLI, 브리지, 서버가 필요 없습니다.

Claude Desktop의 원격 커넥터 헤더는 제한된 베타 기능입니다. 사용자 지정 헤더 이름에는
Anthropic의 승인이 필요할 수 있고, 조직 단위 고정 자격 증명은 커넥터를 쓰는 모든
사람에게 공유될 수 있습니다. 사용자별 접근을 조직 전체 자격 증명으로 대신하지 마세요.
Claude Desktop에서 사용자별 헤더를 쓰려면 대신 사용자마다 자기
`claude_desktop_config.json`에서 `mcp-remote`를 쓰세요. 헤더를 그 사용자의 컴퓨터에서
보내며, 그 컴퓨터에 Node.js 18 이상이 필요합니다.
[Claude Desktop 방법 4](claude-desktop-guide.ko.md#다중-사용자-모드-사용자별-application-credential)를
참고하세요. OAuth 흐름은 별도의 설계 결정이며, 공유 자격 증명으로 조용히 대체하는 방식이
아닙니다.

이 브랜치를 설계하면서 확인한 자료:

- [Claude Code HTTP 설정](https://code.claude.com/docs/en/mcp)
- [Claude 커넥터의 요청 헤더 제한](https://claude.com/docs/connectors/custom/add-unlisted#authenticate-with-request-headers)
- [Keystone Application Credentials](https://docs.openstack.org/keystone/latest/user/application_credentials.html)
- [OpenWebUI 기본 MCP 사용자 지정 헤더](https://docs.openwebui.com/features/extensibility/mcp/#custom-headers)

## 배포 검증 체크리스트

버려도 되는 테스트 프로젝트와 독립적으로 만든 자격 증명을 쓰세요. 비밀값이나 리소스
데이터를 공개하지 말고 클라이언트 버전, 서비스 버전, 결과를 기록하세요.

1. 프로젝트 범위 Application Credential로 Claude Code에서 연결합니다. 도구와 리소스를
   나열하고, 예상한 프로젝트 데이터가 반환되는지 확인합니다.
2. 서로 다른 프로젝트의 사용자 A와 B를 동시에 활성 상태로 둡니다. 각 프로젝트의
   인스턴스를 반복해서 조회하고, 어느 응답에도 상대 프로젝트의 비공개 리소스가 없는지
   확인합니다. 공개·공유 리소스는 기존 검사와 서비스 정책을 따릅니다. 프로젝트
   격리는 사용자별 소유권이 아닙니다.
3. 상대 프로젝트의 알려진 비공개 리소스 ID를 조회해 접근이 실패하는지 확인합니다.
   관리자 자격 증명도 같은 프로젝트 소유권 검사를 받습니다.
4. 같은 사용자를 프로젝트별 자격 증명 두 개(클라이언트 항목 두 개)로 연결해, 각 항목이
   의도한 프로젝트만 보는지 확인합니다.
5. 자격 증명 헤더 중 하나를 빼거나, 잘못 넣거나, 중복으로 넣습니다. 서버 환경에 유효한
   기존 자격 증명이 설정되어 있어도 어떤 도구도 실행되면 안 됩니다. 공유 Bearer
   인증을 켰다면 그 헤더도 빼거나 잘못 넣어, Keystone 인증을 시도하지 않는지
   확인합니다.
6. 관리자를 포함해 기본적으로 쓰기 도구가 없는지 확인합니다. 버려도 되는 환경에서만
   쓰기를 명시적으로 켜고, `reader`만 위임받은 자격 증명이 실제 클라우드 정책에서
   리소스를 바꿀 수 없는지 확인합니다.
7. 사용 중에 Application Credential을 폐기합니다. 호출을 반복하며 마지막으로 허용된
   요청과 처음 거부된 요청의 시각을 기록합니다. 새 연결도 실패하는지 확인합니다.
8. 서버/프록시 로그에 사용자 ID, 프로젝트 ID, 도구 이름, HTTP 완료가 기록되고,
   자격 증명 ID/secret이나 Keystone 토큰은 없는지 확인합니다. HTTP 200은 전달되었다는
   뜻이지, OpenStack 작업이 성공했다는 뜻은 아닙니다.
9. 새 플래그 없이 기존 stdio 배포와 단일 계정 HTTP 배포를 다시 실행합니다.
10. Claude Desktop은 `mcp-remote`와 사용자별 자기 설정으로 테스트합니다. 원격 사용자 지정
    커넥터는 개인별 헤더 설정을 독립적으로 할 수 있을 때만 테스트합니다. 키를 공유하지
    말고, UI나 헤더 승인 제한으로 쓸 수 없다면 그대로 보고합니다.

자동 점검(실제 OpenStack 호출 없음):

```bash
uv run --locked --extra dev python -m pytest -q tests
```

자동 테스트는 인증 거부와 재검증, 동기 도구를 포함한 동시 컨텍스트, Keystone보다
Bearer를 먼저 확인하는 순서, 정리 작업, 기본 쓰기 제한, 프로젝트 검사, 기존 캐시 동작을
다룹니다. 실제 Keystone 폐기 반영 시간, 서비스 정책 적용, Claude 클라이언트 호환성은
확인하지 못합니다.
