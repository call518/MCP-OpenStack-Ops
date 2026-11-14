[English](configuration.md) | **Korean**

# 서버 설정

이 가이드는 명령줄 옵션, 환경 변수, OpenStack endpoint와 HTTPS 설정, MCP 클라이언트
설정 템플릿, 여러 프로젝트 구성, 구 버전 OpenStack 릴리스용 openstacksdk 버전 변경을
다룹니다.

## 명령줄 옵션

```bash
uv run python -m mcp_openstack_ops --help

Options:
  --log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}
                        Logging level
  --type {stdio,streamable-http}
                        Transport type (default: stdio)
  --host HOST          Host address for HTTP transport (default: 127.0.0.1)
  --port PORT          Port number for HTTP transport (default: 8080)
  --auth-enable        Enable Bearer token authentication for streamable-http mode
  --secret-key SECRET  Secret key for Bearer token authentication
  --multi-user         Use request-local Application Credentials (streamable-http only)
```

## 환경 변수

| 변수 | 설명 | 기본값 | 용도 |
|----------|-------------|---------|--------|
| **OpenStack 인증** |
| `OS_AUTH_HOST` | OpenStack Identity 서비스 호스트 | 필수 | 인증 호스트 주소 |
| `OS_AUTH_PORT` | OpenStack Identity 서비스 포트 | 필수 | 인증 포트 |
| `OS_AUTH_PROTOCOL` | 연결 프로토콜(http 또는 https) | `http` | 운영 환경에서 SSL/TLS를 쓰려면 `https` |
| `OS_CACERT` | HTTPS용 SSL CA 인증서 경로 | 선택 | 안전한 HTTPS 연결에 필요(예: `/etc/ssl/certs/ca.pem`). HTTPS에서 설정하지 않으면 SSL 검증이 꺼짐(안전하지 않음) |
| `OS_USERNAME` | OpenStack 사용자 이름 | 단일 계정 모드에서 필수 | 다중 사용자 요청 인증에는 쓰이지 않음 |
| `OS_PASSWORD` | OpenStack 비밀번호 | 단일 계정 모드에서 필수 | 다중 사용자 요청 인증에는 쓰이지 않음 |
| `OS_PROJECT_NAME` | OpenStack 프로젝트 이름 | 단일 계정 모드에서 필수 | 다중 사용자 모드의 범위는 각 Application Credential이 정함 |
| `OS_IDENTITY_API_VERSION` | Identity API 버전 | `3` | API 버전 |
| `OS_PROJECT_DOMAIN_NAME` | 프로젝트 도메인 이름 | `default` | 도메인 범위 |
| `OS_USER_DOMAIN_NAME` | 사용자 도메인 이름 | `default` | 도메인 범위 |
| `OS_REGION_NAME` | OpenStack 리전 | `RegionOne` | 리전 범위 |
| **OpenStack 서비스 포트** |
| `OS_COMPUTE_PORT` | Compute 서비스 포트 | `8774` | Nova endpoint |
| `OS_NETWORK_PORT` | Network 서비스 포트 | `9696` | Neutron endpoint |
| `OS_VOLUME_PORT` | Volume 서비스 포트 | `8776` | Cinder endpoint |
| `OS_IMAGE_PORT` | Image 서비스 포트 | `9292` | Glance endpoint |
| `OS_PLACEMENT_PORT` | Placement 서비스 포트 | `8780` | Placement endpoint |
| `OS_HEAT_STACK_PORT` | Heat orchestration 서비스 포트 | `8004` | Heat API endpoint |
| `OS_HEAT_STACK_CFN_PORT` | Heat CloudFormation 서비스 포트 | `18888` | Heat CFN API endpoint(원래 기본값 8000을 Docker 포트 충돌을 피하려고 변경) |
| **MCP 서버 설정** |
| `MCP_LOG_LEVEL` | 로그 수준 | `INFO` | 개발 시 디버깅 |
| `ALLOW_MODIFY_OPERATIONS` | 변경 작업 허용 | `false` | 상태 변경에 대한 안전 장치 |
| `ALLOW_CROSS_PROJECT_READ` | 지원하는 목록 도구에서 `all_projects=true` 허용 | `false` | 기능만 켜며, 허용 여부는 OpenStack 정책이 판단. 고급 기능. [cross-project 조회 가이드](cross-project-guide.ko.md) 참고 |
| `FASTMCP_TYPE` | 전송 방식 | `stdio` | 바꿀 일이 거의 없음 |
| `FASTMCP_HOST` | HTTP 호스트 주소 | `127.0.0.1` | HTTP 모드 전용 |
| `FASTMCP_PORT` | HTTP 포트 번호 | `8080` | HTTP 모드 전용 |
| **인증(선택)** |
| `MCP_MULTI_USER` | 요청 단위 사용자별 Application Credential 인증 사용 | `false` | Streamable HTTP 전용. 기본적으로 HTTPS OpenStack endpoint가 필요하며 공유 Bearer 인증과 함께 쓸 수 있음 |
| `MCP_MULTI_USER_ALLOW_INSECURE_HTTP` | 다중 사용자 모드에서 OpenStack API 요청에 HTTP 허용 | `false` | 개발/테스트 전용. `MCP_MULTI_USER=true`가 필요하며 자격 증명과 토큰이 평문으로 전송됨 |
| `REMOTE_AUTH_ENABLE` | streamable-http 모드의 Bearer 토큰 인증 사용 | `false` | 운영 환경 보안 |
| `REMOTE_SECRET_KEY` | Bearer 토큰 인증용 공유 비밀값 | 인증을 켜면 필수 | 두 모드를 함께 켜면 사용자별 인증보다 먼저 확인됨 |
| **Docker Compose** |
| `DOCKER_BIND_ADDRESS` | 공개 포트의 바인드 주소 | `127.0.0.1` | HTTP 인증이 꺼져 있으면 로컬로 유지 |
| `DOCKER_EXTERNAL_PORT_OPENWEBUI` | OpenWebUI 호스트 포트 | `3000` | 브라우저 접속 |
| `DOCKER_EXTERNAL_PORT_MCP_SERVER` | MCP 서버 호스트 포트 | `8000` | 직접 MCP 클라이언트 |
| `DOCKER_EXTERNAL_PORT_MCPO_PROXY` | MCPO 호스트 포트 | `8080` | OpenAPI 프록시와 문서 |
| `MCPO_CONFIG_FILE` | Compose가 마운트하는 MCPO 설정 | `mcp-config.json.http.local` | Compose를 시작하기 전에 추적되는 HTTP 템플릿을 Git이 무시하는 이 로컬 파일로 복사 |

