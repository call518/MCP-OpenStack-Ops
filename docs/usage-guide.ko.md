[English](usage-guide.md) | **Korean**

# 사용 가이드

이 가이드는 도구를 실제로 어떻게 쓰는지 보여 줍니다. 요청 예시, 일괄·필터 작업,
작업 후 상태, 대규모 프로젝트의 페이지 처리를 다룹니다. 모든 도구와 대응하는
OpenStack CLI 명령은 README의
[CLI와 도구 매핑](../README.ko.md#-openstack-cli와-mcp-도구-매핑)을 참고하세요.

## 요청 예시

일상 언어로 물어보면 클라이언트가 알맞은 도구를 고릅니다. 예를 들면 다음과
같습니다.

```text
Show me the overall cluster status
List all instances in the project
Find instances in SHUTOFF state
Show all networks and their subnets
List all volumes and their status
Show the vCPUs and memory allocated to my project and the remaining quota
Show CPU usage of web-01 over the last hour
Stop all instances with name containing 'test'
```

리소스를 만들거나 바꾸거나 지우는 요청은 변경 도구가 켜져 있을 때만
(`ALLOW_MODIFY_OPERATIONS=true`) 동작합니다. CPU 사용량 같은 텔레메트리 요청에는
클라우드에 Ceilometer와 Gnocchi가 있어야 합니다.

분야별로 정리하고 요청마다 쓰이는 도구를 표시한 더 많은 예시는
[Example Queries & Usage Patterns](../src/mcp_openstack_ops/prompt_template.md#7-example-queries--usage-patterns)에
있습니다(영문).

- 🎯 클러스터 개요와 상태 조회
- 🖥️ 인스턴스 관리 작업
- 🌐 네트워크 설정 작업
- 💾 스토리지 관리 작업
- 🔥 Heat orchestration 예시
- ⚖️ 로드밸런서 작업
- 🔍 고급 검색 패턴
- 📊 모니터링과 문제 해결
- 🧠 여러 도구를 조합하는 복잡한 요청

## 일괄 작업과 필터 기반 대상 지정

여러 관리 도구는 이름 목록이나 필터 조건으로 많은 리소스를 한 번의 호출로
처리합니다.

```bash
# One call per instance:
set_instance("vm1", "stop")
set_instance("vm2", "stop")

# One call for every instance whose name contains "test":
set_instance(action="stop", name_contains="test")
```

**일괄 작업과 필터를 지원하는 도구:**
- **`set_instance`**: 필터(name_contains, status, flavor_contains, image_contains)를 지원하는 일괄 수명 주기 관리
- **`set_volume`**: 필터(name_contains, status, 크기 필터)를 지원하는 일괄 볼륨 작업
- **`set_image`**: 필터(name_contains, status)를 지원하는 일괄 이미지 관리
- **`set_networks`**: 필터(name_contains, status)를 지원하는 일괄 네트워크 작업
- **`set_keypair`**: 필터(name_contains)를 지원하는 일괄 키페어 관리
- **`set_snapshot`**: 필터(name_contains, status)를 지원하는 일괄 스냅샷 작업

**입력 형식:**
```python
# Single resource
resource_names="vm1"

# Multiple resources (comma-separated)
resource_names="vm1,vm2,vm3"

# JSON array format
resource_names='["vm1", "vm2", "vm3"]'

# Filter-based (automatic target identification)
name_contains="test", status="ACTIVE"
```

## 작업 후 상태

관리 작업은 리소스별 결과와 작업 후 다시 읽은 상태를 보고합니다.

```bash
✅ Bulk Instance Management - Action: stop
📊 Total instances: 3
✅ Successes: 2
❌ Failures: 1

Post-Action Status:
🟢 test-vm-1: SHUTOFF
🟢 test-vm-2: SHUTOFF
🔴 test-vm-3: ERROR
```

많은 OpenStack 작업은 비동기입니다. 요청이 접수되었다고 작업이 끝난 것은 아닙니다.
중요한 경우에는 조회 도구로 최종 상태를 확인하세요.

## 인스턴스 조회

`get_instance`는 이름, ID, 상태, 자유 검색으로 찾는 기능을 하나의 도구로 묶고, 페이지
처리와 요약·상세 출력을 제공합니다. 예: `get_instance(names="vm1,vm2")`. 전용 도구인
`get_instance_details`, `get_instance_by_name`, `get_instances_by_status`,
`search_instances`도 함께 제공됩니다.

## 대규모 프로젝트와 페이지 처리

인스턴스 목록은 페이지 단위로 나뉘므로 큰 프로젝트에서도 수천 개의 인스턴스를 한
번에 돌려주지 않습니다.

- `get_instance_details`는 기본적으로 요청당 인스턴스 50개, 최대 200개를 반환합니다.
- `limit`과 `offset`으로 결과를 넘겨 봅니다.
- `include_all=True`는 한도를 무시합니다. 큰 프로젝트에서는 주의해서 쓰세요.

```bash
# Browse a large project page by page
get_instance_details(limit=50, offset=0)     # First 50 instances
get_instance_details(limit=50, offset=50)    # Next 50 instances

# All instances (use with caution)
get_instance_details(include_all=True)

# Search with pagination
search_instances("web", "name", limit=20, offset=0, case_sensitive=False)
```
