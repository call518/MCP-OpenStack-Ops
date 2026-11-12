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
[분야별 요청 예시](#분야별-요청-예시)에 있습니다.

## 분야별 요청 예시

아래 요청을 그대로 클라이언트에 복사해 써 보세요. 각 그룹 아래에 적은 도구는
클라이언트가 보통 호출하는 도구입니다.

### 🎯 클러스터 개요와 상태

```
"Show me the overall cluster status"
"Create a comprehensive cluster report"
"What's the current infrastructure health?"
"Give me a cluster overview with resource allocation and capacity"
```

**사용 도구:** `get_service_status()`, `get_resource_monitoring()`, `get_service_status()`

### 🖥️ 인스턴스 관리

```
"List all instances in the project"
"Show details for instance web-server-01"
"Create an instance named test-vm with flavor m1.small and image ubuntu-20.04"
"Start instance web-server-01"
"Stop all instances with name containing 'test'"
"Delete instance old-server"
```

**사용 도구:** `get_instance_details()`, `set_instance()`, `search_instances()`

### 🌐 네트워크 작업

```
"Show all networks and their subnets"
"List floating IPs and their assignments"
"Create a network named private-net with subnet 192.168.100.0/24"
"Associate floating IP 203.0.113.10 to instance web-server"
"Show network topology"
```

**사용 도구:** `get_network_details()`, `get_floating_ips()`, `set_networks()`, `set_floating_ip()`

### 💾 스토리지 관리

```
"List all volumes and their status"
"Show volume details for data-volume-01"
"Create a 50GB volume named backup-storage"
"Attach volume data-vol to instance web-server-01"
"Create a snapshot of volume database-storage"
```

**사용 도구:** `get_volume_list()`, `set_volume()`, `set_snapshot()`

### 🗂️ cross-project 조회(선택 기능)

```
"List all projects in the cloud"
"Show a table of VMs per project"
"Which projects have SHUTOFF instances?"
"Find instances named 'web' in every project"
"List volumes across all projects with size and status"
"Which project uses the most volume storage?"
"Show volume snapshots in every project"
"How many instances and volumes does each project have?"
```

**사용 도구:** `get_project_details(all_projects=true)`, `get_instance_details(all_projects=true)`, `get_instances_by_status(all_projects=true)`, `search_instances(all_projects=true)`, `get_volume_list(all_projects=true)`, `get_volume_snapshots(all_projects=true)`

**흐름:** 사용자가 전체 프로젝트나 다른 프로젝트에 대해 물을 때만 `all_projects=true`를 넘깁니다. 행은 `project_name`(없으면 `project_id`)으로 묶고, `get_instance_details`에는 `include_all=true`나 페이지 처리를 써서 어떤 프로젝트도 잘리지 않게 합니다. `scope.projects_in_result`를 보고하고, `scope.warning`이 있으면 결과가 현재 프로젝트만 다룰 수 있다고 알립니다. "Cross-project reads are disabled" 오류는 운영자가 `ALLOW_CROSS_PROJECT_READ=true`를 설정하지 않았다는 뜻이고, 정책 거부 오류는 자격 증명에 권한이 없다는 뜻입니다. 이런 요청을 `all_projects` 없이 다시 시도한 결과를 클라우드 전체 결과처럼 제시하지 마세요. 프로젝트별 리소스 개수는 `get_project_details`가 아니라 인스턴스·볼륨 목록에서 나옵니다.

### 🖼️ 이미지 작업

```
"List available images"
"Show details for Ubuntu images"
"Create an image from instance web-server-01 named custom-web-image"
"Delete image old-snapshot-image"
```

**사용 도구:** `get_image_detail_list()`, `set_image()`

### 👥 ID와 접근 관리

```
"Show project details and quotas"
"List users in current project"
"Show role assignments"
"Create keypair named my-key"
```

**사용 도구:** `get_project_details()`, `get_user_list()`, `get_role_assignments()`, `set_keypair()`

### 🔥 오케스트레이션(Heat)

```
"List all Heat stacks"
"Show stack status for production-stack"
"Create stack from template with parameters"
"Delete stack old-deployment"
```

**사용 도구:** `get_heat_stacks()`, `set_heat_stack()`

### ⚖️ 로드밸런서

```
"Show load balancer status"
"List all load balancers and listeners"
"Create load balancer for web tier"
"Show health monitor status"
```

**사용 도구:** `get_load_balancer_details()`, `set_load_balancer()`, `get_load_balancer_listeners()`

### 🔍 고급 검색과 필터링

```
"Find all instances with 'web' in the name"
"Search for running instances"
"Show instances created in the last 7 days"
"Find volumes larger than 100GB"
```

**사용 도구:** `search_instances()`, `get_instances_by_status()`

### 📊 리소스 할당과 용량

```
"Show resource allocation and capacity by hypervisor"
"How many vCPUs and how much RAM are allocated in my project?"
"Show quota usage and limits"
"Display storage capacity statistics"
"Show the vCPUs and memory allocated to my project and the remaining quota"
```

**사용 도구:** `get_resource_monitoring()`, `get_quota()`, `get_usage_statistics()`

결과는 할당량, 쿼터, 용량이며 실제 측정한 사용률이 아닙니다.

### 📡 텔레메트리 지표(Gnocchi)

```
"Monitor CPU and memory usage of web-01"
"Show the actual CPU utilization trend of web-01"
"Show the telemetry metrics collected for server web-01"
"Show memory measures of web-01 since 2026-11-08T00:00:00, resampled hourly"
"List all Gnocchi metrics in my project"
"Show the archive policies and supported aggregation methods"
"Is Gnocchi measure processing backlogged?"
"Show the latest 10 vcpus measures of web-01"
"What is the average CPU usage across all instances in my project?"
"Show the top 5 instances by CPU usage"
"Show mean memory usage per flavor"
"Show the memory.usage to flavor memory ratio across my instances"
```

**사용 도구:** `get_gnocchi_resources()`, `get_gnocchi_metrics()`, `get_gnocchi_measures()`, `get_gnocchi_aggregates()`, `get_gnocchi_service_info()`

**흐름:** `get_instance_by_name()`으로 서버 UUID를 찾고, `get_gnocchi_resources(resource_type="instance", resource_id=UUID)`로 지표 이름을 확인한 뒤 `get_gnocchi_measures(metric=name, resource_id=UUID)`를 호출합니다. granularity와 aggregation은 지표의 archive policy에 있는 값을 씁니다. `cpu`는 누적 나노초 값이므로 `aggregation="rate:mean"`으로 요청하고, 사용률 비율을 구하려면 granularity × 10^9 × vCPU 수로 나눕니다. 없는 지표는 수집되지 않았다고 보고하고, 값을 추정하지 않습니다.

**여러 리소스 흐름:** `get_gnocchi_aggregates`는 한 번에 한 가지 모드로만 씁니다. 단순 모드 예: 프로젝트 평균 CPU → `metric="cpu", aggregation="rate:mean", reaggregation="mean"`; CPU 상위 5개 → `metric="cpu", aggregation="rate:mean", top=5`; flavor별 메모리 → `metric="memory.usage", reaggregation="mean", groupby="flavor_name"`. 표현식 모드(`operations`만 사용)는 `(/ (metric memory.usage mean) (metric memory mean))` 같은 계산에만 쓰고, 지표 UUID가 아니라 지표 이름을 씁니다. 시리즈의 `resource_name`을 보고하고, 결과가 현재 프로젝트만 다룬다고 밝힙니다. "Metric ... does not exist" 오류는 현재 프로젝트에 맞는 리소스가 없다는 뜻일 수도 있습니다.

### 🚨 알람(Aodh)

```
"List alarms in my project"
"Create an alarm when web-01 memory.usage exceeds 1500 MB"
"Create an alarm when web-01 CPU exceeds 80%"
"Show details and current state of alarm mem-high"
"Delete alarm mem-high"
"Create a threshold alarm on the vcpus metric of web-01"
```

**사용 도구:** `set_alarms()`(`ALLOW_MODIFY_OPERATIONS=true` 필요), `get_gnocchi_metrics()`

**흐름:** `set_alarms(action="create")` 전에 `get_gnocchi_metrics(resource_id=UUID)`로 그 리소스에 지표가 있는지 확인합니다. Aodh는 존재하지 않는 리소스나 기본값 `cpu_util`처럼 수집되지 않는 지표도 받아 주며, 그런 알람은 계속 `insufficient data` 상태로 남습니다. `cpu_util` 기본값에 기대지 마세요. CPU 백분율 알람에는 `metric="cpu"`, `aggregation_method="rate:mean"`, `threshold = percent / 100 × granularity × 10^9 × vCPUs`를 넘깁니다(vCPU 1개, 300초 기준 80%는 2.4e11). 새 알람은 평가될 때까지 `insufficient data`이며 몇 분 걸릴 수 있습니다. 짐작한 상태가 아니라 반환된 상태를 보고하세요.

### 🛠️ 문제 해결

```
"Check OpenStack service status"
"Show instance events for server-01"
"Display hypervisor details"
"Show network agent status"
```

**사용 도구:** `get_service_status()`, `get_server_events()`, `get_hypervisor_details()`

### 🔒 보안 작업

```
"List security groups and rules"
"Show keypair information"
"Display floating IP associations"
"Check role assignments for current project"
```

**사용 도구:** `get_security_groups()`, `get_keypair_list()`, `get_floating_ips()`, `get_role_assignments()`

### 📈 성능과 최적화

```
"Show top 10 instances by allocated vCPU and RAM"
"Display flavor allocation statistics"
"Monitor network resource counts and status"
"Check disk I/O telemetry of web-01"
```

**사용 도구:** `get_instance_details()`, `get_resource_monitoring()`(할당), `get_gnocchi_measures()`(측정된 I/O, 수집되는 경우)

### 🎛️ 일괄 작업

```
"Stop all instances with tag 'development'"
"Create multiple volumes with names vol-01, vol-02, vol-03"
"Delete all snapshots older than 30 days"
"Update all instances with new security group"
```

**사용 도구:** 필터 매개변수와 함께 여러 도구를 조합

### 🧠 고급 요청 패턴

#### 복잡한 요청을 위한 여러 도구 조합

```
"Show complete infrastructure overview" →
1. get_service_status() (service health)
2. get_resource_monitoring() (allocation and capacity)
3. get_instance_details() (compute resources)
4. get_network_details() (network topology)
5. get_volume_list() (storage resources)
6. get_project_details() (quotas & usage)
```

```
"Troubleshoot performance issues" →
1. get_instance_details() (instance status & specs)
2. get_gnocchi_measures() (measured load, if collected)
3. get_resource_monitoring() + get_hypervisor_details() (allocation and host capacity)
4. get_service_status() (service health)
```

```
"Security audit report" →
1. get_security_groups() (security rules)
2. get_floating_ips() (external access points)
3. get_keypair_list() (SSH access keys)
4. get_role_assignments() (user permissions)
5. get_user_list() (project members)
```

#### 일상 언어를 도구로 옮기는 예

- **"Show me everything"** → 여러 도구를 써서 클러스터 전체 보고서 작성
- **"What's broken?"** → 서비스 상태 + 리소스 모니터링 + 인스턴스 상태 점검
- **"Can I create a new VM?"** → 프로젝트 쿼터 + 사용 가능한 flavor + 네트워크 선택지
- **"Why is my instance slow?"** → 인스턴스 상세 + 리소스 모니터링 + 하이퍼바이저 상태
- **"Show network connectivity"** → 네트워크 상세 + 보안 그룹 + floating IP + 라우터
- **"Open public TCP port 80 on security group web"** → `set_security_group_rules(action="create", security_group="web", protocol="tcp", port_range_min=80, port_range_max=80, remote_ip_prefix="0.0.0.0/0")`

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
