# 대화 세션 인수인계 컨텍스트

이 문서는 이번 장기 대화의 핵심 의사결정과 작업 이력을 다른 대화에서 이어갈 수
있도록 요약한 것이다. 자격증명, 토큰, 내부 주소 등 민감정보는 제외했다.

## 저장소와 현재 상태

- 저장소: `MCP-OpenStack-Ops`
- 현재 브랜치: `main`
- 기준 커밋: `a597404 fix: harden multi-user OpenStack operation handling`
- 주 작업: GitHub issue `#73` 사용자별 OpenStack 자격증명·프로젝트 격리
- 개발은 `feat/73-per-user-connections`에서 시작했고 주요 기능은 이후 릴리스에 반영됐다.
- 대화 중 `3.5.6`, `3.6.1`, `3.6.2` 릴리스가 진행됐다.
- 현재 작업 트리에는 `3.6.2` 이후 피드백 대응이 아직 커밋되지 않았다.

## issue #73의 요구사항과 방향

vishrm은 하나의 원격 MCP 서버를 여러 사용자가 공유하면서 각 사용자의 OpenStack
자격증명과 Keystone 권한으로 요청을 실행하는 기능을 요청했다.

- 공용 서비스 계정 대신 호출 사용자 자신의 권한을 사용한다.
- 사용자별 프로젝트와 리소스를 엄격히 격리한다.
- 자격증명은 디스크·DB·로그에 저장하지 않고 짧게 메모리에만 유지한다.
- 일반 사용자는 자기 프로젝트만 접근한다.
- 관리자는 정책이 허용하는 범위에서 여러 프로젝트를 조회할 수 있어야 한다.
- 프로젝트는 연결 시 선택하며 세션 중 전환은 요구하지 않는다.
- 자격증명 폐기는 짧은 캐시 만료 시간 안에 반영되면 된다.
- 쓰기 도구는 관리자에게도 기본 비활성화한다.
- 주 클라이언트는 Claude Code이고 Claude Desktop도 사용한다.

초기 검토에서 사용자별 격리를 1단계로, 관리자 교차 프로젝트 조회를 영향과 위험이
더 큰 후속 단계로 구분했다. 관리자 기능의 핵심은 변경 권한 확대가 아니라 Keystone
정책이 허용한 여러 프로젝트에 대한 **조회** 지원이다.

## 구현·문서화·검증 경과

`feat/73-per-user-connections`에서 다음을 구현했다.

- HTTP 요청마다 호출자 자격증명으로 Keystone 인증 및 OpenStack 연결 생성
- 연결과 자격증명의 사용자 간 공유 방지
- 짧은 메모리 캐시와 만료 후 폐기
- 프로젝트 범위와 Keystone 역할에 따른 권한 위임
- 호출자 로그 추적과 기존 단일 사용자 방식의 호환성 유지
- 원격 HTTP bearer 인증 설정 주석 보강
- README 영문·한글에 Claude Code 등록·제거 및 브랜치 설치 방법 추가
- `phase1` 표현을 제거하고 다중 사용자 안내를 범용 문서로 정리

실제 Kolla OpenStack에 테스트용 프로젝트·사용자·네트워크·VM·볼륨을 만들어 격리,
동시 요청, 읽기/쓰기 권한과 여러 도구를 검증했다. Claude Code에 MCP 서버를 실제
등록해 자연어 요청이 MCP 도구와 OpenStack API를 호출하는 종단 간 검사도 수행했다.
모의 호출과 실제 Claude Code 검증은 결과에서 구분했다.

### 실환경 검사에서 얻은 결론

- 일반 사용자의 관리자 전용 전체 클러스터 조회 실패는 정상 정책 결과이므로 해당
  사용자에게 적합한 프로젝트 범위 질문으로 재검증했다.