## OpenStack endpoint 구성

단일 계정 연결과 다중 사용자 연결은 모두 현재 하나의 `OS_AUTH_HOST`,
`OS_AUTH_PROTOCOL`, 그리고 `OS_*_PORT` 값으로 서비스 URL을 만듭니다. 나열된 모든
서비스를 한 호스트에서 노출하는 소규모 배포, API 게이트웨이, 가상 IP에서는 이
방식이 동작합니다. 서버는 현재 Keystone 서비스 catalog에서 서로 다른 서비스
호스트나 사용자 지정 URL 경로를 찾아내지 않습니다.

시작하기 전에 이 URL들이 `mcp-server` 컨테이너 안에서 접근 가능한지 확인하세요.
클라우드가 서비스마다 다른 호스트나 경로를 쓴다면, `OS_AUTH_HOST`에 게이트웨이나
리버스 프록시를 두고 설정한 포트를 해당 endpoint로 연결하세요. Keystone 호스트
이름만 넣고 진행하지 마세요. MCP 서버가 인증에는 성공하고 첫 서비스 도구에서
실패할 수 있습니다.

`OS_INTERFACE`는 이렇게 명시적으로 만든 endpoint URL을 바꾸지 않습니다. 현재 단일
호스트 구성은 internal interface 관례를 따릅니다.

