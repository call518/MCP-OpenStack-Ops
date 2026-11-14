[English](cross-project-guide.md) | **Korean**

# cross-project 조회 (고급)

**대부분의 사용자에게는 이 가이드가 필요 없습니다.** 기본적으로 모든 도구는 서버에
설정된 OpenStack 프로젝트 하나 안에서만 동작하며, 여기 나오는 설정은 하지 않아도
됩니다. cross-project 조회는 OpenStack CLI의 `--all-projects`처럼 여러 프로젝트를
한 번에 봐야 하는 관리자와 운영자를 위한 선택 기능이며, 기본으로 꺼져 있습니다.

## 두 가지 사용 방식

기준은 누구의 권한으로 여러 프로젝트를 조회하느냐입니다.

| | 1. 관리자가 직접 사용 | 2. 조회 권한만 위임 |
|---|---|---|
| 사용자 | 클라우드 관리자 | 운영(NOC)팀이나 감사 담당처럼 `admin`을 주면 안 되는 사람 |
| 목적 | 평소 하던 `--all-projects` 조회를 자연어로 | 관리 권한 없이 클라우드 전체 현황을 보여 줌 |
| 자격 증명 | `admin` Role 계정(방식 A) | 전용 Role(방식 B) 또는 제한된 Application Credential(방식 C) |
| OpenStack 설정 | 거의 없음. Heat 스택 조회에만 정책 규칙 하나 필요 | 필요함. Role과 정책 override, 또는 Cinder 설정 |
| 조회 범위 | 전부 | 정책이 허용한 것만. Cinder 목록과 서버 그룹은 Role에 위임할 수 없음 |
| 일반적인 경우 | 대부분 | 직무를 분리하는 조직 |

