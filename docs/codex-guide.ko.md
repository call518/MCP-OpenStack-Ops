[English](codex-guide.md) | **Korean**

# Codex

ChatGPT 데스크톱 앱의 Codex, Codex CLI, Codex IDE 확장은 설정 파일
`~/.codex/config.toml`(홈 디렉터리의 `.codex` 폴더) 하나를 함께 씁니다. 여기에
`[mcp_servers.<name>]` 표를 하나 추가하면 세 곳 모두에서 쓸 수 있습니다. 신뢰된
프로젝트 안의 `.codex/config.toml`에 추가하면 그 프로젝트에서만 쓰입니다.

아래 방법 중 **하나**를 선택하세요.

| 방법 | 이런 경우에 사용 | Codex 컴퓨터에 필요한 것 |
| --- | --- | --- |
| [1. `uvx`로 PyPI 패키지 실행](#방법-1-uvx로-pypi-패키지-실행) | Codex가 릴리스된 서버를 로컬에서 stdio로 시작 | uv, OpenStack API에 대한 네트워크 접근 |
| [2. 기존 HTTP 서버 사용](#방법-2-기존-http-서버-사용) | 실행 중인 Docker Compose `mcp-server`나 다른 Streamable HTTP 서버를 사용 | MCP 서버에 대한 네트워크 접근 |

이 파일에는 입력한 값이 평문으로 저장되므로 비공개로 두고 커밋하지 마세요.

## 방법 1: uvx로 PyPI 패키지 실행

`uvx`는 [uv](https://docs.astral.sh/uv/)에 포함되어 있습니다. `mcp-openstack-ops`
패키지를 [PyPI](https://pypi.org/project/mcp-openstack-ops/)에서 내려받아 캐시된 도구
환경에서 실행합니다. Codex를 처음 시작하기 전에 한 번 내려받아 두세요.

```bash
uvx mcp-openstack-ops --help
```

이후에는 캐시된 버전을 다시 쓰며 업데이트를 확인하지 않습니다. 업그레이드하려면
`uvx mcp-openstack-ops@latest --help`를 실행하고 Codex를 다시 시작하세요.

`~/.codex/config.toml`에 다음을 추가합니다.

```toml
[mcp_servers.MCP-OpenStack-Ops]
command = "uvx"
args = ["mcp-openstack-ops", "--type", "stdio"]
startup_timeout_sec = 120

[mcp_servers.MCP-OpenStack-Ops.env]
# Required
OS_AUTH_HOST = "<keystone-host>"
OS_AUTH_PORT = "5000"
OS_PROJECT_NAME = "<project>"
OS_USERNAME = "<user>"
OS_PASSWORD = "<password>"
# Optional; set to the server defaults
OS_AUTH_PROTOCOL = "http"
OS_CACERT = ""
OS_USER_DOMAIN_NAME = "Default"
OS_PROJECT_DOMAIN_NAME = "Default"
OS_REGION_NAME = "RegionOne"
OS_IDENTITY_API_VERSION = "3"
OS_ENDPOINT_SOURCE = "configured"
OS_INTERFACE = "internal"
OS_COMPUTE_PORT = "8774"
OS_NETWORK_PORT = "9696"
OS_VOLUME_PORT = "8776"
OS_IMAGE_PORT = "9292"
OS_PLACEMENT_PORT = "8780"
OS_HEAT_STACK_PORT = "8004"
MCP_LOG_LEVEL = "INFO"
ALLOW_MODIFY_OPERATIONS = "false"
ALLOW_CROSS_PROJECT_READ = "false"
LIST_MAX_LIMIT = "100"
INSTANCE_FILTER_MAX_MATCHES = "100"
```

- HTTPS를 쓰면 `OS_AUTH_PROTOCOL`과 `OS_CACERT`, 포트가 다르면 포트처럼 클라우드에
  맞게 바꿔야 하는 값만 고치세요. 각 묶음의 의미와 여기에 해당하지 않는 `.env` 키는
  [로컬 stdio 클라이언트](configuration.ko.md#로컬-stdio-클라이언트)에 정리되어 있습니다.
- Codex는 기본적으로 서버 시작을 10초 기다립니다. `startup_timeout_sec = 120`은
  패키지가 아직 캐시되지 않았을 때 `uvx`가 Python과 의존성을 설치할 시간을 줍니다.
- `ALLOW_MODIFY_OPERATIONS = "false"`이면 조회 도구만 등록됩니다.
- 릴리스되지 않은 소스 체크아웃을 쓰려면
  [Claude Desktop 방법 3](claude-desktop-guide.ko.md#방법-3-uv로-소스-체크아웃-실행)처럼
  준비한 뒤 `command = "uv"`와
  `args = ["--directory", "/path/to/MCP-OpenStack-Ops", "run", "mcp-openstack-ops", "--type", "stdio"]`를
  쓰세요.

파일을 고친 뒤 Codex를 다시 시작하세요. 데스크톱 앱 입력창이나 Codex CLI에서 `/mcp`로,
또는 `codex mcp list`로 서버를 확인한 뒤, 예를 들어 다음과 같이 물어보세요.

```text
MCP-OpenStack-Ops로 프로젝트의 모든 인스턴스를 나열해줘.
```

## 방법 2: 기존 HTTP 서버 사용

Codex는 Streamable HTTP 서버에 직접 연결하므로 브리지가 필요 없습니다. MCPO URL이
아니라 MCP 서버의 `/mcp` URL을 등록하세요. 호스트 포트 `8000`을 바꿨다면 그 값으로
바꾸고, loopback이 아닌 호스트에는 HTTPS를 쓰세요. 어떤 OpenStack 계정을 쓸지,
`set_*` 도구를 등록할지는 서버 자신의 `.env`가 결정합니다.

```toml
[mcp_servers.MCP-OpenStack-Ops]
url = "http://127.0.0.1:8000/mcp"
bearer_token_env_var = "OPENSTACK_MCP_TOKEN"
```

`bearer_token_env_var`는 서버의 `REMOTE_SECRET_KEY` 값(`Bearer ` 없이)을 담은 환경
변수의 이름입니다. Codex가 이 값을 `Authorization` 헤더로 보냅니다. 이 변수는 Codex를
시작하는 환경에 설정되어 있어야 합니다. 서버 인증이 꺼져 있으면
(`REMOTE_AUTH_ENABLE=false`) 이 줄을 지우세요.

[다중 사용자 모드](multi-user-guide.ko.md)(`MCP_MULTI_USER=true`) 서버에는 자기
Application Credential도 환경 변수에서 읽어 보냅니다.

```toml
[mcp_servers.MCP-OpenStack-Ops]
url = "https://mcp.example.com/mcp"
env_http_headers = { "X-OpenStack-Application-Credential-ID" = "OS_AC_ID", "X-OpenStack-Application-Credential-Secret" = "OS_AC_SECRET" }
```

서버가 Bearer 인증도 요구하면 `bearer_token_env_var`도 함께 두세요.

## 검증 현황

방법 1은 2026-11-21에 ChatGPT 데스크톱 앱의 Codex에서 확인했습니다. 이 `config.toml`
구성과 `startup_timeout_sec = 120`으로 PyPI의 패키지를 `uvx`로 시작했으며, 앱과
패키지 버전은 기록하지 않았습니다. Codex CLI와 IDE 확장은 같은 파일을 읽지만 따로
테스트하지 않았습니다. 방법 2는 단일 계정 모드와 다중 사용자 모드 모두 **Live
unverified**입니다.

[Codex MCP 문서](https://learn.chatgpt.com/docs/extend/mcp)와
[설정 참조](https://learn.chatgpt.com/docs/config-file/config-reference)를 참고하세요.