- 서로 다른 프로젝트의 인스턴스·네트워크·볼륨이 노출되지 않는지 확인했다.
- 동시성 검사를 위해 여러 테스트 리소스를 만들고 요청을 병렬 실행했다.
- `prompt_template.md`의 실행 가능한 자연어 예제를 Claude Code로 일관되게 검사했다.
- OpenWebUI 중간 결과는 최종 결과에서 제외하고 Claude Code 결과로 통일했다.
- Claude Code 사용량 제한으로 중단된 검사는 제한 초기화 후 이어서 수행했다.
- `dontAsk`는 제품 버그보다 Claude Code의 작업 승인 보안 정책으로 판단했다.
- Cinder 백업 실패는 MCP가 아니라 Kolla/NFS 하위 디렉터리 권한 문제였다. 컨테이너
  UID/GID와 마운트를 확인하고 그룹 쓰기 권한을 보정한 뒤 재시험했다.
- MTU 1500 현상도 MCP 로직이 아닌 테스트 네트워크 환경 문제로 분리했다.
- 테스트 환경 제약과 실제 제품 결함을 보고서에서 구분했다.

## 테스트 보고서와 문서 정책

전체 도구 및 자연어 예제 결과를 영문·한글 보고서로 작성했고, 결과 표에는 성공 수,
전체 수, 차이 원인을 함께 표시했다.

- `docs/issues/issue-73-test-report-20261104-054928.md`
- `docs/issues/issue-73-test-report-20261104-054928.ko.md`

날짜별 중간 산출물이 `docs/`에 과도하게 쌓여 불필요한 파일을 정리했다. 이후 원칙:

- `docs/`에는 재사용 가능한 사용자 안내만 유지한다.
- 이슈별 기록은 사용자가 명시적으로 요청할 때만 `docs/issues/`에 둔다.
- README의 CLI-to-tool 매핑은 구현과 실제 검증 상태를 구분한다.
- 영문·한글 README의 기능, 설정, 제약을 동등하게 유지한다.

## 별도로 수행한 저장소 작업

- MCP Python SDK Streamable HTTP 세션 누적 자원 고갈 Dependabot 경고를 확인하고
  의존성·잠금파일을 갱신했다.
- `uv sync --locked`의 설정/잠금파일 불일치를 해결했다.
- DeciFlow를 참고해 태그 푸시 시 PyPI/TestPyPI 배포 후 커밋 메시지를 바탕으로
  GitHub Release도 생성하도록 워크플로를 보강했다.
- PyPI 웹과 `pip index versions`의 새 버전 표시 시차는 배포 실패가 아니라 simple
  index/CDN 전파 지연으로 판단했다.

## vishrm의 대규모 환경 피드백 대응

vishrm은 `3.6.2`를 실제 대규모 OpenStack에서 검사했다. 초기 사용자별 접근 격리는
대체로 해결된 것으로 평가됐고, 후속은 동시성, 성능, 오류 처리와 응답 의미에
집중됐다.

- 잘못된 최초 POST의 `unsupported_protocol` 거절 후 정상 요청 복구 확인
- 서버 이름/UUID를 사용하는 `get_server_events` 첫 호출 문제 수정·검증
- 병렬 요청에서 5xx, 인증 불가, 잘못된 Neutron 404가 없도록 안정화
- Keystone 인증 시간과 도구 실행 시간을 분리해 병목을 판단하는 방향 검토
- 대규모 환경의 위험을 줄이기 위해 읽기 중심의 소규모 QA부터 검증
- 설치·브랜치 사용법을 제공하고 vishrm에게 교차 검증 요청

#73이 여러 하위 주제로 길어졌으므로 핵심 개선 확인 후 종료하고 새로운 독립 문제는
새 이슈로 받는 방향을 논의했다. 다만 `finish_time`은 사용자 결정에 따라 별도
이슈로 분리하지 않고 #73 안에서 처리했다.

## 현재 미커밋 후속 변경

### OAuth discovery 경로

