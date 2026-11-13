# Repository instructions

These instructions supplement the user's global guidelines. They do not authorize
Git writes, external publication, or changes to existing cloud resources.

## Keep the documentation structure

README.md is the first page a new visitor reads. Keep it short and in this order:
what the project is, what it can do, the Quick Start, and pointers to details.

- The Quick Start covers only Claude Desktop with the `.mcpb` bundle and OpenWebUI
  with Docker Compose. Keep it condensed and runnable; put other installation
  types, full settings, and troubleshooting in the matching `docs/` guide and
  link to it.
- When behavior, settings, or installation steps change, update the affected
  `docs/` guides as well as README.md, and keep their links and anchors valid.
  `mcpb/manifest.json` links to the repository page's `#claude-desktop-integration`
  anchor; keep `<a id="claude-desktop-integration"></a>` in both README.md and
  README.ko.md.
- Whenever authentication methods, auth settings, or client support change,
  update the **Authentication support by client** table in `docs/security.md`
  (status date, source revision, rows, Status, Notes) and README.md's short
  pointer section, in both languages. Mark paths without a live check as
  **Live unverified**.

## Keep English and Korean documents in sync

Every Markdown document in README.md and `docs/` exists in two languages:
`<name>.md` in English, the default, and `<name>.ko.md` in Korean with the same
content. `docs/issues/` is outside this rule.

- Whenever you change a document, apply the same change to its other-language
  file in the same change set, so that both state the same facts, steps, values,
  tables, and Status/Notes.
- Create every new document as an English `.md` and a Korean `.ko.md` pair.
- The first line of each file is a language switcher: `**English** | [Korean](<name>.ko.md)`
  in the English file and `[English](<name>.md) | **Korean**` in the Korean file.
- Translate prose only. Keep commands, code blocks, configuration keys, tool and
  action names, and the mapping's Status values (`✅`, `⚠️ Live unverified`,
  `❌ Not implemented`, ...) identical in both languages.
- Links in a Korean file point to the Korean version of other documents
  (`*.ko.md`) and to the anchors generated from their Korean headings. After
  editing, check that every relative link and anchor resolves in both languages.

## Maintain the CLI-to-tool mapping and validation records

For every improvement or fix, review README.md's **OpenStack CLI vs MCP Tools
Mapping** section and `docs/validation.md`. Keep the mapping's tool rows, Status, and
Notes, and the validation records in `docs/validation.md`, consistent with the
resulting implementation and actual verification. README.md keeps only a short
pointer to `docs/validation.md`, not the dated records themselves.

- Update affected rows whenever tools, actions, parameters, prerequisites,
  permissions, limitations, or behavior change. Use registered tool names and
  supported actions; do not advertise missing tools or unimplemented actions.
- Distinguish implementation from verification. Mark implemented paths without
  successful live validation as **Live unverified**, with the specific reason.
  Missing services/APIs, policy denials, failures, and timeouts are not passes.
  Keep intentional capability limitations and unimplemented actions explicit.
- In `docs/validation.md`, keep **Live tool checks** and **Local unit tests** in separate
  summary groups.
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
- Keep `docs/` for reusable user guidance, plus the validation records in
  `docs/validation.md`. Do not create other issue-specific reports, dated test
  results, or evidence JSON in `docs/`, or embed those records in usage guides.
  Report case-specific verification results, limits, failures, and cleanup in
  chat unless the user explicitly requests a separate artifact; put such a
  requested report in `docs/issues/`, the only place for one. Never expose
  credentials, private endpoints, or sensitive resource data. Dated validation
  summaries belong only in `docs/validation.md`; README.md may link to
  `docs/validation.md` but not to other reports.
- Before completion, check summary arithmetic, percentages, tool/action names,
  Status/Notes, source identity, and evidence links in README.md and
  `docs/validation.md` for agreement, and confirm that README.ko.md and
  `docs/validation.ko.md` carry the same information.

## Maintain the MCP server instructions

`src/mcp_openstack_ops/server_instructions.md` is sent to every client in the
MCP initialize response and enters the model's context as-is.

- Keep only rules that span several tools, such as scope, opt-in switches,
  result reporting, async semantics, and confirmation. Put tool-specific
  behavior in the tool's docstring and parameter descriptions.
- Keep it under 4,096 characters; `tests/test_server_instructions.py` checks
  the limit. Write short imperative English. The file is English only and is
  outside the bilingual document rule.
- Every tool name, parameter, and environment variable it mentions must match
  the registered tools and settings. When a change renames or removes them, or
  changes a cross-tool rule, update this file in the same change set.
- Never include credentials, private endpoints, or environment-specific data.
- After changing it, run the unit tests and record the result in
  `docs/validation.md` and its Korean copy, following the rules above.
