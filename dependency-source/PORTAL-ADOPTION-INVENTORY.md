# Read-only portal inventory and offline adoption planning

This implements the first observation step of the [integration candidate](PORTAL-INTEGRATION-CANDIDATE.md).
It does not write an owner receipt, alter payloads, contact a phone, inspect processes,
activate services or authorize a commit. Equal bytes still do not imply ownership.
The existing update planner continues to refuse unowned files.

## Run in a private Linux fixture

Use a trusted exported source tree and a mounted private root containing the three
portal payload files. Keep observations outside that root, private and out of source
exports. The collector prints JSON to stdout; it never creates an output directory,
lock, receipt or missing target parent. Do not redirect stdout into the observed root.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/dependency-lab/portal-adoption.py inventory \
  --root /absolute/private-fixture > /private/evidence/inventory.json
PYTHONDONTWRITEBYTECODE=1 python3 scripts/dependency-lab/portal-adoption.py plan \
  --inventory /private/evidence/inventory.json \
  --stage-receipt /private/verified-stage/ownership.json
```

`--baseline /private/evidence/earlier-inventory.json` additionally refuses any
recorded file or parent drift, including metadata and identity changes. A different
observation ID alone is not drift. Neither IDs nor digests authenticate observations.
The supplied stage receipt is an explicit input, not automatically trusted: bind it
to the candidate's exact three pins and verified build/source evidence separately.
Synthetic fixtures use synthetic receipts; success is not device compatibility.

## Observation contract

Linux is required. Every root-path and target-parent component is opened as a
no-follow directory. Only the three known payload files and proposed ownership
sidecar are read; no directory enumeration, process scan or network access occurs.
Files must be singly linked regular files, at most 64 MiB, with at most 256 KiB of
extended attribute names/values. Files use `O_NOATIME` without a fallback; insufficient
ownership/capability refuses rather than changing payload access times. Python import
bytecode writing is disabled. Source/interpreter reads are outside this payload
atime guarantee. Filesystem read errors fail closed; no repair is attempted.

The report records file device/inode, full mode, uid/gid, links, size, nanosecond
atime/mtime/ctime, hash and xattrs. Parent stat identities and missing parent chains
are explicit. Two bounded observations must agree, with open-file/path identity
checks and final root-path revalidation. This detects the exercised races; it is
not an atomic filesystem snapshot or an exclusive lock. Parent ACL/xattr, mount
options, filesystem health, free space and device identity are not collected.

## Plan contract and limits

The offline planner validates complete observation shape and ancestry, refuses
missing/mixed payloads, wrong modes, an existing sidecar (even matching), observed
cross-filesystem boundaries and optional baseline drift. Missing receipt parents
are listed as a proposal, never created. File identities must match all three
entries of the supplied stage receipt. Plans preserve every payload entry and have
`activation: none`, no payload mutations, and `commit_authorized: false`.

Source/runtime trust, device/filesystem health, running-process identity if present,
external ownership registries, durable baseline/journal, private crash rehearsal and
exclusive commit revalidation all remain gates. Absence of this proposed sidecar
is not proof that another package manager does not own the files. A saved plan is
not a durable byte backup, a production installation command or proof of freshness.

## Validation

Twelve Linux fixture tests cover exact match and no payload metadata changes,
missing receipt parents, existing parents and baseline comparison, missing/mixed
files, modes and sidecar conflicts, symlinks/hardlinks/FIFOs, ancestor/root links,
size and no-atime permission refusal, between-scan drift, replacement during read,
xattr baseline drift, malformed/incomplete/cross-device records, and preservation
of the existing unowned-file refusal rule. They run in the exported acceptance suite.
No physical result or device observation is claimed.

Next: a private-root metadata-only writer with durable baseline and crash/rollback
rehearsal. Then collect concrete device/process evidence before any device commit.
