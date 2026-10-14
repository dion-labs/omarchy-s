# Verify and compare saved acceptance evidence

Run the offline verifier from the same exported source release used for acceptance.
It reads local files only: no Docker, network, phone or desktop contact. Supply the
manifest and acceptance receipt hashes from a trusted record, not merely an
unchecked digest stored beside downloaded evidence.

```sh
python3 scripts/dependency-lab/verify-acceptance.py \
  --manifest /path/to/manifest.json --manifest-sha256 TRUSTED_MANIFEST_HASH \
  --builder-receipt /path/to/frontend-lab.json --stage /path/to/staged/rootfs \
  --evidence /path/to/first-results --receipt-sha256 TRUSTED_FIRST_RECEIPT_HASH
```

Add `--compare /path/to/second-results --compare-receipt-sha256 TRUSTED_SECOND_HASH`
to compare another run against those same source/runtime inputs. Both evidence sets
must verify independently. The comparison requires identical source, runtime and
per-suite results; it deliberately ignores duration and diagnostic log contents.
Each log still has to match its own trusted receipt's hash. A copied receipt or
same declared run ID is refused as evidence of independent reproduction.

The verifier checks exact source membership/hashes/modes, source/manifest receipt
identity, builder receipt and lock hashes, recorded image ID, staged portal hash,
all result/log hashes, exact evidence membership and strict per-suite counts.
It rejects duplicate JSON keys, missing/extra/linked artifacts, failed/running
receipts, skips, expected failures, mismatched summaries and totals. It does not
execute the image or recheck installed runtime executables; those were checked
by the acceptance run. Saved evidence alone cannot prove that execution happened.

New acceptance receipts use schema2 with a random run ID. Schema1 receipt shape
is understood, but the source/test registry must still match this verifier's release;
this is not automatic comparison across older releases or different test plans.
Missing IDs in legacy-shaped evidence do not establish independent execution.
A distinct ID is a declared run identity, not cryptographic host attestation.
The engine, producer and trusted receipt hashes remain trust inputs.

Eight new tests cover matching runs with different diagnostics, receipt/log/source/
runtime tampering, malformed or incomplete evidence, duplicate keys, summary drift,
copied runs and incompatible runtime contracts. The [acceptance command](PORTAL-ACCEPTANCE.md)
now runs155 tests (153 Linux and2 host). Two full runs of the exported source are
used for this release's reproduction check; logs and elapsed times may differ.

Next: use the consolidated evidence to define the smallest production integration
candidate and its rollback/adoption gates. Host lab acceptance alone must not enable
updates on the phone or claim physical/GPU acceptance.

The [first integration candidate](PORTAL-INTEGRATION-CANDIDATE.md) defines adoption
without payload replacement or service activation, with explicit rollback gates.
