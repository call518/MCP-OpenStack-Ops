[English](claude-desktop-guide.md) | **Korean**

# Claude Desktop

아래 방법 중 **하나**를 선택하세요. 방법 1이 가장 간단합니다. 파일로 설치하고 설정
양식을 채우면 되며, 설정 파일을 직접 편집할 필요가 없습니다. 방법 2~4는
`claude_desktop_config.json`에 서버 항목을 추가합니다. README의
[빠른 시작](../README.ko.md#빠른-시작)은 방법 1을 압축해서 보여 줍니다.

| 방법 | 이런 경우에 사용 | Claude Desktop 컴퓨터에 필요한 것 |
| --- | --- | --- |
| [1. 데스크톱 확장(`.mcpb`) (권장)](#방법-1-데스크톱-확장mcpb-권장) | 릴리스 버전을 한 번에 설치 | 확장을 지원하는 Claude Desktop |
| [2. `uvx`로 PyPI 패키지 실행](#방법-2-uvx로-pypi-패키지-실행) | `claude_desktop_config.json`에서 릴리스된 서버를 실행 | uv |
| [3. `uv`로 소스 체크아웃 실행](#방법-3-uv로-소스-체크아웃-실행) | 릴리스되지 않았거나 수정한 소스를 실행 | Git, uv |
| [4. `npx`로 기존 Docker HTTP 서버 사용](#방법-4-npx로-기존-docker-http-서버-사용) | 실행 중인 Docker Compose `mcp-server`를 재사용 | Node.js 18+ |

방법 1~3에서는 Claude Desktop이 그 컴퓨터에서 로컬 MCP 서버를 시작하며, 그
컴퓨터가 OpenStack API에 네트워크로 접근할 수 있어야 합니다. 방법 4에서는 Claude
Desktop이 `mcp-remote` 브리지만 시작합니다. MCP 서버는 같은 컴퓨터에서 실행되더라도
별도의 HTTP 서버이고, 자신의 `.env`로 OpenStack에 접속합니다.

예시의 서버 항목 이름은 `OpenStack-uvx`, `OpenStack-uv`, `OpenStack-npx`입니다.
서버 이름은 21자 이하로 하세요. 클라이언트가 도구 이름 앞에 서버 이름을 붙일 수
있고(Claude Code는 `mcp__<server>__<tool>`), Claude API는 도구 이름을 64자로
제한하며, 여기서 가장 긴 도구 이름은 36자입니다. 공개 인터넷에 있는 서버는
`claude_desktop_config.json`을 쓰지 않는 [원격 사용자 지정 커넥터](#원격-사용자-지정-커넥터)로
추가할 수도 있습니다.

## 방법 1: 데스크톱 확장(.mcpb) (권장)

3.7.1 이후의 각 [GitHub Release](https://github.com/call518/MCP-OpenStack-Ops/releases)에는
`mcp-openstack-ops-<version>.mcpb`가 들어 있습니다. 그 이전 릴리스에는 이 파일이
없습니다.

1. 릴리스에서 `.mcpb` 파일을 내려받습니다.
2. Claude Desktop에서 **Settings > Extensions > Advanced settings > Install
   Extension…**을 열고 파일을 선택합니다. Windows에서는 파일을 더블클릭하거나
   채팅 창으로 끌어다 놓아도 설치되지 않았습니다.
3. 설정 양식을 채웁니다. 각 항목 제목에는 그 항목이 설정하는 환경 변수가
   표시되며, [환경 변수](configuration.ko.md#환경-변수)에 정리되어 있습니다.
   Keystone 호스트, 프로젝트, 사용자 이름, 비밀번호는 필수입니다. 포트, 도메인,
   리전은 서버 기본값이 미리 들어 있습니다. CA 인증서는 선택입니다. **Allow modify
   operations**가 꺼져 있으므로 조회 도구만 등록됩니다. **Allow cross-project
   reads**도 꺼져 있습니다. 켜기 전에 [cross-project 조회](security.ko.md#cross-project-조회)를
   참고하세요.

Claude Desktop은 비밀번호를 `claude_desktop_config.json`에 쓰지 않고 민감한 값으로
따로 저장합니다. 번들에는 소스, `pyproject.toml`, `uv.lock`이 들어 있고, Claude
Desktop이 uv로 Python과 고정된 의존성을 설치합니다. 업그레이드하려면 새 릴리스의
`.mcpb` 파일을 설치하세요. 체크아웃에서 번들을 직접 만들려면
`scripts/build-mcpb.sh <version>`을 실행하세요. Python 3와 Node.js가 필요하며
`dist/mcp-openstack-ops-<version>.mcpb`가 만들어집니다.

번들은 MCPB `uv` 서버 유형(manifest 버전 0.4)을 사용합니다. 이를 처음 지원하는 Claude
Desktop 버전은 문서화되어 있지 않습니다. 설치가 거부되면 Claude Desktop을
업데이트하거나 방법 2를 사용하세요. 이 프로젝트는 Python 3.12만 지원하며
(`requires-python = ">=3.12,<3.13"`), uv는 이에 맞는 Python 버전과 고정된 의존성을
설치합니다.

## 방법 2~4의 설정 파일

Claude Desktop의 **Settings > Developer > Edit Config**를 열거나 파일을 직접
편집하세요.

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

기존 `mcpServers` 객체에 항목을 합친 뒤 Claude Desktop을 완전히 종료했다가 다시
시작하세요. MCP 로그는 `~/Library/Logs/Claude`(macOS), `%APPDATA%\Claude\logs`(Windows),
`~/.config/Claude/logs`(Linux)에 있습니다. 이 파일에는 입력한 값이 평문으로
저장되므로 비공개로 두고 커밋하지 마세요.

## 방법 2: uvx로 PyPI 패키지 실행

`uvx`는 [uv](https://docs.astral.sh/uv/)에 포함되어 있습니다. `mcp-openstack-ops`
패키지를 PyPI에서 내려받고, 필요하면 알맞은 Python을 설치한 뒤 캐시된 도구
환경에서 실행하므로 저장소를 복제할 필요가 없습니다. Claude Desktop을 처음
실행하기 전에 한 번 내려받아 두세요.

```bash
uvx mcp-openstack-ops --help
```

처음 실행하면 [PyPI](https://pypi.org/project/mcp-openstack-ops/)의 최신 릴리스가
설치되고, 이후에는 캐시된 버전을 다시 쓰며 업데이트를 확인하지 않습니다.
업그레이드하려면 `uvx mcp-openstack-ops@latest --help`를 실행하고 Claude Desktop을
다시 시작하세요. 모든 컴퓨터에서 같은 버전을 쓰려면 명령과 `args` 모두에
`mcp-openstack-ops@X.Y.Z` 같은 정확한 버전을 쓰세요.

```json
{
  "mcpServers": {
    "OpenStack-uvx": {
      "command": "uvx",
      "args": ["mcp-openstack-ops", "--type", "stdio"],
      "env": {
        "OS_AUTH_HOST": "<keystone-host>",
        "OS_AUTH_PORT": "5000",
        "OS_PROJECT_NAME": "<project>",
        "OS_USERNAME": "<user>",
        "OS_PASSWORD": "<password>",
        "OS_USER_DOMAIN_NAME": "Default",
        "OS_PROJECT_DOMAIN_NAME": "Default",
        "OS_REGION_NAME": "RegionOne",
        "ALLOW_MODIFY_OPERATIONS": "false"
      }
    }
  }
}
```

클라우드에 필요한 endpoint, HTTPS, 포트 변수는 [환경 변수](configuration.ko.md#환경-변수)에서
골라 추가하세요. `ALLOW_MODIFY_OPERATIONS=false`이면 조회 도구만 등록됩니다. 추적되는
`mcp-config.json.stdio` 템플릿은 이 프로젝트 컨테이너 안의 소스 경로인
`PYTHONPATH=/app/src`를 설정합니다. Claude Desktop에는 그 `command`가 아니라 `env`
값만 사용하세요.

## 방법 3: uv로 소스 체크아웃 실행

PyPI에 릴리스되지 않은 변경을 쓸 때 이 방법을 사용하세요. Git과
[uv](https://docs.astral.sh/uv/)가 필요하며, uv가 Python 3.12와 고정된 의존성을
설치합니다.

Claude Desktop 컴퓨터에 이 저장소를 복제하세요. 아래 명령과 설정의
`/path/to/MCP-OpenStack-Ops`는 이 복제본의 절대 경로이며, `pyproject.toml`, `uv.lock`,
`src/`가 있는 디렉터리입니다. 그런 다음 Claude Desktop을 처음 실행할 때 설치를
기다리지 않도록 환경을 한 번 준비해 둡니다.

```bash
git clone https://github.com/call518/MCP-OpenStack-Ops.git /path/to/MCP-OpenStack-Ops
uv --directory /path/to/MCP-OpenStack-Ops sync
```

Windows에서는 명령에 `C:\work\MCP-OpenStack-Ops` 같은 Windows 경로를 쓰고, JSON에는
`C:\\work\\MCP-OpenStack-Ops`처럼 쓰세요. Windows의 Claude Desktop에서는 WSL 안의
복제본이 아니라 Windows에 복제하세요. WSL 안의 `.venv`는 Linux용으로 만들어집니다.

복제본의 절대 경로로 항목을 추가합니다. 방법 2와 다른 것은 `command`와 `args`뿐입니다.

```json
{
  "mcpServers": {
    "OpenStack-uv": {
      "command": "uv",
      "args": ["--directory", "/path/to/MCP-OpenStack-Ops", "run",
               "mcp-openstack-ops", "--type", "stdio"],
      "env": {
        "OS_AUTH_HOST": "<keystone-host>",
        "OS_AUTH_PORT": "5000",
        "OS_PROJECT_NAME": "<project>",
        "OS_USERNAME": "<user>",
        "OS_PASSWORD": "<password>",
        "OS_USER_DOMAIN_NAME": "Default",
        "OS_PROJECT_DOMAIN_NAME": "Default",
        "OS_REGION_NAME": "RegionOne",
        "ALLOW_MODIFY_OPERATIONS": "false"
      }
    }
  }
}
```

`git pull` 후에는 Claude Desktop을 다시 시작해야 갱신된 소스가 적용됩니다.

## 방법 4: npx로 기존 Docker HTTP 서버 사용

Claude Desktop은 `claude_desktop_config.json`의 로컬 명령을 실행할 뿐, HTTP URL을
받지 않습니다. Docker Compose의 `mcp-server`를 쓰려면 서드파티 stdio-HTTP 브리지인
[`mcp-remote`](https://github.com/geelen/mcp-remote)를 사용하세요. Node.js 18 이상이
필요하며 Claude Desktop은 시스템의 Node.js를 씁니다. MCPO URL이 아니라 MCP 서버의
`/mcp` URL을 등록하세요. 호스트 포트 `8000`을 바꿨다면 그 값으로 바꾸세요.

```json
{
  "mcpServers": {
    "OpenStack-npx": {
      "command": "npx",
      "args": ["-y", "mcp-remote@0.15.2", "http://127.0.0.1:8000/mcp",
               "--transport", "http-only",
               "--header", "Authorization:${REMOTE_SECRET_KEY}"],
      "env": {
        "REMOTE_SECRET_KEY": "Bearer <REMOTE_SECRET_KEY>"
      }
    }
  }
}
```

`mcp-remote`는 이 `env` 값을 `Authorization` 헤더에 넣습니다. 값은 `Bearer `, 공백,
그리고 MCP 서버의 `REMOTE_SECRET_KEY` 값으로 설정하세요. `Bearer ` 접두사가 없으면
서버가 연결을 거부합니다. `OS_PASSWORD`는 쓰지 마세요. OpenStack 자격 증명은 서버의
`.env`에 그대로 있습니다. 접두사를 `env`에 두는 이유는 Windows의 Claude Desktop이
`args`의 공백을 이스케이프하지 않기 때문입니다. 서버 인증이 꺼져 있으면
(`REMOTE_AUTH_ENABLE=false`) `--header` 인자와 `env`를 지우세요. `mcp-remote` 버전은
고정해 두세요. 평문 HTTP는 loopback 주소에만 쓰고, 다른 호스트라면 서버를 HTTPS로
공개하세요. 어떤 OpenStack 계정을 쓸지, `set_*` 도구를 등록할지는 서버 자신의
`.env`가 결정합니다.

## 원격 사용자 지정 커넥터

이것은 `claude_desktop_config.json` 방식이 아닙니다. 원격 커넥터는
`claude_desktop_config.json`이 아니라 Claude의 **Customize > Connectors > Add custom
connector**에서 추가합니다. Claude는 사용자 컴퓨터가 아니라 Anthropic 클라우드에서
서버에 접속하므로, 서버에 공개 인터넷에서 접근 가능한 HTTPS URL이 있어야 합니다.
사설 네트워크, VPN, 방화벽 뒤의 서버는 허용 목록에 넣거나 MCP 터널을 쓰지 않으면
접근할 수 없습니다.

이 서버는 OAuth를 구현하지 않습니다. `REMOTE_AUTH_ENABLE=true`이면 **No sign-in**을
선택하고, 값이 스킴을 포함한 `Bearer <REMOTE_SECRET_KEY>`인 `authorization` 요청
헤더를 추가하세요. 요청 헤더 인증은 모든 조직에서 쓸 수 있는 것은 아닌 베타
기능입니다. 이 토큰을 가진 사람은 누구나 서버에 설정된 OpenStack 계정을 쓸 수
있습니다. 인증 없이 이 서버를 노출하지 마세요.
[Bearer 토큰 인증](security.ko.md#bearer-토큰-인증)을 검토하고, 쓰기가 꼭 필요하지
않으면 `ALLOW_MODIFY_OPERATIONS=false`로 두세요. 다중 사용자 모드는 사용자 지정
`X-OpenStack-*` 헤더를 쓰며, 사용자 지정 헤더 이름에는 Anthropic의 승인이
필요합니다. [다중 사용자 가이드](multi-user-guide.ko.md)를 참고하세요.

## 검증 현황

방법 1은 만든 번들이 `mcpb validate`를 통과했고, 압축을 푼 `mcp_config`를 호스트
방식으로 변수 치환한 뒤 MCP 클라이언트로 실행했습니다. 3.7.1부터 3.7.4까지의
릴리스에는 릴리스 workflow가 번들을 첨부했습니다. 방법 2~4는 같은 명령, 인자, 환경으로
MCP 클라이언트에서 확인했습니다. 방법 2는 PyPI에서 내려받은 것이 아니라 로컬
체크아웃을 `uvx`로 설치해서 확인했습니다. 서버 인증을 켠 상태에서 방법 4는
`Bearer ` 값으로 연결되었고, 접두사가 없거나 키가 틀리면 거부되었습니다. 원격 사용자
지정 커넥터 경로는 검증하지 않았습니다.

[Claude Desktop 로컬 MCP 가이드](https://modelcontextprotocol.io/docs/develop/connect-local-servers),
[데스크톱 확장(MCPB)](https://claude.com/docs/connectors/building/mcpb),
[사용자 지정 커넥터](https://claude.com/docs/connectors/custom/remote-mcp)를 참고하세요.
