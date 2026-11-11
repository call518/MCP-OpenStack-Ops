[English](development.md) | **Korean**

# 개발

이 가이드는 로컬 개발, 테스트, 도구 추가 방법을 다룹니다.

## 준비와 테스트 실행

Git과 [uv](https://docs.astral.sh/uv/)가 필요합니다. 필요하면 uv가 Python 3.12를
자동으로 설치합니다.

```bash
git clone https://github.com/call518/MCP-OpenStack-Ops.git
cd MCP-OpenStack-Ops
uv sync --locked --extra dev
uv run python -m pytest -q tests
```

단위 테스트에는 클라우드 자격 증명이 필요 없으며, CI도 같은 명령을 실행합니다.
의존성 버전은 `uv.lock`에서 정해집니다. openstacksdk 버전을 바꾸려면
[구 버전 OpenStack용 SDK 버전](configuration.ko.md#구-버전-openstack용-sdk-버전)을
참고하세요.

## 클라우드 대상 로컬 테스트

```bash
# Test with MCP Inspector (recommended)
./scripts/run-mcp-inspector-local.sh

# Test with debug logging
MCP_LOG_LEVEL=DEBUG uv run python -m mcp_openstack_ops

# Validate OpenStack connection
uv run python -c "from src.mcp_openstack_ops.functions import get_openstack_connection; print(get_openstack_connection())"
```

프로젝트 격리 확인은 [프로젝트 격리 테스트](security.ko.md#프로젝트-격리-테스트)를
참고하세요.

## live 도구 점검

`scripts/live_tool_check.py`는 등록된 모든 도구를 실제 MCP 클라이언트로 호출합니다
(in-process, 또는 `--url`을 주면 Streamable HTTP). 오류 경로도 포함하며, 비동기
작업은 openstacksdk로 최종 상태까지 확인하고, 만든 리소스는 지웁니다. 변경 도구를
켜면 `--prefix`(기본값 `mcpval`)로 이름을 붙인 프로젝트, 도메인, 사용자, 역할,
flavor, 네트워크, 이미지, 서버를 만들고 지우며, 정리 단계에서는 이름이 그 prefix로
시작하는 리소스를 모두 지웁니다. 관리자 계정으로, 버려도 되는 테스트 클라우드에서만
실행하세요. 상태를 바꾸는 실행에는 `--i-understand-this-is-destructive`가
필요합니다.

```bash
# OS_* variables for the test cloud, plus OS_AUTH_HOST/OS_AUTH_PORT for the server
. admin-openrc.sh
ALLOW_MODIFY_OPERATIONS=true uv run python scripts/live_tool_check.py \
  --i-understand-this-is-destructive \
  --image cirros --flavor m1.tiny --resize-flavor m1.small \
  --network demo-net --external-network public1 --existing-server demo1 \
  --output live-tool-check.json
```

요약에는 호출 수와 최종 상태 점검 수, 그리고 도구별 분류(`passed`,
`passed_partial_service`, `service_absent`, `error_paths_only`, `partial`, `failed`)가
나옵니다. 서비스가 배포되지 않은 도구는 명시적 오류를 반환하는 것만으로 통과하며,
이는 live 검증이 아닙니다. 결과 파일은 저장소에 넣지 마세요(`live-tool-check*.json`은
무시됨).

## 사용자 지정 도구 추가

이 MCP 서버는 쉽게 확장할 수 있도록 설계되었습니다. 다음 단계로 직접 도구를
추가하세요.

### 1. 헬퍼 함수 추가(선택)

재사용할 데이터 함수를 `src/mcp_openstack_ops/functions.py`에 추가합니다.

```python
async def get_your_custom_data(target_resource: str = None) -> List[Dict[str, Any]]:
    """Your custom data retrieval function."""
    # Example implementation - adapt to your OpenStack service
    conn = get_openstack_connection()
    results = []

    try:
        # Example: Custom query using OpenStack SDK
        resources = conn.your_service.list_resources(
            filters={'name': target_resource} if target_resource else {}
        )

        for resource in resources:
            results.append({
                'name': resource.name,
                'id': resource.id,
                'status': resource.status,
                'created_at': resource.created_at,
                # Add your custom fields
            })

    except Exception as e:
        logger.error(f"Failed to get custom data: {e}")
        return []

    return results
```

### 2. MCP 도구 파일 만들기

새 파일 `src/mcp_openstack_ops/tools/get_your_custom_analysis.py`를 만듭니다.

```python
"""Tool implementation for get_your_custom_analysis."""

import json
from datetime import datetime
from typing import Optional
from ..functions import get_your_custom_data  # Import your helper function
from ..mcp_main import (
    logger,
    mcp,
)

@mcp.tool()
async def get_your_custom_analysis(limit: int = 50, target_name: Optional[str] = None) -> str:
    """
    [Tool Purpose]: Brief description of what your tool does

    [Exact Functionality]:
    - Feature 1: Data aggregation and analysis
    - Feature 2: Resource monitoring and insights
    - Feature 3: Performance metrics and reporting

    [Required Use Cases]:
    - When user asks "your specific analysis request"
    - Your business-specific monitoring needs

    Args:
        limit: Maximum results (1-100)
        target_name: Target resource/service name

    Returns:
        Formatted analysis results
    """
    try:
        limit = max(1, min(limit, 100))  # Always validate input

        logger.info(f"Getting custom analysis, limit: {limit}, target: {target_name}")

        results = await get_your_custom_data(target_resource=target_name)

        if not results:
            return f"No custom analysis data found" + (f" for '{target_name}'" if target_name else "")

        # Apply limit
        results = results[:limit]

        # Format results as table
        table_data = []
        for item in results:
            table_data.append({
                'Name': item.get('name', 'N/A'),
                'ID': item.get('id', 'N/A'),
                'Status': item.get('status', 'N/A'),
                'Created': item.get('created_at', 'N/A'),
            })

        # Return formatted JSON
        return json.dumps({
            'title': f'Custom Analysis (Top {len(results)})',
            'data': table_data,
            'total_count': len(results),
            'timestamp': datetime.now().isoformat()
        }, indent=2)

    except Exception as e:
        logger.error(f"Failed to get custom analysis: {e}")
        return f"Error: {str(e)}"
```

### 3. 변경 작업용 도구(선택)

도구가 변경 작업을 한다면 대신 `@conditional_tool` 데코레이터를 쓰세요.

```python
"""Tool implementation for set_your_custom_resource."""

from ..mcp_main import (
    conditional_tool,  # Use this instead of @mcp.tool()
    handle_operation_result,
    logger,
)
from ..functions import set_your_custom_resource

@conditional_tool  # Only registers when ALLOW_MODIFY_OPERATIONS=true
async def set_your_custom_resource(resource_name: str, action: str) -> str:
    """
    Manage your custom OpenStack resources.

    Use when user requests custom resource management.
    """
    try:
        result = set_your_custom_resource(resource_name, action)

        return handle_operation_result(
            result=result,
            operation_name="Custom Resource Management",
            details={
                'Resource': resource_name,
                'Action': action
            }
        )

    except Exception as e:
        logger.error(f"Custom resource operation failed: {e}")
        return f"Error: {str(e)}"
```

### 4. 프롬프트 템플릿 갱신(권장)

자연어 인식이 잘 되도록 `src/mcp_openstack_ops/prompt_template.md`에 도구 설명을
추가하세요.

```markdown
### **Your Custom Analysis Tool**

### X. **get_your_custom_analysis**
**Purpose**: Brief description of what your tool does
**Usage**: "Show me your custom analysis" or "Get custom analysis for resource_name"
**Features**: Data aggregation, resource monitoring, performance metrics
**Optional**: `target_name` parameter for specific resource analysis
```

### 5. 도구 테스트

```bash
# Local testing
./scripts/run-mcp-inspector-local.sh

# Or with Docker
docker compose up -d
docker compose logs -f mcp-server

# Test with natural language:
# "Show me your custom analysis"
# "Get custom analysis for target_name"
```

도구가 새 OpenStack 서비스를 호출하거나 기존 도구의 동작을 바꾸면, `AGENTS.md`에
설명된 대로 README의 [CLI와 도구 매핑](../README.ko.md#-openstack-cli와-mcp-도구-매핑)을
갱신하세요.

### 도구 등록 방식

MCP 서버는 도구를 자동으로 찾아 등록합니다. `src/mcp_openstack_ops/tools/`에 새 파일을
만들면 `tools/__init__.py`의 `register_all_tools()` 함수가 자동으로 등록하므로, 따로
import를 추가할 필요가 없습니다.

### 안전 장치

- **읽기 전용 도구**: `@mcp.tool()`을 쓰며 항상 사용 가능합니다.
- **변경 도구**: `@conditional_tool`을 쓰며 `ALLOW_MODIFY_OPERATIONS=true`일 때만 사용 가능합니다.
- **연결**: OpenStack API에 접근할 때는 항상 `get_openstack_connection()`을 쓰세요.
- **프로젝트 격리**: 모든 작업은 자동으로 `OS_PROJECT_NAME` 범위로 제한됩니다.

## 기여

1. 저장소를 fork합니다.
2. 기능 브랜치를 만듭니다(`git checkout -b feature/amazing-feature`).
3. 변경 사항을 커밋합니다(`git commit -m 'Add some amazing feature'`).
4. 브랜치를 push합니다(`git push origin feature/amazing-feature`).
5. Pull Request를 엽니다.
