[English](claude-code-guide.md) | **Korean**

# Claude Code

먼저 Claude Code를 설치하고 MCP 서버를 `streamable-http` 모드로 시작하세요. 예를
들어 [OpenWebUI 가이드](openwebui-guide.ko.md)의 Docker Compose 스택을 쓸 수
있습니다. MCPO/OpenAPI 프록시 URL이 아니라 MCP 서버의 `/mcp` URL을 등록하세요. 아래
예시는 Docker 호스트 포트 `8000`을 씁니다. 배포에 맞게 호스트와 포트를 바꾸고, 원격
연결에는 HTTPS를 쓰세요. 등록한다고 서버가 시작되지는 않습니다.

기존 단일 계정 모드에서 `REMOTE_AUTH_ENABLE=true`이면, 서버의 `REMOTE_SECRET_KEY`를
셸 히스토리에 실제 값이 남지 않게 입력하세요.

```bash
read -rsp 'MCP Bearer token: ' OPENSTACK_MCP_TOKEN
echo
export OPENSTACK_MCP_TOKEN

claude mcp add-json --scope user openstack-ops '{"type":"http","url":"http://127.0.0.1:8000/mcp","headers":{"Authorization":"Bearer ${OPENSTACK_MCP_TOKEN}"}}'
claude mcp list
claude
```

Claude Code를 실행하는 터미널에서 `OPENSTACK_MCP_TOKEN`을 export된 상태로 유지하세요.
`--scope user`는 등록 정보를 일반 사용자 설정에 저장합니다. 서버 인증이 꺼져 있으면
대신 다음 명령으로 등록하세요.

```bash
claude mcp add --transport http --scope user openstack-ops http://127.0.0.1:8000/mcp
```

Claude Code에서 `/mcp`를 확인하고, 예를 들어 다음과 같이 물어보세요.

```text
openstack-ops로 프로젝트의 모든 인스턴스를 나열해줘.
```

더 이상 필요 없으면 등록을 지우세요(서버가 멈추지는 않습니다).

```bash
claude mcp remove --scope user openstack-ops
unset OPENSTACK_MCP_TOKEN
```

이 Bearer 설정은 서버에 설정된 OpenStack 계정을 사용합니다.

## 다중 사용자 모드: Application Credential 헤더

서버가 다중 사용자 모드(`MCP_MULTI_USER=true`, [다중 사용자 가이드](multi-user-guide.ko.md)
참고)로 실행 중이면, 모든 요청이 사용자 자신의 OpenStack Application Credential을 헤더
두 개에 담아 보내야 합니다. 헤더가 없으면 서버는 `Application credential headers are
required`와 함께 HTTP 401을 반환하고, `/mcp`에는 연결 실패로 표시됩니다.

`/mcp`에서는 헤더를 추가하거나 바꿀 수 없으며, 저장된 등록 정보 그대로 연결만 합니다.
`claude mcp add-json`으로 등록 정보에 헤더를 넣은 뒤 `/mcp`에서 다시 연결하세요. VS Code
확장은 CLI와 같은 user 범위 등록 정보를 읽습니다.

1. 도구가 작업할 사용자와 프로젝트로 Application Credential을 만드세요. Keystone은
   secret을 한 번만 보여 줍니다.

   ```bash
   openstack application credential create openstack-ops-mcp
   ```

2. 기존 등록을 credential 헤더 두 개가 들어간 등록으로 바꾸세요. 서버가
   `REMOTE_AUTH_ENABLE=true`이면 `Authorization` 헤더도 유지하세요. 인증이 꺼져 있으면
   서버는 이 헤더를 무시합니다.

   ```bash
   claude mcp remove --scope user openstack-ops
   claude mcp add-json --scope user openstack-ops '{"type":"http","url":"http://127.0.0.1:8000/mcp","headers":{"Authorization":"Bearer <shared-mcp-token>","X-OpenStack-Application-Credential-ID":"<application-credential-id>","X-OpenStack-Application-Credential-Secret":"<application-credential-secret>"}}'
   ```

3. Claude Code에서 `/mcp`를 열고 `openstack-ops`를 다시 연결하세요.

값은 사용자 설정에 평문으로 저장되며, 값을 넣은 명령줄은 따로 막지 않으면 셸
히스토리에 남습니다. 위에서 Bearer 토큰에 쓴 `${VARIABLE}` 형식도 Claude Code를 실행하는
프로세스의 환경에 변수가 export되어 있으면 이 헤더에 쓸 수 있습니다. VS Code 확장에서는
그 프로세스가 터미널이 아니라 VS Code(또는 VS Code Server) 프로세스이며, 이 형식은
확장에서 확인하지 않았습니다. 더 이상 필요 없으면 Application Credential을 삭제하세요.

```bash
openstack application credential delete openstack-ops-mcp
```

[Claude Code MCP 문서](https://code.claude.com/docs/en/mcp)도 참고하세요.