1번이라면 관리자 계정으로 [켜는 순서](#켜는-순서)만 따르면 되고, 아래 방식 설명은
건너뛰어도 됩니다. 2번은 먼저 OpenStack 관리자가 방식 B나 C를 준비해야 합니다.

### 결과를 누가 보는가: 서버 모드

- **고정 자격 증명 모드**(`.env`의 계정 하나): 스위치를 켜면 **서버에 접속하는 모든
  클라이언트**가 그 계정의 권한으로 여러 프로젝트를 조회합니다. 팀 OpenWebUI처럼 함께
  쓰는 클라이언트 뒤에 관리자 계정으로 이 기능을 켜지 마세요. 채팅할 수 있는 누구나
  클라우드 전체를 조회할 수 있습니다. 1번은 Claude Desktop처럼 관리자만 쓰는 서버에
  맞습니다.
- **다중 사용자 모드**: 요청마다 호출자 본인의 Application Credential을 쓰므로, 각자
  자기 권한이 허용하는 것만 봅니다. 여러 사람이 한 서버를 함께 쓰면서 2번을 하려면 이
  모드를 쓰세요. [다중 사용자 가이드](multi-user-guide.ko.md)를 참고하세요.

## 켜는 순서

**1번(관리자):**

1. `admin` Role을 가진 계정으로 서버를 연결합니다.
2. 기능을 켭니다. `ALLOW_CROSS_PROJECT_READ=true`를 설정하거나([설정](configuration.ko.md)),
   Claude Desktop 확장 설정에서 **Allow cross-project reads**를 켭니다.
3. 선택: 여러 프로젝트의 Heat 스택을 조회하려면 OpenStack 설정
   [2단계](#방식별-openstack-필수-설정)의 Heat 정책 규칙을 추가합니다.

**2번(조회 권한 위임):**

1. [방식 선택](#방식-선택)에서 방식 B나 C를 고릅니다.
2. OpenStack 관리자가 그 방식의 [OpenStack 필수 설정](#방식별-openstack-필수-설정)을
   적용합니다.
3. 사용자마다 전용 Role을 가진 계정(방식 B)이나 다중 사용자 모드용 Application
   Credential(방식 C)을 줍니다.
4. `ALLOW_CROSS_PROJECT_READ=true`로 기능을 켭니다.

그다음 요청에서 모든 프로젝트를 물어봅니다. 예: "List VMs per project". 그러면
클라이언트가 지원 도구에 `all_projects=true`를 넘깁니다.

## 지원 도구

서버에 `ALLOW_CROSS_PROJECT_READ=true`(기본값 `false`)가 설정되어 있으면, 일부 목록
도구가 OpenStack CLI의 `--all-projects`처럼 `all_projects=true`를 받습니다.

| 도구 | `all_projects=true`일 때 |
|---|---|
| `get_instance_details`, `search_instances`, `get_instances_by_status` | 조회 가능한 모든 프로젝트의 인스턴스. 각 항목에 `project_id`와 `project_name` 포함 |
| `get_volume_list`, `get_volume_snapshots` | 조회 가능한 모든 프로젝트의 볼륨 또는 스냅샷. 각 항목에 `project_id`와 `project_name` 포함 |
| `get_volume_backups`, `get_volume_groups` | 조회 가능한 모든 프로젝트의 백업 또는 generic 볼륨 그룹. Cinder는 소유 프로젝트를 관리자에게만 보여 주므로, 소유자가 있는 항목이 하나도 없으면 범위를 알 수 없다는 `scope.warning`이 붙음 |
| `get_server_groups` | 조회 가능한 모든 프로젝트의 서버 그룹. 각 항목에 `project_id`와 `project_name` 포함 |
| `get_image_detail_list` | Glance가 자격 증명에 보여 주는 모든 이미지. 관리자에게는 다른 프로젝트의 private 이미지도 포함. Neutron처럼 public, community, shared 이미지는 범위 판단에 포함하지 않음 |
| `get_heat_stacks` | Heat의 `global_tenant` 쿼리로 모든 프로젝트의 스택. Heat의 기본 `stacks:global_index` 정책은 관리자를 포함한 모두에게 이를 거부함 |
| `get_load_balancer_list` | 조회 가능한 모든 프로젝트의 로드밸런서. 각 항목에 `project_id`와 `project_name` 포함. `result.scope`는 모든 페이지를 기준으로 함 |
| `get_network_details`, `get_routers`, `get_security_groups`, `get_floating_ips` | Neutron이 자격 증명에 보여 주는 네트워크, 라우터, 보안 그룹 또는 floating IP. 각 항목에 `project_id`와 `project_name` 포함. Neutron은 목록 요청을 거부하지 않고 다른 프로젝트의 공유·외부 리소스를 모두에게 보여 주므로, 결과에 다른 프로젝트의 비공유 리소스가 없으면 `scope.warning`이 붙음 |
| `get_project_details` | 조회 가능한 모든 프로젝트의 요약(ID, 이름, 도메인, 활성 여부, `is_current`). `project_name`이나 ID가 한 프로젝트와 일치하면 그 프로젝트의 상세와 리소스 수. 네트워크 수는 자격 증명이 볼 수 있는 리소스만 포함 |

## 동작 방식

- **조회 가능한 자격 증명**: 대상 OpenStack 서비스의 정책이 해당 자격 증명의 토큰에
  전체 프로젝트 목록 API를 허용할 때만 여러 프로젝트를 조회할 수 있습니다.
  MCP-OpenStack-Ops는 이 판단을 위해 Role이나 Group을 정의·저장·검사하지 않습니다.
- **스위치의 역할**: `ALLOW_CROSS_PROJECT_READ`는 이 서버에서 파라미터의 동작을 켤 뿐
  권한을 부여하지 않습니다. 고정 자격 증명 모드에서는 서버에 접속하는 모든 클라이언트가
  서버 자격 증명의 권한으로 조회합니다. 다중 사용자 모드에서는 요청마다 호출자의
  Application Credential로 판정됩니다.
- **거부**: 정책 거부(HTTP 403)는 오류로 반환되며, 현재 프로젝트 결과로 대체되지
  않습니다. 일부 서비스는 권한 없는 요청을 거부하지 않고 호출자의 프로젝트로 좁힙니다.
  그래서 결과에 현재 프로젝트만 있으면 `scope.warning`이 붙습니다. 각 목록은
  `scope.projects_in_result`를 함께 보고합니다.
- **변경 없음**: `all_projects`가 없으면 모든 도구는 계속 현재 프로젝트만 다룹니다.
  변경 도구와 이름 기반 단건 조회(예: `get_instance_by_name`)는 항상 프로젝트 범위로
  제한됩니다. 다른 프로젝트의 이름이나 ID를 받는 것은 `all_projects=true`인
  `get_project_details`뿐입니다.

## 방식 선택

cross-project 조회 권한은 이 서버가 아니라 OpenStack에서 설정합니다. 방식 A는
1번을 위한 것이고, 방식 B와 C는 2번을 구현하는 두 가지 방법입니다. 각 방식에 필요한
설정은 다음 절을 참고하세요.

| 방식 | 여러 프로젝트를 조회하는 주체 | 비고 |
|---|---|---|
| A | `admin` Role을 가진 credential | 간단하지만 전체 관리 권한을 줌 |
| B | 서비스 정책이 허용한 전용 Role(예: `cross_project_reader`)을 가진 credential | 최소 권한. 단, 모든 서비스를 위임할 수 있지는 않음 |
| C | 다중 사용자 모드 요청 헤더로 보내는 제한된 Application Credential(Role 일부 또는 access rules) | 다중 사용자 모드 전용 |

## 방식별 OpenStack 필수 설정

이 설정이 없어도 스위치는 동작하지만, OpenStack이 아래 참고 표처럼 요청을
거부하거나 좁힙니다.

| 방식 | 필요한 설정 | 설정하지 않으면 |
|---|---|---|
| A | 대부분의 도구는 없음. 여러 프로젝트의 Heat 스택 조회에는 `stacks:global_index` override(2단계)가 필요 | `all_projects`를 쓴 `get_heat_stacks`가 관리자에게도 정책 거부를 반환 |
| B | 1단계와 2단계 | Nova, Keystone, Heat가 요청을 거부(HTTP 403) |
| C, Role 일부 | 3단계(Cinder만) | `reader`만 가진 credential도 볼륨을 만들 수 있음 |
| C, access rules | 서비스의 `service_type`이 카탈로그 타입이 아니면 4단계(Kolla-Ansible의 Cinder) | 그 서비스가 조회를 포함해 credential을 HTTP 401로 거부 |

**1단계: Role 생성과 부여**(방식 B). 관리자 credential로 실행합니다.

```bash
openstack role create cross_project_reader
openstack role add --user <user> --project <project> cross_project_reader
```

**2단계: 정책 override 추가.** Kolla-Ansible에서는 배포 호스트에 다음 파일을
만듭니다.

```yaml
# /etc/kolla/config/nova/policy.yaml
"os_compute_api:servers:detail:get_all_tenants": "rule:context_is_admin or role:cross_project_reader"
"os_compute_api:servers:index:get_all_tenants": "rule:context_is_admin or role:cross_project_reader"
```

```yaml
# /etc/kolla/config/keystone/policy.yaml (the 2025.1 default rule plus the role)
"identity:list_projects": "(rule:admin_required) or (role:reader and system_scope:all) or (role:reader and domain_id:%(target.domain_id)s) or role:cross_project_reader"
```

```yaml
# /etc/kolla/config/heat/policy.yaml (the default is rule:deny_everybody)
"stacks:global_index": "rule:context_is_admin or role:cross_project_reader"
```

방식 A에는 Heat 파일만 필요합니다. override는 규칙 전체를 바꾸므로 기본값 부분을
유지하세요. 사용하는 릴리스의 기본값은 예를 들어
`oslopolicy-policy-generator --namespace keystone`로 확인합니다.

**3단계: Cinder의 새 정책 기본값 적용**(Role 일부를 쓰는 방식 C). Cinder 2025.1은
`[oslo_policy] enforce_new_defaults`의 기본값이 `false`라서, 예전(deprecated) 규칙
때문에 `reader`만 가진 credential도 볼륨을 만들 수 있습니다. 이 설정은 테스트
클라우드에서 라이브로 확인하지 않았습니다.

```ini
# /etc/kolla/config/cinder.conf
[oslo_policy]
enforce_new_defaults = true
```

**4단계: Cinder에 카탈로그 서비스 타입 지정**(access rules를 쓰는 방식 C).
keystonemiddleware는 access rules를 `[keystone_authtoken] service_type`과 비교하며,
이 값은 Keystone 카탈로그에 있는 서비스 타입이어야 합니다. Kolla-Ansible은 Cinder의
값을 카탈로그에 없는 `volume`으로 설정합니다.

```ini
# /etc/kolla/config/cinder.conf
[keystone_authtoken]
service_type = block-storage
```

그러면 볼륨 도구용 access rules의 `service`는 `block-storage`를 씁니다. 3단계와
4단계를 모두 적용하면 두 섹션을 같은 `cinder.conf`에 넣으세요.

**적용**은 Kolla-Ansible 배포 호스트에서 합니다. 지정한 서비스가 재시작됩니다.

```bash
kolla-ansible reconfigure -i <inventory> -t nova,keystone,heat,cinder
```

파일을 추가한 서비스만 지정하세요. 새로 `kolla-ansible deploy`를 실행하면
`/etc/kolla/config`에 있는 파일이 적용되며, 이 설정들에 해당하는 `globals.yml` 변수는
없습니다. 되돌리려면 파일을 지우고 같은 명령을 실행합니다. Kolla-Ansible을 쓰지
않으면 같은 규칙을 각 서비스의 정책 파일에, 같은 옵션을 설정 파일에 넣으세요.

## 참고: 정책 규칙과 위임 가능 여부

cross-project 조회를 판단하는 정책 규칙과 OpenStack 2025.1(Epoxy)의 기본값은 다음과
같습니다.

| 서비스 | 요청 | 정책 규칙과 기본값 | 권한이 없을 때 |
|---|---|---|---|
| Nova | 전체 프로젝트 서버 목록 | `os_compute_api:servers:detail:get_all_tenants`, `os_compute_api:servers:index:get_all_tenants`: `rule:context_is_admin` (`role:admin`) | HTTP 403 |
| Cinder | 전체 프로젝트 볼륨·스냅샷 목록 | 전용 규칙 없음. `context_is_admin`(`role:admin`)을 통과할 때만 `all_tenants`를 적용 | 호출자 프로젝트로 조용히 좁혀짐 |
| Keystone | 프로젝트 목록 | `identity:list_projects`: `rule:admin_required`, system 범위 reader, 또는 자기 도메인의 domain reader | HTTP 403 |
| Neutron | 네트워크, 라우터, 보안 그룹, floating IP 목록 | 전체 프로젝트 옵션 없음. 각 리소스의 조회 정책이 목록을 결정하고, 다른 프로젝트의 공유·외부 리소스는 모두에게 보임 | 자격 증명이 볼 수 있는 것으로 좁혀짐 |
| Glance | 이미지 목록 | `get_images`: `rule:context_is_admin` 또는 프로젝트 reader. 관리자는 다른 프로젝트의 private 이미지도 봄 | 자기 이미지와 public·shared 이미지로 좁혀짐 |
| Heat | 전체 프로젝트 스택 목록 | `stacks:global_index`: `rule:deny_everybody` | HTTP 403, 관리자 포함 |
| Octavia | 전체 프로젝트 로드밸런서 목록 | `os_load-balancer_api:loadbalancer:get_all-global`: `rule:load-balancer:read-global` (`role:admin`) | 호출자 프로젝트로 좁혀짐 |

전용 Role(방식 B)은 정책 규칙만으로 요청이 결정되는 곳에서만 동작합니다.

| 요청 | 전용 Role로 위임 | 이유 |
|---|---|---|
| Nova 서버 목록 | 가능 | `get_all_tenants` 규칙이 결정 |
| Keystone 프로젝트 목록 | 가능 | `identity:list_projects`가 결정 |
| Heat 스택 목록 | 가능 | `stacks:global_index`가 결정 |
| Nova 서버 그룹 목록 | 불가 | Nova가 `os-server-groups:index:all_projects` 규칙보다 먼저 코드에서 `context_is_admin`을 검사 |
| Cinder 볼륨, 스냅샷, 백업, 그룹 목록 | 불가 | Cinder가 코드에서 `context_is_admin`을 검사 |
| Glance private 이미지, Octavia 로드밸런서 | 해당 서비스의 관리자 규칙으로만 | 목록 정책이 다른 프로젝트의 리소스를 관리자에게 허용 |

위임할 수 없는 목록은 방식 A나 C를 쓰거나, `scope.warning`이 붙은 좁혀진 결과를
받아들여야 합니다.