서비스가 배포되지 않았어도 모든 서비스 URL이 만들어집니다. 방화벽이 그런 포트(예:
Cinder가 없는 클라우드의 `OS_VOLUME_PORT`)로 가는 트래픽을 조용히 버리면, 해당
서비스 호출은 바로 실패하지 않고 연결 timeout까지 기다립니다. 없는 서비스가 명시적
오류로 빨리 실패하도록, 그 포트를 거부(refuse)하게 하거나 접근 가능한 게이트웨이로
연결하세요.

Aodh(`alarming`)와 Gnocchi(`metric`)에는 `OS_*_PORT` 설정이 없습니다. 이 도구들은
`OS_INTERFACE`와 `OS_REGION_NAME`에 해당하는 Keystone catalog endpoint를 사용하며,
이 endpoint도 `mcp-server` 컨테이너에서 접근할 수 있어야 합니다.

## HTTPS와 사설 CA 설정

공개 CA가 서명한 HTTPS OpenStack endpoint라면, 컨테이너에 이미 있는 시스템 CA 번들을
사용하세요.

```dotenv
OS_AUTH_PROTOCOL=https
OS_CACERT=/etc/pki/tls/certs/ca-bundle.crt
```

사설 CA라면 인증서가 `mcp-server` 컨테이너 안에 있어야 합니다. `.env`에 호스트
경로만 적어서는 안 됩니다.

`docker-compose.yml`의 `mcp-server` 아래에 있는 CA 볼륨 예시의 주석을 풀고 값을
바꾸세요.

```yaml
volumes:
  - /absolute/host/path/openstack-ca.pem:/etc/ssl/certs/openstack-ca.pem:ro
```

그런 다음 컨테이너 안의 경로를 설정하고, MCP 경로를 다시 만들고, 로그를 확인하세요.

```dotenv
OS_AUTH_PROTOCOL=https
OS_CACERT=/etc/ssl/certs/openstack-ca.pem
```

```bash
docker compose up -d --force-recreate mcp-server mcpo-proxy
docker compose logs mcp-server
```

`OS_CACERT`가 없으면 단일 계정 HTTPS는 인증서 검증을 끄므로 안전한 운영 구성이
아닙니다. 다중 사용자 모드는 HTTPS가 켜져 있지 않으면 안전하게 실패하며, 전체
요건은 [다중 사용자 가이드](multi-user-guide.ko.md)에 있습니다.

## MCP 클라이언트 설정 템플릿

추적되는 `mcp-config.json.*` 파일은 참조용 템플릿입니다. 자격 증명을 넣기 전에 필요한
템플릿만 복사하세요. `.local`로 끝나는 파일은 모두 Git이 무시합니다.

```bash
cp mcp-config.json.http mcp-config.json.http.local
cp mcp-config.json.multi-user mcp-config.json.multi-user.local
cp mcp-config.json.multi-project mcp-config.json.multi-project.local
cp mcp-config.json.stdio mcp-config.json.stdio.local
chmod 600 mcp-config.json.*.local
```

MCPO에는 `.env`에서 사본을 지정하세요. 예: `MCPO_CONFIG_FILE=mcp-config.json.multi-user.local`.
Compose를 쓰지 않는 클라이언트는 각자의 로컬 사본을 따로 가리키게 하세요. 추적되는
템플릿에는 실제 자격 증명을 절대 넣지 마세요.

## 다중 프로젝트 구성

