[English](openwebui-guide.md) | **Korean**

# Docker Compose로 OpenWebUI 사용하기

이 가이드는 Docker Compose로 MCP-OpenStack-Ops와 OpenWebUI를 실행하고 서로
연결합니다. README의 [빠른 시작](../README.ko.md#빠른-시작)은 같은 절차를 압축한
버전입니다.

## 구성 요소와 연결 경로

Compose 파일은 서비스 세 개를 시작합니다.

| 서비스 | 이미지 | 역할 |
| --- | --- | --- |
| `mcp-server` | `call518/mcp-server-openstack-ops` | MCP 서버. OpenStack과 통신하고 `/mcp`에서 Streamable HTTP로 MCP를 제공 |
| `open-webui` | `ghcr.io/open-webui/open-webui` | 채팅 화면과 모델 연결 |
| `mcpo-proxy` | `call518/mcpo-proxy-openstack-ops` | 선택 사항. [MCPO](https://github.com/open-webui/mcpo)가 MCP 도구를 OpenAPI(REST) 서버로 노출 |

OpenWebUI는 두 가지 방법 중 하나로 MCP 서버에 연결할 수 있습니다.

```text
Browser → OpenWebUI → MCP-OpenStack-Ops → OpenStack                (direct MCP)
Browser → OpenWebUI → MCPO (OpenAPI) → MCP-OpenStack-Ops → OpenStack (through MCPO)
```

### 직접 MCP와 MCPO 중 무엇을 쓸까?

MCPO는 필수가 아닙니다. OpenWebUI 0.13은 MCP 서버에 직접 연결할 수 있고, 직접
연결이 구성 요소가 더 적습니다. OpenAPI 호환성이 필요할 때 MCPO를 사용하세요.

| | 직접 MCP | MCPO 경유 |
| --- | --- | --- |
| OpenWebUI 연결 유형 | `MCP (Streamable HTTP)` | `OpenAPI` |
| Compose 내부 연결 URL | `http://mcp-server:8000/mcp` | `http://mcpo-proxy:8000/mcp-openstack-ops` |
| 요청 경로의 구성 요소 | OpenWebUI와 MCP 서버 | OpenWebUI, MCPO, MCP 서버 |
| 추가 설정 | 없음 | MCPO 설정 파일(`MCPO_CONFIG_FILE`) |
| 둘러볼 수 있는 REST 문서 | 없음 | 있음. `http://localhost:8080/mcp-openstack-ops/docs` |
| `mcp-server` 재시작 후 | 클라이언트가 세션 오류를 보고하면 다시 연결 | MCPO가 이전 MCP 세션을 유지하므로 `mcpo-proxy`를 재시작([문제 해결](#문제-해결) 참고) |
| 이런 경우에 사용 | OpenWebUI의 기본 MCP 지원을 쓸 때 | OpenAPI endpoint, 자동 생성 문서, 또는 OpenAPI만 쓰는 클라이언트가 필요할 때 |

MCPO 없이 실행하려면 필요한 두 서비스만 시작하세요.

```bash
docker compose up -d mcp-server open-webui
```

`mcpo-proxy` 이미지는 mcpo 0.0.20, mcp 1.30.0, FastAPI 0.128.0으로 고정되어
있습니다. mcpo 0.0.20은 mcp 2.x나 FastAPI 0.162.2에서 시작하지 못합니다. mcp
1.x 프록시도 mcp 2.x 서버에 정상적으로 연결됩니다. 두 경로에서의 사용자별 인증은
다중 사용자 가이드의 [클라이언트 호환성](multi-user-guide.ko.md#클라이언트-호환성)을
참고하세요.

## 사전 준비와 기본값

Git, Compose 플러그인이 있는 Docker, 접근 가능한 OpenStack 환경, OpenWebUI가
지원하는 모델 공급자가 필요합니다. 모델은 도구 호출(native tool calling)을
안정적으로 지원해야 합니다.

이 기본 구성은 Identity, Compute, Network, Block Storage, Image, Placement,
Orchestration API가 Docker 호스트에서 하나의 호스트 이름과 설정한 서비스 포트로
접근 가능한 OpenStack 배포를 대상으로 합니다. 서비스마다 호스트 이름이나 URL
경로가 다르다면 시작하기 전에
[OpenStack endpoint 구성](configuration.ko.md#openstack-endpoint-구성)을 확인하세요.

| 기본값 | 값 |
| --- | --- |
| OpenStack 계정 | `.env`의 계정 하나 |
| 사용 가능한 도구 | 읽기 전용. 변경 도구는 숨겨짐 |
| HTTP 인증 | 꺼짐 |
| 공개 네트워크 | localhost만 |
| MCPO 설정 | `mcp-config.json.http.local` |

## 1. 복제와 설정

```bash
git clone https://github.com/call518/MCP-OpenStack-Ops.git
cd MCP-OpenStack-Ops
cp .env.example .env
cp mcp-config.json.http mcp-config.json.http.local
chmod 600 mcp-config.json.http.local
openssl rand -hex 32
vi .env
```

`.env`에서:

1. `WEBUI_SECRET_KEY`를 생성한 값으로 바꿉니다.
2. 대상 OpenStack 환경에 맞게 `OS_*` 인증, 도메인, 리전, 프로토콜, 서비스 포트
   값을 설정합니다.
3. 다음 로컬 기본값은 그대로 둡니다.

```dotenv
ALLOW_MODIFY_OPERATIONS=false
MCP_MULTI_USER=false
REMOTE_AUTH_ENABLE=false
REMOTE_SECRET_KEY=
DOCKER_BIND_ADDRESS=127.0.0.1
MCPO_CONFIG_FILE=mcp-config.json.http.local
```

로컬 MCPO 설정 사본은 `mcpo-proxy`를 실행할 때만 필요합니다. 이 모드에서는 자격
증명이 들어 있지 않고, Compose의 내부 네트워크로 MCP 컨테이너에 연결합니다. Git이
무시하는 파일이라, 나중에 인증 설정을 바꿔도 추적되는 참조 템플릿은 바뀌지
않습니다. 템플릿의 Authorization 헤더 자리표시자는 `REMOTE_AUTH_ENABLE=false`인
동안 무시됩니다. Bearer 인증을 켤 때는 로컬 MCPO 사본의 `<REMOTE_SECRET_KEY>`를
`.env`에 설정한 값과 같은 값으로 바꾸세요.

## 2. 스택 시작

```bash
docker compose up -d
docker compose ps
```

`mcp-server`가 healthy가 되고 `mcpo-proxy`와 `open-webui`가 실행될 때까지
기다립니다.

| 서비스 | 로컬 URL | 용도 |
| --- | --- | --- |
| OpenWebUI | `http://localhost:3000` | 채팅 화면 |
| MCP 서버 | `http://localhost:8000/mcp` | 직접 MCP endpoint |
| MCPO 문서 | `http://localhost:8080/mcp-openstack-ops/docs` | 자동 생성된 OpenAPI 스키마와 테스트 화면 |

`mcp-server`가 unhealthy이면 계속하기 전에 로그를 확인하세요.

```bash
docker compose logs mcp-server
```

## 3. OpenWebUI 0.13 설정

`http://localhost:3000`을 열어 첫 관리자 계정을 만들고 모델 공급자를 추가합니다.
도구 호출을 안정적으로 지원하는 모델을 쓰세요.

가장 빨리 시작하려면 공급자 하나를 고르세요.

- **OpenAI:** **Settings → Admin → Connections**에서 OpenAI API 연결을 추가하고
  `https://api.openai.com/v1`과 API 키를 입력해 저장합니다.
  [OpenWebUI OpenAI 가이드](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-openai/)를
  참고하세요.
- **Docker 호스트의 Ollama:** Compose 설정이 이미 OpenWebUI를
  `http://host.docker.internal:11434`로 연결해 둡니다. Docker가 접근할 수 있는
  주소에서 Ollama가 수신하는지 확인하고, 도구 호출이 가능한 모델을 선택하세요.
  [OpenWebUI Ollama 가이드](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-ollama/)를
  참고하세요.
- **다른 OpenAI 호환 공급자나 로컬 서버:** **Settings → Admin → Connections**에
  base URL과 API 키를 추가합니다. 공급자가 모델 목록을 제공하지 않으면 모델 ID를
  직접 입력합니다.
  [OpenAI 호환 공급자 가이드](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-openai-compatible/)를
  참고하세요.

MCP 연결을 설정하기 전에, 선택한 모델이 새 채팅에 나타나는지 확인하세요.

### 3.1 외부 도구 서버 연결 추가

다음 중 하나를 선택하세요. 직접 MCP 방식이 구성 요소가 더 적습니다. OpenAPI
호환성이 필요하면 MCPO를 사용하세요.

**방법 A: 직접 MCP 연결**

**Settings → Admin → Tools → Integrations**를 열고 **External Tool Servers**에서
다음 연결을 추가합니다.

| 항목 | 값 |
| --- | --- |
| Type | `MCP (Streamable HTTP)` |
| Name | `MCP OpenStack Ops Direct` |
| ID | `mcp-openstack-ops-direct` 또는 자동 생성된 값 |
| URL | `http://mcp-server:8000/mcp` |
| Authentication | `None` |
| Function name filter list | 비워 둠 |
| Enabled | On |

`REMOTE_AUTH_ENABLE=true`이면 대신 `Bearer` 인증과 `REMOTE_SECRET_KEY` 값을
사용하세요. 연결을 저장하고 연결 확인이 성공하는지 봅니다. 지원 전송 방식과 현재
호환성 정보는
[OpenWebUI 기본 MCP 가이드](https://docs.openwebui.com/features/extensibility/mcp/)를
참고하세요.

**방법 B: MCPO OpenAPI 연결**

**Settings → Admin → Tools → Integrations**를 열고 **External Tool Servers**에서
다음 연결을 추가합니다.

| 항목 | 값 |
| --- | --- |
| Type | `OpenAPI` |
| Name | `MCP OpenStack Ops` |
| ID | `mcp-openstack-ops` 또는 자동 생성된 값 |
| URL | `http://mcpo-proxy:8000/mcp-openstack-ops` |
| Authentication | `None` |
| Function name filter list | 비워 둠 |
| Enabled | On |

관리자가 관리하는 연결이므로 OpenWebUI는 자기 컨테이너에서 스키마를 가져옵니다.
`http://localhost:8080`이 아니라 위의 Compose 서비스 주소를 쓰세요. OpenWebUI
컨테이너 안에서 `localhost`는 OpenWebUI 자신을 가리킵니다. 화면에서 입력한 base
URL의 `openapi.json`을 자동으로 가져옵니다. 연결을 저장하고 연결 확인이 성공하는지
봅니다.

### 3.2 전체 도구 목록을 위한 Tool Search 켜기

OpenStack 서버의 도구와 OpenWebUI 기본 도구를 합치면 모델 공급자가 요청당 허용하는
함수 정의 수를 넘을 수 있습니다. **Settings → Admin → System → Interface**를 엽니다.
설정 메뉴 위쪽의 개인용 Interface가 아니라, **Authentication** 아래에 있는 관리자용
**Interface** 항목입니다. **Chat** 섹션에서 다음과 같이 설정합니다.

| 설정 | 값 |
| --- | --- |
| Tool Search | On |
| Defer Built-in Tools | On |
| Deferral Threshold (characters) | `0` |
| Always Loaded Tools | 비워 둠 |

설정을 저장합니다. Tool Search는 전체 도구 목록을 유지하되, 맞는 도구가 필요해질
때까지 모델에는 `search_tools`, `call_tool`, 그리고 명시적으로 항상 불러오도록 한
도구만 보냅니다.
[OpenWebUI 도구 문서](https://docs.openwebui.com/features/extensibility/plugin/tools/)를
참고하세요.

### 3.3 OpenAI reasoning 모델 설정

이 단계는 기본값이 아닌 reasoning effort와 함수 도구가 둘 다 필요한 OpenAI
reasoning 모델에만 해당합니다. **Settings → Admin → AI → Connections**에서 해당
OpenAI 연결을 편집하고 API type을 **Responses**로 선택하세요. 최신 reasoning
모델에서 Chat Completions는 함수 도구와 `none`이 아닌 reasoning effort를 함께
지원하지 않습니다.

OpenWebUI 0.13.0에서는 채팅의 **Model controls → Advanced Params → Reasoning
Effort**를 **Default**로 두세요. **Custom**을 선택하면 값이 `medium`으로 초기화되고
Chat Completions 파라미터인 `reasoning_effort`가 전송되는데, 이는 Responses 요청에서
유효하지 않습니다. Default는 이 값을 보내지 않고 모델이 자기 기본 effort를 쓰게
합니다. Responses에 명시적인 값을 보내려면 대신 다음 사용자 지정 파라미터를
추가하세요.

```text
Name: reasoning
Value: {"effort":"medium"}
```

[OpenAI Responses 마이그레이션 가이드](https://developers.openai.com/api/docs/guides/migrate-to-responses)와
[OpenWebUI Open Responses 가이드](https://docs.openwebui.com/getting-started/quick-start/connect-a-provider/starting-with-open-responses/)를
참고하세요.

이런 제약이 없는 모델과 공급자는 평소의 API type과 reasoning 설정을 그대로 써도
됩니다.

### 3.4 채팅에서 연결 켜기

새 채팅을 열고 모델을 선택한 뒤, 입력창 옆의 **Integrations** 아이콘을 눌러
**Tools**에서 `MCP OpenStack Ops`를 켭니다. 전역 도구 서버 연결은 모든 채팅에서
자동으로 켜지지 않습니다.

## 4. 확인

모델에게 물어봅니다.

```text
Use mcp-openstack-ops to list the instances in my OpenStack project.
```

정상 응답이 오면, 채팅에서 고른 연결에 따라 OpenWebUI → MCP 서버 → OpenStack 경로나
OpenWebUI → MCPO → MCP 서버 → OpenStack 경로가 동작하는 것입니다. MCPO 방식이면
위의 문서 URL에도 자동 생성된 도구 endpoint가 나열되어야 합니다.

## 문제 해결

연결이 실패하면 선택한 경로에 쓰이는 서비스의 로그를 확인하세요.

```bash
docker compose logs mcp-server mcpo-proxy open-webui
```

OpenWebUI 0.13에서 자주 나오는 오류:

| 오류 | 원인 | 해결 |
| --- | --- | --- |
| `Cannot connect to host localhost` | 관리자 연결에 브라우저/호스트용 URL을 써서, OpenWebUI 컨테이너 안에서 접속하지 못함 | 직접 MCP는 `http://mcp-server:8000/mcp`, MCPO는 `http://mcpo-proxy:8000/mcp-openstack-ops`를 사용 |
| `tools: array too long` | 외부 도구와 기본 도구 정의가 모델 공급자의 요청 한도를 넘음 | 임계값 `0`으로 Tool Search를 켬 |
| `Function tools with reasoning_effort are not supported ... /v1/chat/completions` | Chat Completions가 함수 도구와 `none`이 아닌 reasoning effort를 함께 받음 | Responses를 쓰거나, reasoning이 필요 없으면 reasoning effort를 `none`으로 설정 |
| `Unsupported parameter: reasoning_effort ... moved to reasoning.effort` | OpenWebUI 0.13.0이 Responses 연결로 사용자 지정 Reasoning Effort를 보냄 | Reasoning Effort를 Default로 두고, 명시적 값이 꼭 필요할 때만 사용자 지정 `reasoning={"effort":"medium"}`을 사용 |
| MCPO 로그에 `POST http://mcp-server:8000/mcp "404 Not Found"`와 `McpError: Session terminated`, `mcp-server` 로그에 `Rejected request with unknown or expired session ID` | MCP 세션은 실행 중인 `mcp-server` 프로세스 안에만 존재함. `mcp-server`가 재시작된 뒤에도 MCPO는 이전 세션을 유지하고 다시 연결하지 않음. `docker compose restart`는 `mcp-server` health check를 기다리지 않으므로, MCPO가 종료 직전의 이전 프로세스에 연결할 수 있음 | `mcp-server`가 실행 중인 상태에서 `docker compose restart mcpo-proxy`를 실행. 둘 다 재시작하려면 `docker compose restart` 대신 `docker compose up -d --force-recreate mcp-server mcpo-proxy`를 사용. 직접 MCP 클라이언트가 같은 세션 오류를 보고하면 다시 연결 |

## 5. 필요할 때만 변경 작업 켜기

생성, 변경, 삭제 도구는 기본적으로 일부러 빠져 있습니다. 켜려면 `.env`에서
`ALLOW_MODIFY_OPERATIONS=true`로 설정하고 MCP 경로를 다시 만드세요.

```bash
docker compose up -d --force-recreate mcp-server mcpo-proxy
```

설정한 계정이 무엇을 바꿀 수 있는지는 여전히 OpenStack 정책이 결정합니다. Bearer
인증, localhost 밖 노출, 사용자 지정 설정 파일은 [설정 가이드](configuration.ko.md)를
참고하세요. 요청 단위 사용자 계정은 [다중 사용자 가이드](multi-user-guide.ko.md)를
참고하세요.

OpenWebUI 데이터 볼륨을 지우지 않고 스택을 멈추려면:

```bash
docker compose down
```

## 6. 설치 변형과 상세 가이드

위 절차는 로컬 단일 계정 평가용입니다. 환경이 다르면 해당 가이드를 따르세요.

| 환경 또는 요구 사항 | 참고 가이드 |
| --- | --- |
| OpenStack API가 공개 CA나 사설 CA로 HTTPS를 사용 | [HTTPS와 사설 CA 설정](configuration.ko.md#https와-사설-ca-설정) |
| OpenStack 서비스가 서로 다른 호스트나 URL 경로를 사용 | [OpenStack endpoint 구성](configuration.ko.md#openstack-endpoint-구성) |
| 호스트 포트 `3000`, `8000`, `8080`이 이미 사용 중 | [Docker Compose 환경 변수](configuration.ko.md#환경-변수) |
| MCP를 localhost 밖으로 노출 | [Bearer 인증과 원격 접근 주의 사항](security.ko.md#bearer-토큰-인증) |
| 사용자마다 별도의 OpenStack 계정을 사용 | [다중 사용자 설정과 사용 가이드](multi-user-guide.ko.md) |
| 고정 계정이나 프로젝트별로 MCP 항목을 따로 둠 | [다중 프로젝트 구성](configuration.ko.md#다중-프로젝트-구성) |
| 클라이언트가 Claude Desktop이나 Claude Code | [Claude Desktop 가이드](claude-desktop-guide.ko.md) 또는 [Claude Code 가이드](claude-code-guide.ko.md) |
| OpenAI reasoning 모델에 명시적 reasoning effort가 필요 | [OpenAI reasoning 모델 설정](#33-openai-reasoning-모델-설정) |
