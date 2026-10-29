# Integration validation

Validated on 2026-10-30 against a single-node Kolla Ansible test deployment,
using an administrative project. Credentials and deployment addresses are not
included in this report.

## Results

The final live suite recorded 68 passing checks, including prerequisite creation,
API read-back, asynchronous state checks, and cleanup. Three lifecycle checks
were skipped as described below. These counts are checks, not distinct features.

| Area | Live result |
| --- | --- |
| Connection | The project's connection factory authenticated successfully |
| Inventory | Domains, identity groups, backups, volume groups, volume QoS, and volume transfers were queried through actual MCP tool handlers |
| Monitoring and usage | Current allocation reporting and date-bounded Nova usage queries succeeded; unavailable physical capacity remained null |
| Floating IP pools | Allocation ranges totaled 50 addresses; one visible Floating IP was counted; global free capacity remained unknown |
| Routers and security groups | Created disposable resources, read them back through the SDK, deleted them through MCP tools, and confirmed absence |
| Volume types | Created a disposable type and removed it after group checks |
| Cinder QoS | Created a specification, showed it, changed its limit, verified the updated value, deleted it, and confirmed absence |
| Volume groups | Created a temporary group type and empty group; group reached available; show and delete succeeded |
| Identity | Created a disposable domain, group and user; group show/update/delete and user read-back/delete succeeded; domain was disabled and deleted during cleanup |
| Image sharing | Created a disposable shared image and recipient project; member add/list/remove succeeded |
| Heat | Created an empty stack, waited for CREATE_COMPLETE, queried resources/events/template/outputs, and deleted the stack |
| Backups | Created a blank 1 GiB source volume; created and showed its backup; restored into a new 1 GiB volume; waited for available states; deleted the backup and both volumes |

All registered cleanup checks passed. A final read-only audit across 14 resource
categories found zero remaining resources with either validation run's unique
names. Only disposable resources created by the validation runs were targeted
for deletion. Backup validation covered the API
lifecycle and ready states; it did not test integrity of non-empty application
data. Heat validation used an empty template with a constant output.

## Defect found and fixed

The existing Heat endpoint override ended at `/v1`. In the tested deployment,
SDK discovery failed with a `catalog_url` attribute error; forcing API version 1
alone instead produced a request to the invalid `/v1/stacks` path.

The connection factory now sets Heat API version 1 and, after authentication,
scopes the endpoint to `/v1/{project_id}`. The corrected connection passed live
stack creation and all four new query sections. A local regression test covers
the endpoint construction. The connection success log no longer includes token
contents.

## Limits and skipped operations

- **Network QoS:** the deployment does not advertise the Neutron `qos` extension;
  policy listing returned HTTP 404. Successful policy creation/deletion remains
  covered by local mocked tests, not live validation.
- **Alarms:** no `alarming` or `metric` service was registered in the catalog.
  Alarm listing returned an explicit missing-endpoint failure. The successful
  Aodh/Gnocchi lifecycle remains unverified against a live service.
- **Network agents:** listing succeeded. Existing cloud-wide agents were not
  enabled or disabled to avoid affecting the platform's networking.
- **Logs and telemetry:** no centralized logging or telemetry sample backend
  was added. The explicit unsupported responses remain intentional.
- This deployment does not establish compatibility with every OpenStack release,
  storage backend, policy configuration, or non-administrative role.

After the Heat fix, `uv run --no-sync python -m pytest -q tests` passed all 90
local tests. The SDK emitted 12 deprecated-field warnings. No commit or push
was performed as part of validation.
