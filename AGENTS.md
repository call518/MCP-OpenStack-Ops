# Repository instructions

These instructions supplement the user's global guidelines. They do not authorize
Git writes, external publication, or changes to existing cloud resources.

## Maintain the CLI-to-tool mapping and validation snapshot

For every improvement or fix, review README.md's **OpenStack CLI vs MCP Tools
Mapping** section. Keep its summary, tool rows, Status, Notes, and linked evidence
consistent with the resulting implementation and actual verification.

- Update affected rows whenever tools, actions, parameters, prerequisites,
  permissions, limitations, or behavior change. Use registered tool names and
  supported actions; do not advertise missing tools or unimplemented actions.
- Distinguish implementation from verification. Mark implemented paths without
  successful live validation as **Live unverified**, with the specific reason.
  Missing services/APIs, policy denials, failures, and timeouts are not passes.
  Keep intentional capability limitations and unimplemented actions explicit.
- Keep **Live tool checks** and **Local unit tests** in separate summary groups.
  Live classifications count unique tools; unit tests count test cases. Multiple
  tests for one tool do not increase the unique-tool count. Keep classification
  totals consistent with the stated inventory and scope.
- Show unit-test results concisely as `160/160 (100%)`, using the actual results,
  not this example's values. Account for failures and skipped tests separately
  when present; do not count skipped tests as passes. Do not treat unit-test
  success as proof of live service functionality.
- Run relevant verification after functional changes. Update dates, source
  revision or working-tree identity, counts, percentages, and evidence links only
  from checks actually performed. Do not present an older snapshot as validation
  of newer code. Mark affected paths as unverified or the snapshot as outdated
  when validation cannot be repeated.
- Replace a complete live summary only after repeating its stated coverage.
  Label targeted retests as partial; do not extrapolate them to the full toolset.
  Document polling limits and distinguish accepted requests from confirmed final
  resource states. Explain changes in test conditions that affect comparisons.
- Keep dated reports as historical evidence and link the latest applicable
  report from README.md. Reports must state verification limits, observed
  failures, and cleanup results without exposing credentials, private endpoints,
  or sensitive resource data.
- Before completion, check summary arithmetic, percentages, tool/action names,
  Status/Notes, source identity, and evidence links for agreement. If README.ko.md
  exists, maintain equivalent information in both README files.
