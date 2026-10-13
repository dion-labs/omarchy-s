#!/usr/bin/env python3
"""Validate explicit attribution coverage; never infer licensing clearance."""
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
def check(root):
    plan = json.loads((root / 'packaging/source-export.allowlist.json').read_text())
    ledger = json.loads((root / 'packaging/source-attribution.json').read_text())
    rows = ledger['files']
    by_path = {row['path']: row for row in rows}
    if len(by_path) != len(rows):
        raise ValueError('Duplicate attribution path')
    selected = {row['path']: row for row in plan['files']}
    exceptions = ledger['coverage_exceptions']
    if set(by_path) & set(exceptions) or set(by_path) | set(exceptions) != set(selected):
        raise ValueError('Attribution coverage differs from export')
    if ledger['publication_cleared'] is not False or plan['publication_cleared'] is not False:
        raise ValueError('This review must not assert publication clearance')
    for path, row in selected.items():
        if hashlib.sha256((root / path).read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('Export hash drift: ' + path)
    origins = json.loads((root / 'packaging/source-origins.json').read_text())
    if origins['publication_cleared'] is not False:
        raise ValueError('Origin tracing cannot assert publication clearance')
    expected_patches = {path for path in selected if path.endswith('.patch')}
    if {row['path'] for row in origins['patches']} != expected_patches or len(origins['patches']) != len(expected_patches):
        raise ValueError('Patch provenance coverage differs')
    for row in origins['patches'] + origins['helpers']:
        if row['sha256'] != selected[row['path']]['sha256']:
            raise ValueError('Origin hash drift: ' + row['path'])
    vendor = json.loads((root / 'packaging/vendor-ancestry.json').read_text())
    history = json.loads((root / 'packaging/vendor-dts-history.json').read_text())
    external = json.loads((root / 'packaging/external-attribution.json').read_text())
    dtbh = json.loads((root / 'packaging/dtbh-build.lock.json').read_text())
    if any(x['publication_cleared'] is not False for x in (vendor, history, external)):
        raise ValueError('Vendor review cannot assert clearance')
    if vendor['vendor_archive_sha256'] != dtbh['files']['artifacts/header-provenance/vendor-source.tar.gz']:
        raise ValueError('Vendor archive pin drift')
    if history['pinned_blob'] != vendor['dts']['git_blob_sha1'] or history['path'] != vendor['dts']['path']:
        raise ValueError('DTS history identity mismatch')
    for path, row in by_path.items():
        digest = hashlib.sha256((root / path).read_bytes()).hexdigest()
        if row['sha256'] != digest or selected[path]['sha256'] != digest:
            raise ValueError('Attribution hash drift: ' + path)
        if not row['review'] or not row['category'] or not row['evidence']:
            raise ValueError('Missing attribution evidence: ' + path)
        for evidence in row['evidence']:
            if evidence not in selected:
                raise ValueError('Evidence absent from export: ' + evidence)
    reviews = ledger['exception_reviews']
    if set(reviews) != set(exceptions):
        raise ValueError('Exception disposition coverage differs')
    valid_categories = {'inherited-notice', 'inherited-patch', 'mixed-patch',
        'local-delta-on-inherited', 'generated-configuration', 'evidence-metadata',
        'local-review-text', 'local-integration-candidate'}
    valid_scopes = {'none', 'identified-delta-only', 'selection-only', 'local-expression-only'}
    for path, row in list(by_path.items()) + list(reviews.items()):
        if row['category'] not in valid_categories or row.get('original_scope') not in valid_scopes or not row.get('review'):
            raise ValueError('Missing/invalid per-file disposition: ' + path)
        if row['category'].startswith('inherited-') and row['original_scope'] != 'none':
            raise ValueError('Inherited content cannot be original scope: ' + path)
        if row['category'] in {'mixed-patch', 'local-delta-on-inherited'} and row['original_scope'] != 'identified-delta-only':
            raise ValueError('Patch scope must be limited to identified deltas: ' + path)
    for path, row in list(by_path.items()) + list(reviews.items()):
        expected_license = 'MIT' if row['original_scope'] != 'none' else None
        if row.get('original_license') != expected_license:
            raise ValueError('Original license scope mismatch: ' + path)
        if expected_license and row.get('original_copyright') != 'Copyright (c) 2026 DionLabs':
            raise ValueError('Original copyright holder mismatch: ' + path)
    if any(path.startswith('upstream/pmaports/main/dtbtool-exynos/') for path in selected):
        raise ValueError('Disputed dtbtool patch payload must not be exported')
    fb = origins['addition_review']['framebuffer']
    addition = json.loads((root / 'build/kernel-repro/additions.json').read_text())[fb['path']]
    if fb['identical'] is not True or fb['upstream_generated_sha256'] != fb['selected_sha256'] or fb['selected_sha256'] != addition['result_sha256']:
        raise ValueError('Framebuffer inheritance evidence differs')
    return {'reviewed_classifications': len(rows), 'explicit_exceptions': len(exceptions), 'per_file_dispositions': len(rows) + len(reviews), 'publication_cleared': False}
if __name__ == '__main__':
    print(json.dumps(check(ROOT), indent=2))
