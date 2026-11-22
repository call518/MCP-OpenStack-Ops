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
클러스터 전체 상태를 보여줘
프로젝트의 모든 인스턴스를 나열해줘
SHUTOFF 상태인 인스턴스를 찾아줘
모든 네트워크와 서브넷을 보여줘
모든 볼륨과 상태를 나열해줘
내 프로젝트에 할당된 vCPU와 메모리, 남은 쿼터를 보여줘
최근 1시간 동안 web-01의 CPU 사용량을 보여줘
이름에 'test'가 들어간 인스턴스를 모두 중지해줘
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
"클러스터 전체 상태를 보여줘"
"클러스터 종합 보고서를 만들어줘"
"현재 인프라 상태는 어때?"
"리소스 할당과 용량을 포함한 클러스터 개요를 보여줘"
```

**사용 도구:** `get_service_status()`, `get_resource_monitoring()`

### 🖥️ 인스턴스 관리

```
"프로젝트의 모든 인스턴스를 나열해줘"
"인스턴스 web-server-01의 상세 정보를 보여줘"
"flavor m1.small, 이미지 ubuntu-20.04로 test-vm이라는 인스턴스를 만들어줘"
"인스턴스 web-server-01을 시작해줘"
"이름에 'test'가 들어간 인스턴스를 모두 중지해줘"
"인스턴스 old-server를 삭제해줘"
```

**사용 도구:** `get_instance_details()`, `set_instance()`, `search_instances()`

### 🌐 네트워크 작업

```
"모든 네트워크와 서브넷을 보여줘"
"floating IP와 할당 상태를 나열해줘"
"서브넷 192.168.100.0/24를 가진 private-net 네트워크를 만들어줘"
"floating IP 203.0.113.10을 인스턴스 web-server에 연결해줘"
"네트워크 토폴로지를 보여줘"
```

**사용 도구:** `get_network_details()`, `get_floating_ips()`, `set_networks()`, `set_floating_ip()`

### 💾 스토리지 관리

```
"모든 볼륨과 상태를 나열해줘"
"볼륨 data-volume-01의 상세 정보를 보여줘"
"backup-storage라는 50GB 볼륨을 만들어줘"
"볼륨 data-vol을 인스턴스 web-server-01에 연결해줘"
"볼륨 database-storage의 스냅샷을 만들어줘"
```

**사용 도구:** `get_volume_list()`, `set_volume()`, `set_snapshot()`

### 🗂️ cross-project 조회(고급, 선택 기능)

기본으로 꺼져 있습니다. 이 요청에는 `ALLOW_CROSS_PROJECT_READ=true`와 OpenStack
권한이 필요합니다. [cross-project 조회 가이드](cross-project-guide.ko.md)를 참고하세요.

```
"클라우드의 모든 프로젝트를 나열해줘"
"프로젝트별 VM을 표로 보여줘"
"SHUTOFF 인스턴스가 있는 프로젝트는 어디야?"
"모든 프로젝트에서 이름이 'web'인 인스턴스를 찾아줘"
"모든 프로젝트의 볼륨을 크기, 상태와 함께 나열해줘"
"볼륨 스토리지를 가장 많이 쓰는 프로젝트는 어디야?"
"모든 프로젝트의 볼륨 스냅샷을 보여줘"
"프로젝트마다 인스턴스와 볼륨이 몇 개야?"
"'dev' 프로젝트의 리소스 수를 보여줘"
"모든 프로젝트의 네트워크와 floating IP를 나열해줘"
"모든 프로젝트의 볼륨 백업과 서버 그룹을 보여줘"
"모든 프로젝트의 로드밸런서와 private 이미지를 나열해줘"
```

**사용 도구:** `get_project_details(all_projects=true)`, `get_instance_details(all_projects=true)`, `get_instances_by_status(all_projects=true)`, `search_instances(all_projects=true)`, `get_volume_list(all_projects=true)`, `get_volume_snapshots(all_projects=true)`, `get_network_details(all_projects=true)`, `get_routers(all_projects=true)`, `get_security_groups(all_projects=true)`, `get_floating_ips(all_projects=true)`, `get_volume_backups(all_projects=true)`, `get_volume_groups(all_projects=true)`, `get_server_groups(all_projects=true)`, `get_image_detail_list(all_projects=true)`, `get_heat_stacks(all_projects=true)`, `get_load_balancer_list(all_projects=true)`

**흐름:** 사용자가 전체 프로젝트나 다른 프로젝트에 대해 물을 때만 `all_projects=true`를 넘깁니다. 행은 `project_name`(없으면 `project_id`)으로 묶고, `get_instance_details`에는 `include_all=true`나 페이지 처리를 써서 어떤 프로젝트도 잘리지 않게 합니다. `scope.projects_in_result`를 보고하고, `scope.warning`이 있으면 결과가 현재 프로젝트만 다룰 수 있다고 알립니다. "Cross-project reads are disabled" 오류는 운영자가 `ALLOW_CROSS_PROJECT_READ=true`를 설정하지 않았다는 뜻이고, 정책 거부 오류는 자격 증명에 권한이 없다는 뜻입니다. 이런 요청을 `all_projects` 없이 다시 시도한 결과를 클라우드 전체 결과처럼 제시하지 마세요. 한 프로젝트의 리소스 수는 그 프로젝트의 이름이나 ID와 `all_projects=true`로 `get_project_details`를 호출해 얻습니다. 이름이 여러 프로젝트와 일치하면 ID로 다시 호출합니다.

### 🖼️ 이미지 작업

```
"사용 가능한 이미지를 나열해줘"
"Ubuntu 이미지의 상세 정보를 보여줘"
"인스턴스 web-server-01로 custom-web-image라는 이미지를 만들어줘"
"이미지 old-snapshot-image를 삭제해줘"
```

**사용 도구:** `get_image_detail_list()`, `set_image()`

### 👥 Identity와 접근 관리

```
"프로젝트 상세 정보와 쿼터를 보여줘"
"현재 프로젝트의 사용자를 나열해줘"
"역할 할당을 보여줘"
"my-key라는 키페어를 만들어줘"
```

**사용 도구:** `get_project_details()`, `get_user_list()`, `get_role_assignments()`, `set_keypair()`

### 🔥 오케스트레이션(Heat)

```
"모든 Heat 스택을 나열해줘"
"production-stack의 스택 상태를 보여줘"
"템플릿과 파라미터로 스택을 만들어줘"
"스택 old-deployment를 삭제해줘"
```

**사용 도구:** `get_heat_stacks()`, `set_heat_stack()`

### ⚖️ 로드밸런서

```
"로드밸런서 상태를 보여줘"
"모든 로드밸런서와 리스너를 나열해줘"
"웹 계층용 로드밸런서를 만들어줘"
"헬스 모니터 상태를 보여줘"
```

**사용 도구:** `get_load_balancer_details()`, `set_load_balancer()`, `get_load_balancer_listeners()`

### 🔐 Barbican 시크릿과 TLS 리스너

```
"Barbican 시크릿을 나열하고 web-tls를 쓰는 서비스를 보여줘"
"192.168.35.169용 자체 서명 TLS 시크릿 web-tls를 만들어줘"
"web-lb에 인증서 web-tls를 쓰는 443 포트 TERMINATED_HTTPS 리스너를 추가해줘"
"시크릿 web-tls의 ACL을 보여줘"
```

**사용 도구:** `get_secrets()`, `set_secret()`, `set_load_balancer_listener()`, `get_secret_acl()`

시크릿 payload는 이 도구들을 거치지 않습니다. 사용자 인증서는 MCP 밖에서
등록합니다. [Barbican과 TLS 가이드](barbican-tls-guide.ko.md)를 참고하세요.

### 🔍 고급 검색과 필터링

```
"이름에 'web'이 들어간 인스턴스를 모두 찾아줘"
"실행 중인 인스턴스를 검색해줘"
"최근 7일 동안 만든 인스턴스를 보여줘"
"100GB보다 큰 볼륨을 찾아줘"
```

**사용 도구:** `search_instances()`, `get_instances_by_status()`

### 📊 리소스 할당과 용량

```
"하이퍼바이저별 리소스 할당과 용량을 보여줘"
"내 프로젝트에 vCPU와 RAM이 얼마나 할당되어 있어?"
"쿼터 사용량과 한도를 보여줘"
"스토리지 용량 통계를 보여줘"
"내 프로젝트에 할당된 vCPU와 메모리, 남은 쿼터를 보여줘"
```

**사용 도구:** `get_resource_monitoring()`, `get_quota()`, `get_usage_statistics()`

결과는 할당(allocation), 쿼터, 용량이며 실제 측정한 사용률이 아닙니다.

### 📡 텔레메트리 지표(Gnocchi)

```
"web-01의 CPU와 메모리 사용량을 모니터링해줘"
"web-01의 실제 CPU 사용률 추이를 보여줘"
"서버 web-01에 대해 수집된 텔레메트리 지표를 보여줘"
"2026-11-08T00:00:00 이후 web-01의 메모리 측정값을 1시간 단위로 리샘플링해서 보여줘"
"내 프로젝트의 모든 Gnocchi 지표를 나열해줘"
"archive policy와 지원되는 aggregation 방식을 보여줘"
"Gnocchi 측정값 처리가 밀려 있어?"
"web-01의 최근 vcpus 측정값 10개를 보여줘"
"내 프로젝트 전체 인스턴스의 평균 CPU 사용량은 얼마야?"
"CPU 사용량 상위 5개 인스턴스를 보여줘"
"flavor별 평균 메모리 사용량을 보여줘"
"내 인스턴스들의 flavor 메모리 대비 memory.usage 비율을 보여줘"
```

**사용 도구:** `get_gnocchi_resources()`, `get_gnocchi_metrics()`, `get_gnocchi_measures()`, `get_gnocchi_aggregates()`, `get_gnocchi_service_info()`

**흐름:** `get_instance_by_name()`으로 서버 UUID를 찾고, `get_gnocchi_resources(resource_type="instance", resource_id=UUID)`로 지표 이름을 확인한 뒤 `get_gnocchi_measures(metric=name, resource_id=UUID)`를 호출합니다. granularity와 aggregation은 지표의 archive policy에 있는 값을 씁니다. `cpu`는 누적 나노초 값이므로 `aggregation="rate:mean"`으로 요청하고, 사용률 비율을 구하려면 granularity × 10^9 × vCPU 수로 나눕니다. 없는 지표는 수집되지 않았다고 보고하고, 값을 추정하지 않습니다.

**여러 리소스 흐름:** `get_gnocchi_aggregates`는 한 번에 한 가지 모드로만 씁니다. 단순 모드 예: 프로젝트 평균 CPU → `metric="cpu", aggregation="rate:mean", reaggregation="mean"`; CPU 상위 5개 → `metric="cpu", aggregation="rate:mean", top=5`; flavor별 메모리 → `metric="memory.usage", reaggregation="mean", groupby="flavor_name"`. 표현식 모드(`operations`만 사용)는 `(/ (metric memory.usage mean) (metric memory mean))` 같은 계산에만 쓰고, 지표 UUID가 아니라 지표 이름을 씁니다. 시리즈의 `resource_name`을 보고하고, 결과가 현재 프로젝트만 다룬다고 밝힙니다. "Metric ... does not exist" 오류는 현재 프로젝트에 맞는 리소스가 없다는 뜻일 수도 있습니다.

### 🚨 알람(Aodh)

```
"내 프로젝트의 알람을 나열해줘"
"web-01의 memory.usage가 1500 MB를 넘으면 울리는 알람을 만들어줘"
"web-01의 CPU가 80%를 넘으면 울리는 알람을 만들어줘"
"알람 mem-high의 상세 정보와 현재 상태를 보여줘"
"알람 mem-high를 삭제해줘"
"web-01의 vcpus 지표에 임계값 알람을 만들어줘"
```

**사용 도구:** `set_alarms()`(`ALLOW_MODIFY_OPERATIONS=true` 필요), `get_gnocchi_metrics()`

**흐름:** `set_alarms(action="create")` 전에 `get_gnocchi_metrics(resource_id=UUID)`로 그 리소스에 지표가 있는지 확인합니다. Aodh는 존재하지 않는 리소스나 기본값 `cpu_util`처럼 수집되지 않는 지표도 받아 주며, 그런 알람은 계속 `insufficient data` 상태로 남습니다. `cpu_util` 기본값에 기대지 마세요. CPU 백분율 알람에는 `metric="cpu"`, `aggregation_method="rate:mean"`, `threshold = percent / 100 × granularity × 10^9 × vCPUs`를 넘깁니다(vCPU 1개, 300초 기준 80%는 2.4e11). 새 알람은 평가될 때까지 `insufficient data`이며 몇 분 걸릴 수 있습니다. 짐작한 상태가 아니라 반환된 상태를 보고하세요.

### 🛠️ 문제 해결

```
"OpenStack 서비스 상태를 확인해줘"
"server-01의 인스턴스 이벤트를 보여줘"
"하이퍼바이저 상세 정보를 보여줘"
"네트워크 agent 상태를 보여줘"
```

**사용 도구:** `get_service_status()`, `get_server_events()`, `get_hypervisor_details()`

### 🔒 보안 작업

```
"보안 그룹과 규칙을 나열해줘"
"키페어 정보를 보여줘"
"floating IP 연결 상태를 보여줘"
"현재 프로젝트의 역할 할당을 확인해줘"
```

**사용 도구:** `get_security_groups()`, `get_keypair_list()`, `get_floating_ips()`, `get_role_assignments()`

### 📈 성능과 최적화

```
"할당된 vCPU와 RAM 기준 상위 10개 인스턴스를 보여줘"
"flavor 할당 통계를 보여줘"
"네트워크 리소스 수와 상태를 모니터링해줘"
"web-01의 디스크 I/O 텔레메트리를 확인해줘"
```

**사용 도구:** `get_instance_details()`, `get_resource_monitoring()`(할당), `get_gnocchi_measures()`(측정된 I/O, 수집되는 경우)

### 🎛️ 일괄 작업

```
"'development' 태그가 붙은 인스턴스를 모두 중지해줘"
"vol-01, vol-02, vol-03이라는 볼륨 여러 개를 만들어줘"
"30일보다 오래된 스냅샷을 모두 삭제해줘"
"모든 인스턴스에 새 보안 그룹을 적용해줘"
```

**사용 도구:** 필터 매개변수와 함께 여러 도구를 조합

### 🧠 고급 요청 패턴

#### 복잡한 요청을 위한 여러 도구 조합

```
"인프라 전체 개요를 보여줘" →
1. get_service_status() (service health)
2. get_resource_monitoring() (allocation and capacity)
3. get_instance_details() (compute resources)
4. get_network_details() (network topology)
5. get_volume_list() (storage resources)
6. get_project_details() (quotas & usage)
```

```
"성능 문제를 진단해줘" →
1. get_instance_details() (instance status & specs)
2. get_gnocchi_measures() (measured load, if collected)
3. get_resource_monitoring() + get_hypervisor_details() (allocation and host capacity)
4. get_service_status() (service health)
```

```
"보안 감사 보고서를 만들어줘" →
1. get_security_groups() (security rules)
2. get_floating_ips() (external access points)
3. get_keypair_list() (SSH access keys)
4. get_role_assignments() (user permissions)
5. get_user_list() (project members)
```

#### 일상 언어를 도구로 옮기는 예

- **"전부 보여줘"** → 여러 도구를 써서 클러스터 전체 보고서 작성
- **"뭐가 고장 났어?"** → 서비스 상태 + 리소스 모니터링 + 인스턴스 상태 점검
- **"새 VM을 만들 수 있어?"** → 프로젝트 쿼터 + 사용 가능한 flavor + 네트워크 선택지
- **"내 인스턴스가 왜 느려?"** → 인스턴스 상세 + 리소스 모니터링 + 하이퍼바이저 상태
- **"네트워크 연결 상태를 보여줘"** → 네트워크 상세 + 보안 그룹 + floating IP + 라우터
- **"보안 그룹 web에서 TCP 80 포트를 외부에 열어줘"** → `set_security_group_rules(action="create", security_group="web", protocol="tcp", port_range_min=80, port_range_max=80, remote_ip_prefix="0.0.0.0/0")`

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
- **`set_instance`**: 필터(name_contains, status, flavor_contains, image_contains)를 지원하는 일괄 수명 주기 관리. 지정한 필터는 모두 일치해야 함. 서버의 `INSTANCE_FILTER_MAX_MATCHES`(기본값 100, [설정](configuration.ko.md#환경-변수) 참고)보다 많이 일치하면 어떤 인스턴스에도 작업하지 않고 거부하므로 필터를 좁힐 것
- **`set_volume`**: 이름 목록에 대한 일괄 볼륨 작업. 필터 파라미터는 없음
- **`set_image`**: 이름 목록에 대한 일괄 이미지 관리. 필터 파라미터는 없음
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

- `get_instance_details`는 기본적으로 요청당 인스턴스 50개, 최대 서버의 `LIST_MAX_LIMIT`(기본값 100)개를 반환합니다.
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
