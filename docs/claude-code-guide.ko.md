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
Use openstack-ops to list all instances in the project.
```

더 이상 필요 없으면 등록을 지우세요(서버가 멈추지는 않습니다).

```bash
claude mcp remove --scope user openstack-ops
unset OPENSTACK_MCP_TOKEN
```

이 Bearer 설정은 서버에 설정된 OpenStack 계정을 사용합니다. 실험 기능인 사용자별
인증은 [다중 사용자 가이드](multi-user-guide.ko.md)를 참고하세요.
[Claude Code MCP 문서](https://code.claude.com/docs/en/mcp)도 참고하세요.