- `/mcp/.well-known/openid-configuration`이 인증 미들웨어에서 `401`로 차단되지 않고
  명시적으로 `404`를 반환하도록 수정했다.
- 실행 중인 컨테이너에서 실제 `404`를 확인했다.

### `get_server_events`의 `finish_time`

- Nova action 목록에는 완료 시간이 없을 수 있으므로 기본 `finish_time=null`을 오류가
  아닌 정보 부재로 취급한다.
- `finish_time_source`로 값의 출처나 누락 이유를 표시한다.
- `include_event_details=true`로 action detail event의 실제 완료 시간을 조회한다.
- action마다 Nova API를 추가 호출하므로 상세 조회는 최대 10개로 제한했다.
- 기본 조회는 추가 호출 없이 기존 성능과 limit을 유지한다.
- 실제 OpenStack VM과 등록된 stdio MCP 도구에서 `finish_time` 및
  `finish_time_source=latest_event` 반환을 확인했다.

### 검증 결과

- 전체 단위 테스트: `254/254` 통과, 실패·건너뜀 없음, 경고 27개
- OAuth 경로, 이름/UUID, 완료 시간 출처, 상세 이벤트, 10개 제한 테스트 추가
- 실제 OpenStack 및 실제 MCP 호출 검증 완료
- `git diff --check` 통과
- Ruff는 잠시 추가했으나 기존 코드 전반의 진단이 대량 발생했고, 사용자 요청에
  따라 설치·의존성·잠금파일 관련 변경을 모두 제거했다.

현재 변경 파일:

- `README.md`
- `docs/issues/issue-73-test-report-20261104-054928.md`
- `docs/issues/issue-73-test-report-20261104-054928.ko.md`
- `src/mcp_openstack_ops/prompt_template.md`
- `src/mcp_openstack_ops/services/compute.py`
- `src/mcp_openstack_ops/tools/get_server_events.py`
- `src/mcp_openstack_ops/user_connection.py`
- `tests/test_phase1_stabilization.py`
- `tests/test_user_connection.py`
- `CONTEXT.md`

## 남은 작업과 다음 대화 시작점

1. 현재 diff와 테스트 결과를 최종 확인한다.
2. 요청 시 변경 범위에 맞는 커밋 메시지를 작성한다. 커밋·푸시·태그는 각각 별도
   승인 없이는 실행하지 않는다.
3. 새 릴리스 버전을 정해 릴리스한 뒤 vishrm에게 최종 교차 검증을 요청한다.
4. vishrm 환경에서 다음은 아직 교차 검증이 필요하다.
   - 서로 다른 프로젝트 자격증명의 동시 접속
   - OpenStack 서비스 장애 시 오류 응답
   - 자격증명 폐기 후 캐시 만료에 따른 접근 차단
   - `include_event_details=true`의 대규모 환경 지연
5. #73 댓글은 영어 전문과 완전한 한글 번역을 먼저 채팅에 제시하고, 정확한 문구와
   게시를 사용자가 승인한 뒤에만 등록한다.
6. 핵심 검증 완료 후 #73 종료를 제안하고 이후 독립 문제는 새 이슈로 분리한다.

## 반드시 유지할 작업 원칙

- Git stage/commit/push/tag/merge/branch 작업은 명시적 승인 없이 수행하지 않는다.
- GitHub 댓글 등 외부 메시지는 최종 초안 승인을 받은 경우에만 게시한다.
- 영어 외부 메시지는 검토용 전체 한글 번역을 함께 제공한다.
- `.env`, 내부 주소, 사용자명, 비밀번호, 토큰을 문서·로그·댓글에 포함하지 않는다.
- 단위 테스트 성공을 실서비스 성공으로 표현하지 않고 실제 호출, 정책 거부, 환경
  실패, 미검증 항목을 명확히 구분한다.
- 테스트 OpenStack 리소스의 생성·변경·삭제 범위를 명확히 하고 운영 리소스를
  건드리지 않는다.
