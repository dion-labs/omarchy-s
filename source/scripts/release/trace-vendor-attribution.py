#!/usr/bin/env python3
"""Measure pinned vendor/port ancestry without device access or source execution."""
import argparse
import hashlib
import json
import re
import tarfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
def sha(data):
    return hashlib.sha256(data).hexdigest()
def selected(archive, digest, paths):
    h = hashlib.sha256()
    with archive.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    if h.hexdigest() != digest:
        raise ValueError('Archive hash mismatch')
    found = {}
    with tarfile.open(archive) as tar:
        for member in tar:
            if not member.isfile() or '/' not in member.name:
                continue
            name = member.name.split('/', 1)[1]
            if name in paths:
                if name in found:
                    raise ValueError('Duplicate archive member')
                found[name] = tar.extractfile(member).read()
    if set(found) != set(paths):
        raise ValueError('Missing required source member')
    return found

def measure(root):
    lock = json.loads((root / 'packaging/dtbh-build.lock.json').read_text())
    source_lock = json.loads((root / 'packaging/kernel-sources.lock.json').read_text())
    port_pin = next(p for p in source_lock['packages'] if p['name'] == 's9plus-port')
    dts = 'arch/arm64/boot/dts/exynos/exynos9810-star2lte_eur_open_26.dts'
    vendor_ufs = ['drivers/scsi/ufs/ufs-cal-9810.' + ext for ext in ('c', 'h')]
    port_ufs = ['src/ufs/ufs-cal-9810.' + ext for ext in ('c', 'h')]
    refs = ['drivers/i2c/busses/i2c-exynos5.c', 'drivers/net/wireless/bcmdhd_100_15/dhd_msgbuf.c', 'drivers/net/wireless/bcmdhd_100_15/dhd_pcie.c']
    archive = 'artifacts/header-provenance/vendor-source.tar.gz'
    vendor = selected(root / archive, lock['files'][archive], [dts] + vendor_ufs + refs)
    port = selected(root / 'artifacts/kernel-source-closure' / port_pin['filename'], port_pin['digest'], port_ufs)
    data = vendor[dts]
    text = data.decode()
    references = []
    patterns = ['ipclk / (op_clk * 15)', '9 * ipclk', '7 * ipclk', 'epoch = ring->seqnum % H2D_EPOCH_MODULO', 'bus->dongle_ram_base = CR4_4347_RAM_BASE']
    for name in refs:
        payload = vendor[name]
        references.append({'member': name, 'sha256': sha(payload), 'matching_lines': [{'line': i, 'pattern': pattern} for i, line in enumerate(payload.decode().splitlines(), 1) for pattern in patterns if pattern in line], 'license_concluded': 'NOASSERTION'})
    for name, notice in [(refs[0], 'vendor-i2c-exynos5-notice.txt'), (refs[1], 'vendor-dhd-msgbuf-notice.txt')]:
        payload = vendor[name]
        expected = payload[:payload.index(b'*/') + 2] + b'\n'
        if (root / 'open-source/licenses' / notice).read_bytes() != expected:
            raise ValueError('Retained vendor notice differs')
    return {'schema': 1, 'vendor_references': references, 'publication_cleared': False,
            'vendor_archive_sha256': lock['files'][archive], 'vendor_url': lock['sources']['vendor'],
            'port_archive_sha256': port_pin['digest'],
            'dts': {'path': dts, 'sha256': sha(data), 'git_blob_sha1': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest(),
                    'bytes': len(data), 'starts_with_dts_directive': text.startswith('/dts-v1/;'),
                    'include_directives': len(re.findall(r'^\s*(?:#\s*include|/include/)', text, re.M)),
                    'cpp_line_markers': len(re.findall(r'^\s*#\s*(?:line\s+)?\d+', text, re.M)),
                    'observed_spdx': re.findall(r'SPDX-License-Identifier:\s*([^\r\n]+)', text),
                    'copyright_marker_count': len(re.findall('copyright', text, re.I)),
                    'interpretation': 'Flattened-looking source; these measurements do not prove decompilation origin or license.'},
            'ufs': [{'vendor_member': v, 'port_member': p, 'vendor_sha256': sha(vendor[v]), 'port_sha256': sha(port[p]), 'byte_identical': vendor[v] == port[p], 'license_concluded': 'NOASSERTION'} for v, p in zip(vendor_ufs, port_ufs)]}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('Output must be new')
    result = measure(ROOT)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'dts_sha256': result['dts']['sha256'], 'ufs_exact_matches': sum(x['byte_identical'] for x in result['ufs'])}))
if __name__ == '__main__':
    main()