MCP 서버 인스턴스 하나는 프로젝트 하나로 범위가 정해집니다
([프로젝트 격리](security.ko.md#프로젝트-격리) 참고). 여러 OpenStack 프로젝트를
관리하려면 `OS_PROJECT_NAME`이 다른 MCP 서버 인스턴스를 여러 개 배포하세요.

**예: 프로젝트 3개 관리**

```bash
# Project 1: Production Environment
OS_PROJECT_NAME=production
# ... other config
uv run python -m mcp_openstack_ops --type stdio

# Project 2: Development Environment
OS_PROJECT_NAME=development
# ... other config
uv run python -m mcp_openstack_ops --type streamable-http --port 8001

# Project 3: Testing Environment
OS_PROJECT_NAME=testing
# ... other config
uv run python -m mcp_openstack_ops --type streamable-http --port 8002
```

**Claude Desktop 다중 프로젝트 설정 예:**

```json
{
  "mcpServers": {
    "openstack-production": {
      "command": "python",
      "args": ["-m", "mcp_openstack_ops", "--type", "stdio"],
      "env": {
        "OS_PROJECT_NAME": "production",
        "OS_USERNAME": "<user>",
        "OS_PASSWORD": "<password>",
        "OS_AUTH_HOST": "<keystone-host>"
      }
    },
    "openstack-development": {
      "command": "python",
      "args": ["-m", "mcp_openstack_ops", "--type", "stdio"],
      "env": {
        "OS_PROJECT_NAME": "development",
        "OS_USERNAME": "<user>",
        "OS_PASSWORD": "<password>",
        "OS_AUTH_HOST": "<keystone-host>"
      }
    },
    "openstack-testing": {
      "command": "python",
      "args": ["-m", "mcp_openstack_ops", "--type", "stdio"],
      "env": {
        "OS_PROJECT_NAME": "testing",
        "OS_USERNAME": "<user>",
        "OS_PASSWORD": "<password>",
        "OS_AUTH_HOST": "<keystone-host>"
      }
    }
  }
}
```

이렇게 하면 Claude가 각 프로젝트에 독립적으로 접근하며, 환경 사이가 완전히 분리됩니다.

**📁 참조 설정 파일:**

전체 다중 프로젝트 설정 예시는 `mcp-config.json.multi-project`에 있습니다.
- **Production**: 안전을 위해 읽기 전용(`ALLOW_MODIFY_OPERATIONS=false`)
- **Development**: 모든 작업 허용(`ALLOW_MODIFY_OPERATIONS=true`)
- **Testing**: 디버그 로그 사용(`MCP_LOG_LEVEL=DEBUG`)

```bash
# Preserve the tracked template and customize only the ignored local copy
cp mcp-config.json.multi-project mcp-config.json.multi-project.local
chmod 600 mcp-config.json.multi-project.local
# Point the client to this file, or merge its contents into the client's
# existing private configuration. Do not overwrite an existing client config.
```

## 구 버전 OpenStack용 SDK 버전

구 버전 OpenStack 릴리스(Wallaby, Caracal, Bobcat 등)에서는 openstacksdk 버전을
환경에 맞게 바꿔야 할 수 있습니다. `uv` 환경, Claude Desktop 번들, `mcp-server`
Docker 이미지는 모두 `uv.lock`에 기록된 의존성 버전을 설치하므로,
`pyproject.toml`에서 버전을 바꾸고 lock을 다시 만드세요. 릴리스별 권장 버전은 README의
[호환성 표](../README.ko.md#호환성)에 있습니다.

**1단계: `pyproject.toml` 수정**
```toml
dependencies = [
    "openstacksdk==3.1.1",  # ← Change to your required version (e.g., 3.1.1 for Wallaby)
    # ... other dependencies unchanged
]
```

**2단계: `uv.lock` 갱신**
```bash
uv lock --upgrade-package openstacksdk
uv run --extra dev python -m pytest -q tests
```

**3단계: Docker 이미지 다시 빌드**

`Dockerfile.MCP-Server`는 `uv.lock`에 있는 패키지를 정확히 그대로 설치합니다.
`build-mcp-server-docker-image.sh`의 `VERSION`과 `docker-compose.yml`의 `mcp-server`
이미지 태그를 새 태그로 바꾼 뒤 빌드하고 시작하세요.
```bash
./build-mcp-server-docker-image.sh
docker compose up -d
```

> ⚠️ **중요**: `Dockerfile.MCP-Server`에서 패키지 버전을 직접 고치지 마세요. `uv.lock`이 `pyproject.toml`과 맞지 않으면 이미지 빌드가 실패합니다. `mcpo-proxy` 이미지(`Dockerfile.MCPO-Proxy`)는 자기 패키지를 따로 고정합니다. mcpo 0.0.20에는 mcp 1.x가 필요하고(mcp 2.x에서는 시작하지 못함), FastAPI 0.128.0이 필요합니다(FastAPI 0.162.2에서는 실패함). mcp 1.x 프록시도 mcp 2.x 서버에 정상적으로 연결됩니다.
