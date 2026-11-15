[English](barbican-tls-guide.md) | **Korean**

# Barbican 시크릿과 TLS 로드밸런서

Barbican(key-manager) 도구는 시크릿의 **메타데이터와 참조**를 다룹니다. 시크릿,
컨테이너, 주문(order)을 조회하고, 읽기 ACL을 변경하고, Barbican 안에서 키를
생성하고, 자체 서명 인증서를 만들고, 인증서를 Octavia `TERMINATED_HTTPS` 리스너에
연결합니다. 시크릿 내용은 MCP 서버의 도구 인자나 결과를 거치지 않습니다.

## 도구가 시크릿 payload를 다루지 않는 이유

Barbican은 어떤 payload든 저장하고 반환할 수 있고, MCP 서버도 그것을 전달할 수
있습니다. 그래도 의도적으로 전달하지 않습니다. 도구 인자와 결과는 클라이언트의
LLM을 거치므로, 개인키, 인증서 번들, 비밀번호를 이 경로로 보내면 외부 모델과 그
대화 기록에 남습니다. 이를 원천 차단하기 위해 다음과 같이 구현했습니다.

- 어떤 도구에도 payload 파라미터가 없습니다. 사용자 인증서와 키는 CLI나 다른
  신뢰할 수 있는 경로로 등록합니다([사용자 인증서 등록](#사용자-인증서-등록) 참고).
- 어떤 도구도 payload를 반환하지 않습니다. 시크릿은 메타데이터 API로만 읽으며,
  payload를 내려받는 openstacksdk 호출(`get_secret`, `find_secret`)은 쓰지 않습니다.
- 키는 사용되는 곳에서 만들어집니다. `set_secret`(`create_self_signed_tls`)은 MCP
  서버 안에서 키를 생성해 Barbican에 바로 저장하고, `set_secret_order`는 Barbican이
  직접 키를 생성하게 합니다. 반환되는 것은 href, 공개 인증서, 그 fingerprint뿐입니다.

## 사전 조건

아래 항목은 배포와 계정 설정이며, Octavia와 Barbican을 쓰는 모든 사용자에게
같습니다. MCP 밖에서 준비합니다.

1. **Barbican이 배포되어 있어야 합니다.** Keystone catalog에 `key-manager`
   endpoint가 있어야 합니다.

   ```bash
   openstack endpoint list --service key-manager
   ```

   없으면 모든 Barbican 도구가 `Barbican (key-manager) service is not available`을
   반환합니다.
2. **Octavia가 인증서 관리에 Barbican을 사용해야 합니다.** `octavia.conf`의
   `[certificates]` 기본값은 `cert_manager = barbican_cert_manager`,
   `barbican_auth = barbican_acl_auth`입니다. 이 설정에서는 리스너를 만들 때 Octavia
   API가 요청 사용자의 토큰으로, 참조된 시크릿에 Octavia 서비스 사용자의 읽기
   권한(ACL 항목)을 추가합니다. 사용자는 Octavia 서비스 사용자의 ID를 알 필요가
   없습니다.
3. **계정이 시크릿을 만들고 ACL을 변경할 수 있어야 합니다.** Barbican 정책에 따라
   다릅니다. 구 정책에서는 `admin` 또는 `creator` 역할이 필요하고, Secure RBAC
   기본값에서는 프로젝트 `member` 역할로 충분합니다. 리스너를 만드는 사용자는
   참조한 시크릿의 ACL을 변경할 수 있어야 합니다.
4. **배포가 ACL을 자동으로 부여하지 않는 경우에만:** `set_secret_acl`(`add_users`)
   이나 `openstack acl user add`로 Octavia 서비스 사용자에게 읽기 권한을 직접
   부여합니다. 그 사용자의 ID는 관리자가 조회할 수 있습니다.

## 사용자 인증서 등록

MCP 밖, 신뢰할 수 있는 호스트에서 진행합니다. Octavia는 `opaque` 시크릿으로 저장된
PKCS#12 번들을 받습니다.

```bash
openssl pkcs12 -export -inkey server.key -in server.crt -certfile ca-chain.crt \
  -passout pass: -out server.p12
openstack secret store --name web-tls -t opaque -e base64 \
  -p "$(base64 -w0 < server.p12)"
```

이후 도구에서는 시크릿을 이름(`web-tls`), ID 또는 href로 지정합니다.

## 자체 서명 인증서 생성

테스트나 내부 서비스에는 자체 서명 인증서를 요청할 수 있습니다.

> Create a self-signed TLS secret named web-tls for 192.168.35.169 with SANs
> 192.168.35.169 and 10.40.40.185.

`set_secret`(`action="create_self_signed_tls"`)은 `name`, `common_name`,
`subject_alt_names`(DNS 이름과 IP 주소, 쉼표 구분), `days`(1-3650),
`key_size`(2048, 3072, 4096)와 선택 항목인 Barbican `expiration`을 받습니다. 결과로
시크릿 href, PEM 형식의 공개 인증서, SHA-256 fingerprint, 만료 시각을 반환합니다.
자체 서명 인증서는 클라이언트의 신뢰 저장소에 추가하기 전에는 신뢰되지 않습니다.

## TERMINATED_HTTPS 리스너 생성

`set_load_balancer_listener`는 Octavia에 필요한 인증서 참조를 받습니다.

| 파라미터 | 의미 |
| --- | --- |
| `default_tls_container_ref` | 기본 서버 인증서. PKCS#12 시크릿 또는 certificate 컨테이너를 이름, ID, href로 지정합니다. `TERMINATED_HTTPS`에서는 필수입니다. 클라이언트가 호스트 이름(SNI)을 보내지 않거나 맞는 SNI 인증서가 없을 때 Octavia가 사용합니다 |
| `sni_container_refs` | 선택 항목. Octavia가 요청된 호스트 이름에 따라 고르는 인증서들(쉼표 구분) |

이름은 현재 프로젝트에서 href로 변환되며, 시크릿을 먼저 찾고 없으면 certificate
컨테이너를 찾습니다. 두 파라미터는 `action="set"`에서도 쓸 수 있습니다. 예시:

> On web-lb, add a TERMINATED_HTTPS listener web-listener-https on port 443
> with certificate web-tls and default pool web-pool.

리스너 생성은 비동기입니다. `get_load_balancer_listeners`로 리스너가
`ACTIVE`/`ONLINE`이 되었는지 확인한 뒤 `curl -vk https://<address>/`로 시험합니다.
리스너 결과에는 `default_tls_container_ref`와 `sni_container_refs`가 표시됩니다.

## 멤버까지의 TLS

Octavia Cookbook은 HTTPS 처리 방식을 세 가지로 설명합니다. **TLS-terminated
HTTPS**(로드밸런서에서 TLS를 종료), **non-terminated HTTPS**(TLS를 풀지 않고 멤버로
전달하며, 흔히 TLS passthrough라고 부름), **backend re-encryption**(로드밸런서에서
TLS를 종료한 뒤 멤버로 다시 암호화)입니다. 위의 `TERMINATED_HTTPS` 리스너가
TLS-terminated HTTPS이며, 나머지 두 방식은 리스너와 pool의 프로토콜, pool의 TLS
필드로 설정합니다. Backend re-encryption에는 **client authentication**을 더할 수
있습니다. 이 경우 로드밸런서도 멤버에게 클라이언트 인증서를 제시합니다(mutual TLS,
mTLS). Client authentication이 없으면 로드밸런서만 멤버를 검증합니다.

| 방식 | 리스너 / pool | 인증서 | 로드밸런서가 할 수 있는 것 |
| --- | --- | --- | --- |
| TLS-terminated HTTPS | `TERMINATED_HTTPS` / `HTTP` | Barbican의 서버 인증서 | L7 정책, `X-Forwarded-For`, 쿠키 기반 세션 유지. 멤버로는 평문 HTTP |
| Non-terminated HTTPS (TLS passthrough) | `HTTPS` / `HTTPS` | 각 멤버가 보유. Barbican 시크릿 불필요 | 암호화된 스트림 전달만 가능. L7 정책과 헤더 삽입 불가, 세션 유지는 `SOURCE_IP`만 |
| Backend re-encryption | `TERMINATED_HTTPS` / `tls_enabled=true`인 `HTTP` | Barbican의 서버 인증서, 선택적으로 CA와 CRL, client authentication용 클라이언트 인증서 | L7 기능을 쓰면서 멤버로 가는 트래픽도 다시 암호화 |

항목별 비교:

| 항목 | TLS-terminated HTTPS | Non-terminated HTTPS | Backend re-encryption |
| --- | --- | --- | --- |
| 클라이언트 → 로드밸런서 암호화 | ✅ | ✅ | ✅ |
| 로드밸런서 → 멤버 암호화 | ❌ 평문 | ✅ | ✅ |
| 로드밸런서가 HTTP 내용을 봄 | ✅ | ❌ | ✅ |
| L7 정책, `X-Forwarded-For` | ✅ | ❌ | ✅ |
| 세션 유지 | 쿠키 가능 | `SOURCE_IP`만 | 쿠키 가능 |
| 서버 인증서 위치 | Barbican | 각 멤버 | Barbican과 각 멤버 |
| 멤버 인증서 검증 | 해당 없음 | ❌ | ✅ 선택 (`ca_tls_container_ref`) |
| 멤버에 대한 client authentication (mTLS) | 해당 없음 | ❌ | ✅ 선택 (`tls_container_ref`) |
| 멤버에 인증서 설치 | 불필요 | 필요 | 필요 |
| 적합한 경우 | 내부망을 신뢰하고 인증서를 로드밸런서에서 일괄 관리 | 인증서를 로드밸런서에 맡길 수 없거나 멤버까지 종단 간 암호화가 필요 | L7 기능과 구간별 암호화가 모두 필요 |

**Non-terminated HTTPS**에는 새 파라미터가 필요 없습니다. `set_load_balancer_listener`로 `HTTPS`
리스너를, `set_load_balancer_pool`로 `HTTPS` pool을 만듭니다. 헬스 체크는
`set_load_balancer_health_monitor`에서 `monitor_type="TLS-HELLO"`로 TLS 핸드셰이크를
확인합니다.

**Backend re-encryption**에는 `set_load_balancer_pool`의 다음 파라미터를 씁니다(create와
set).

| 파라미터 | 의미 |
| --- | --- |
| `tls_enabled` | `true`면 멤버로 가는 트래픽을 다시 암호화하고, `false`면 끕니다 |
| `ca_tls_container_ref` | 멤버 인증서를 검증할 CA 인증서(PEM 시크릿). 없으면 멤버 인증서를 검증하지 않습니다 |
| `crl_container_ref` | 인증서 폐기 목록(PEM 시크릿). `ca_tls_container_ref`가 필요합니다 |
| `tls_container_ref` | client authentication용 클라이언트 인증서. mutual TLS(mTLS)를 요구하는 멤버에 로드밸런서가 제시합니다. PKCS#12 시크릿 또는 certificate 컨테이너 |
| `tls_versions`, `tls_ciphers`, `alpn_protocols` | 멤버 방향의 TLS 버전(`TLSv1.2,TLSv1.3`), OpenSSL cipher 문자열, ALPN 프로토콜(`h2,http/1.1`) |

인증서 참조는 리스너와 같이 이름, ID, href로 지정합니다. openstacksdk 4.22.0의
pool에는 `tls_container_ref` 필드가 없어서, 이 값이 있는 create나 set 요청은
Octavia API로 직접 보내고, `show`는 Octavia 응답에서 이 값을 읽습니다. CA와 CRL
시크릿은 다른 사용자 인증서처럼 MCP 밖에서 등록합니다.

## Backend re-encryption with client authentication(mTLS) 단계별 절차

로드밸런서에서 멤버로 가는 구간에서는 역할이 클라이언트 입장과 반대입니다.
로드밸런서(amphora)가 **TLS 클라이언트**이고, 각 멤버가 **TLS 서버**입니다. Client
authentication(mutual TLS, mTLS)에서는 양쪽이 모두 인증서로 신원을 증명합니다.

| 인증서 | 증명하는 것 | 위치 | 설치 주체 |
| --- | --- | --- | --- |
| 멤버 서버 인증서와 키 | 멤버를 로드밸런서에 증명 | 각 멤버의 웹 서버 | 사용자가 모든 멤버에 설치 |
| CA 인증서 | 로드밸런서의 클라이언트 인증서를 신뢰할 수 있음 | 각 멤버의 웹 서버 | 사용자가 모든 멤버에 설치 |
| 로드밸런서 클라이언트 인증서와 키(PKCS#12) | 로드밸런서를 멤버에 증명 | Barbican, 이어서 pool의 `tls_container_ref` | 사용자가 등록하고, amphora 설치는 Octavia가 처리 |
| CA 인증서 | 멤버 인증서를 신뢰할 수 있음 | Barbican, 이어서 pool의 `ca_tls_container_ref` | 사용자가 등록하고, amphora 설치는 Octavia가 처리 |

멤버는 보통 사설 주소를 쓰므로 공인 CA로는 인증서를 발급받을 수 없습니다. 사설 CA
하나(openssl, 사내 PKI, HashiCorp Vault 같은 도구)로 멤버 인증서와 클라이언트
인증서를 모두 발급합니다. `set_secret`(`create_self_signed_tls`)은 자체 서명 인증서
하나를 만드는 기능이며, CA가 아니므로 이 인증서들을 발급할 수 없습니다.

1~4단계는 개인키를 다루므로 MCP 밖, 신뢰할 수 있는 호스트에서 진행합니다.

**1. 사설 CA를 만듭니다.** `ca.key`는 오프라인으로 보관하고 `ca.crt`만 배포합니다.

```bash
openssl req -x509 -newkey rsa:4096 -nodes -days 3650 \
  -keyout ca.key -out ca.crt -subj "/CN=web-backend-ca"
```

**2. 멤버마다 서버 인증서를 발급합니다.** SAN에 멤버 주소를 넣습니다(멤버마다
반복).

```bash
openssl req -newkey rsa:2048 -nodes -keyout member1.key -out member1.csr \
  -subj "/CN=10.40.40.11"
openssl x509 -req -in member1.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -days 365 -out member1.crt \
  -extfile <(printf "subjectAltName=IP:10.40.40.11\nextendedKeyUsage=serverAuth")
```

**3. 로드밸런서 클라이언트 인증서를 발급**하고 PKCS#12로 묶습니다.

```bash
openssl req -newkey rsa:2048 -nodes -keyout lb-client.key -out lb-client.csr \
  -subj "/CN=web-lb"
openssl x509 -req -in lb-client.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -days 365 -out lb-client.crt -extfile <(printf "extendedKeyUsage=clientAuth")
openssl pkcs12 -export -inkey lb-client.key -in lb-client.crt \
  -passout pass: -out lb-client.p12
```

**4. 각 멤버를 설정합니다.** 자신의 인증서를 제공하고, CA가 서명한 클라이언트
인증서를 요구하게 합니다. nginx 예시:

```nginx
server {
    listen 443 ssl;
    ssl_certificate        /etc/nginx/tls/member1.crt;
    ssl_certificate_key    /etc/nginx/tls/member1.key;
    ssl_client_certificate /etc/nginx/tls/ca.crt;
    ssl_verify_client      on;
}
```

**5. 클라이언트 인증서와 CA를 CLI로 Barbican에 등록합니다.**

```bash
openstack secret store --name web-lb-client -t opaque -e base64 \
  -p "$(base64 -w0 < lb-client.p12)"
openstack secret store --name web-backend-ca -t opaque -e base64 \
  -p "$(base64 -w0 < ca.crt)"
```

**6. MCP로 pool과 멤버를 만듭니다.** `TERMINATED_HTTPS` 리스너 뒤에 둡니다.

> On listener web-listener-https, create pool web-pool-mtls with protocol HTTP,
> tls_enabled true, client certificate web-lb-client and CA web-backend-ca,
> then add members 10.40.40.11 and 10.40.40.12 on port 443.

이 요청은 `set_load_balancer_pool`(`tls_enabled="true"`,
`tls_container_ref="web-lb-client"`, `ca_tls_container_ref="web-backend-ca"`)과
`set_load_balancer_pool_member`를 호출합니다. 기존 pool은 같은 파라미터와
`action="set"`으로 전환할 수 있습니다.

**7. 확인합니다.**

- `set_load_balancer_pool`(`action="show"`)이 `tls_enabled`, `tls_container_ref`,
  `ca_tls_container_ref`를 보여 주고, `get_load_balancer_pool_members`에서 멤버가
  `ONLINE`이 됩니다.
- 로드밸런서를 거친 `curl -vk https://<address>/`가 페이지를 반환합니다.
- 다른 호스트에서 클라이언트 인증서 없이 `curl -v --cacert ca.crt https://10.40.40.11/`
  로 접속하면 멤버가 거부합니다(nginx는 400 "No required SSL certificate was sent"로
  응답). 멤버가 mTLS를 강제하고 있다는 뜻입니다.

클라이언트 인증서를 교체하려면 새 시크릿을 등록하고 `action="set"`과
`tls_container_ref`로 pool이 새 시크릿을 가리키게 합니다.

리스너가 외부 클라이언트를 인증하는 client authentication(TLS-terminated HTTPS load
balancer with client authentication. 리스너의 `client_ca_tls_container_ref`,
`client_authentication`, `client_crl_container_ref`)은 별개의 기능이며 구현되어 있지
않습니다.

## 도구와 액션

| 도구 | 액션 | 용도 |
| --- | --- | --- |
| `get_secrets` | 목록, 또는 `name`으로 상세 | 시크릿 메타데이터와 consumer. `secret_type`으로 필터 |
| `get_secret_containers` | 목록, 또는 `name`으로 상세 | 컨테이너와 그것이 묶는 시크릿 href |
| `get_secret_orders` | 목록, 또는 `order_id`로 상세 | 키 생성 주문과 결과 참조 |
| `get_secret_acl` | 조회 | 시크릿 또는 컨테이너의 읽기 ACL |
| `get_key_manager_quotas` | 조회 | 프로젝트의 실효 쿼터(-1은 무제한) |
| `get_secret_stores` | 목록 | 시크릿 스토어 백엔드. 다중 백엔드가 활성화된 경우에만 제공 |
| `set_secret` | `create_self_signed_tls`, `delete` | 자체 서명 PKCS#12 시크릿 생성, 시크릿 삭제 |
| `set_secret_container` | `create`, `delete` | 기존 시크릿 묶기(`generic`, `certificate`, `rsa`). 삭제해도 시크릿은 남음 |
| `set_secret_order` | `create`, `delete` | Barbican이 생성하는 대칭키(`key`) 또는 RSA 키(`asymmetric`) |
| `set_secret_acl` | `add_users`, `remove_users`, `set`, `delete` | 시크릿 또는 컨테이너의 읽기 ACL 사용자와 프로젝트 전체 접근 |

`set_*` 도구는 `ALLOW_MODIFY_OPERATIONS=true`일 때만 등록됩니다. 시크릿, 컨테이너,
주문 이름은 고유하지 않으므로, 이름이 여러 개와 일치하면 ID나 href를 사용합니다.

## 문제 해결

| 증상 | 원인과 조치 |
| --- | --- |
| `Barbican (key-manager) service is not available` | 서버의 interface와 `OS_REGION_NAME`에 해당하는 `key-manager` endpoint가 Keystone catalog에 없습니다. Barbican에는 `OS_*_PORT` 설정이 없으며, catalog endpoint에 MCP 서버에서 접근할 수 있어야 합니다 |
| 시크릿 생성 시 HTTP 403 | 계정에 Barbican 정책이 요구하는 역할이 없습니다([사전 조건](#사전-조건) 참고) |
| 리스너 생성이 인증서 오류로 실패 | 결과에 안내 문구가 붙습니다. 시크릿이 이 프로젝트에 있고 `ACTIVE`인지, PKCS#12 번들이거나 certificate 컨테이너인지, Octavia가 읽을 수 있는지(ACL) 확인합니다 |
| `get_secret_stores` 실패 | Barbican은 다중 시크릿 스토어 백엔드가 활성화된 경우에만 이 API를 제공합니다 |
| `not found or name is ambiguous` | 같은 이름의 시크릿이 여러 개이거나 없습니다. `get_secrets`의 ID나 href를 사용합니다 |
