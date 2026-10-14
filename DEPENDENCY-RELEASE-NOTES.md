# Dependency-source preview 9

Updates now have an isolated admission wrapper that refuses active or unresolved
frontend/backend sessions, requests, media nodes and unknown clients. It also
refuses missing, stale, malformed or unresponsive inventories and changed fence
identity. Successful admission requires an adapter-owned exclusive fence that
prevents new clients/requests throughout apply or recovery.

## Validation

All 109 tests pass without skips from the extracted source archive. Twelve new
contract tests verify refusal without service stop or payload modification,
probe timeout, post-stop request races, fence loss, explicit recovery and hook
failure. One new real frontend capture test closes its tracked sessions/media
and still refuses update authorization: complete inventory and fencing are absent.
The previous 318 injected process exits are unchanged; no new crash-coverage claim.

Two normalized 73-file exports match, 72 attribution entries verify and source
links/privacy findings are reviewed. Earlier boot/desktop inventories and runtime
pins remain unchanged. No phone or live desktop was contacted.

## Limits and next step

Read the [admission contract](https://github.com/dion-labs/omarchy-s/blob/dependency-source-preview-9/dependency-source/PORTAL-ADMISSION-LAB.md).
The wrapper never cancels or force-closes clients. It rechecks after stopping,
before payload writes; a failed check requires explicit recovery under a fresh
fence/inventory. Adapter acquire/probe calls must be bounded and its fence must
survive relevant races and release safely after coordinator death. These are
adapter obligations, not guarantees supplied by the synchronous wrapper.

No production collector/fence adapter or live updater is enabled. Empty tracked
session lists cannot prove global quiescence. Next: implement and crash-test an
exclusive private-session admission adapter before production integration.
Phone GPU/wlr capture, chooser and physical acceptance remain separate.
