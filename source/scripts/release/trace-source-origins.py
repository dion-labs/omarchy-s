#!/usr/bin/env python3
"""Offline provenance measurements against hash-pinned archives; no device access."""
import argparse
import difflib
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tarfile
import tempfile
ROOT = Path(__file__).resolve().parents[2]
def sha(data):
    return hashlib.sha256(data).hexdigest()
def archive(path, expected, wanted=None):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    if h.hexdigest() != expected:
        raise ValueError('Archive hash mismatch: ' + path.name)
    result = {}
    with tarfile.open(path) as tar:
        for member in tar:
            if not member.isfile() or '/' not in member.name:
                continue
            name = member.name.split('/', 1)[1]
            if wanted is not None and name not in wanted:
                continue
            if name in result:
                raise ValueError('Duplicate source member')
            result[name] = tar.extractfile(member).read()
    return result

def targets(patch):
    names = re.findall(r'^--- a/(.+)$', patch, re.M)
    after = re.findall(r'^\+\+\+ b/(.+)$', patch, re.M)
    if not names or names != after:
        raise ValueError('Only same-path modifications supported')
    for name in names:
        if PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts or '\\' in name:
            raise ValueError('Unsafe patch target')
    return names

def apply(work, patch_name, sources, origin, expected=None):
    patch = ROOT / patch_name
    names = targets(patch.read_text())
    files = []
    for name in names:
        path = work / name
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(sources[name])
        data = path.read_bytes()
        files.append({'path': name, 'before_sha256': sha(data),
                      'observed_spdx': re.findall(r'SPDX-License-Identifier:\s*([^\r\n]+)', data.decode('utf-8', errors='replace'))})
    # git apply checks context without patch's fuzz matching. No repository needed.
    run = subprocess.run(['git', 'apply', '--check', str(patch)], cwd=work, capture_output=True, text=True)
    if run.returncode:
        raise ValueError(patch_name + ': ' + run.stderr)
    subprocess.run(['git', 'apply', str(patch)], cwd=work, check=True, capture_output=True)
    for row in files:
        row['after_sha256'] = sha((work / row['path']).read_bytes())
        if expected and row['after_sha256'] != expected[row['path']]:
            raise ValueError('Reconstructed result mismatch: ' + row['path'])
    return {'path': patch_name, 'sha256': sha(patch.read_bytes()), 'origin': origin,
            'context_application': 'git apply --check and apply passed', 'files': files,
            'license_concluded': 'NOASSERTION'}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.with_suffix('.residuals.json').exists():
        raise ValueError('Output must be new')
    pins = json.loads((ROOT / 'packaging/kernel-sources.lock.json').read_text())['packages']
    additions = json.loads((ROOT / 'build/kernel-repro/additions.json').read_text())
    dtbh = json.loads((ROOT / 'packaging/dtbh-build.lock.json').read_text())
    kernel_patches = ['build/kernel-repro/patches/native20-tracked.patch', 'build/boot-repro/preserve-weak-version.patch']
    wanted = {'drivers/gpu/drm/sysfb/simpledrm.c'}
    for name in kernel_patches:
        wanted.update(targets((ROOT / name).read_text()))
    sources = {}
    for entry in pins:
        sources[entry['name']] = archive(ROOT / 'artifacts/kernel-source-closure' / entry['filename'], entry['digest'], wanted if entry['name'] == 'linux' else None)
    dtbpath = 'artifacts/header-provenance/dtbtool-source.tar.gz'
    dtb = archive(ROOT / dtbpath, dtbh['files'][dtbpath])
    patches = []
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        for label in ['linux', 'additions', 'loader', 'dtbtool']:
            (base / label).mkdir()
        for name in kernel_patches:
            patches.append(apply(base / 'linux', name, sources['linux'], pins[0]))
        # Replay the reviewed upstream transformer in an isolated temporary tree.
        upstream_work = base / 'upstream-transform'
        upstream_work.mkdir()
        for name, data in sources['linux'].items():
            dest = upstream_work / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        generated = sources['linux']['drivers/gpu/drm/sysfb/simpledrm.c'].replace(b'simpledrm', b'exynos_bootfb').replace(b'#define DRIVER_NAME\t"exynos_bootfb"', b'#define DRIVER_NAME\t"exynos"').replace(b'DRM driver for simple-framebuffer platform devices', b'DRM driver for the framebuffer an Exynos bootloader leaves running')
        (upstream_work / 'drivers/gpu/drm/sysfb/exynos-bootfb.c').write_bytes(generated)
        transformer = sources['s9plus-port']['scripts/build/patch_tree.py']
        driver = base / 'patch_tree.py'
        driver.write_bytes(transformer)
        subprocess.run([sys.executable, str(driver), str(upstream_work)], check=True, capture_output=True)
        upstream_comparison = []
        for row in patches[0]['files']:
            name = row['path']
            upstream_data = (upstream_work / name).read_bytes()
            upstream_comparison.append({'path': name, 'upstream_generated_sha256': sha(upstream_data), 'native20_sha256': row['after_sha256'], 'identical': sha(upstream_data) == row['after_sha256'], 'residual_diff': ''.join(difflib.unified_diff(upstream_data.decode().splitlines(True), (base / 'linux' / name).read_text().splitlines(True), fromfile='port-generated/' + name, tofile='native20/' + name))})
        charger = sources['s9plus-port']['src/soc/max77705_charger.c'].replace(b'\r\n', b'\n')
        charger_final = (base / 'linux/drivers/power/supply/max77705_charger.c').read_bytes()
        port_copy_comparison = {'source': 'src/soc/max77705_charger.c', 'copy_recipe': 'scripts/build/apply_drivers.sh', 'source_sha256': sha(charger), 'native20_sha256': sha(charger_final), 'remaining_diff': ''.join(difflib.unified_diff(charger.decode().splitlines(True), charger_final.decode().splitlines(True), fromfile='port-charger', tofile='native20-charger'))}
        transformer_report = {'source': 'scripts/build/patch_tree.py', 'sha256': sha(transformer), 'files': upstream_comparison, 'meaning': 'Equal output proves these final bytes are reproduced by the pinned port transformer; unequal output requires separate delta review.'}
        for name, entry in additions.items():
            if not entry.get('patch'):
                continue
            if entry['source'].startswith('generated-from-linux:'):
                data = sources['linux']['drivers/gpu/drm/sysfb/simpledrm.c'].replace(b'simpledrm', b'exynos_bootfb').replace(b'#define DRIVER_NAME\t"exynos_bootfb"', b'#define DRIVER_NAME\t"exynos"').replace(b'DRM driver for simple-framebuffer platform devices', b'DRM driver for the framebuffer an Exynos bootloader leaves running')
            else:
                data = sources['s9plus-port'][entry['source']]
            if entry['normalize_crlf']:
                data = data.replace(b'\r\n', b'\n')
            if sha(data) != entry['source_sha256'] or sha((ROOT / entry['patch']).read_bytes()) != entry['patch_sha256']:
                raise ValueError('Addition input mismatch')
            patches.append(apply(base / 'additions', entry['patch'], {name: data}, {'source': entry['source'], 'preparation': 'build/kernel-repro/additions.json and scripts/kernel-repro/prepare-public.py'}, {name: entry['result_sha256']}))
        framebuffer = 'drivers/gpu/drm/sysfb/exynos-bootfb.c'
        upstream_fb = sha((upstream_work / framebuffer).read_bytes())
        selected_fb = sha((base / 'additions' / framebuffer).read_bytes())
        if upstream_fb != selected_fb:
            raise ValueError('Framebuffer delta no longer matches upstream transformer')
        addition_review = {'framebuffer': {'path': framebuffer,
            'upstream_generated_sha256': upstream_fb, 'selected_sha256': selected_fb,
            'identical': True, 'source': 'scripts/build/patch_tree.py'},
            'board_switches': {'source': 'scripts/build/build71.sh',
                'source_sha256': sha(sources['s9plus-port']['scripts/build/build71.sh']),
                'inspection': 'UFS, DECON, GPU, WLAN enablement mirrors upstream feature switches; USB OTG role-switch hunk is a separate local candidate delta.'}}
        loader = {k[len('bootloader/uniLoader/'):]: v for k, v in sources['s9plus-port'].items() if k.startswith('bootloader/uniLoader/')}
        patches.append(apply(base / 'loader', 'build/mainline/loader/checkpoints.patch', loader, pins[1]))
        for name, digest in sorted(dtbh['files'].items()):
            if not name.endswith('.patch'):
                continue
            if sha((ROOT / name).read_bytes()) != digest:
                raise ValueError('dtbtool patch mismatch')
            patches.append(apply(base / 'dtbtool', name, dtb, {'source': dtbh['sources']['dtbtool'], 'pmaports_commit': dtbh['pmaports_commit']}))
    helpers = []
    candidates = {}
    for name, data in sources['s9plus-port'].items():
        if len(data) > 1000000 or b'\0' in data:
            continue
        if not (name.endswith('.sh') or data.startswith(b'#!/bin/sh') or data.startswith(b'#!/bin/bash')):
            continue
        candidates[name] = data.decode('utf-8', errors='replace').splitlines()
    paths = ['build/mainline/diagnostic/init', 'build/mainline/diagnostic/root-layout.sh', 'build/mainline/diagnostic/usb-console.sh', 'build/arch-arm/native-boot/root-layout.sh', 'build/arch-arm/native-boot/transition.sh']
    for name in paths:
        data = (ROOT / name).read_bytes()
        lines = data.decode().splitlines()
        matches = []
        for upstream, other in candidates.items():
            match = difflib.SequenceMatcher(None, lines, other, autojunk=False).find_longest_match(0, len(lines), 0, len(other))
            if match.size >= 3:
                matches.append({'source': upstream, 'local_line': match.a + 1, 'source_line': match.b + 1, 'consecutive_lines': match.size})
        helpers.append({'path': name, 'sha256': sha(data), 'exact_file_matches': [n for n in candidates if sources['s9plus-port'][n] == data], 'longest_blocks': sorted(matches, key=lambda x: (-x['consecutive_lines'], x['source']))[:5], 'license_concluded': 'NOASSERTION'})
    report = {'schema': 1, 'scope': 'Pinned source context and bounded helper comparison; not proof of original authorship', 'sources': pins, 'helper_candidate_count': len(candidates), 'patches': patches, 'upstream_transformer': transformer_report, 'port_charger': port_copy_comparison, 'addition_review': addition_review, 'helpers': helpers, 'publication_cleared': False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    residuals = {row['path']: row.pop('residual_diff') for row in report['upstream_transformer']['files'] if 'residual_diff' in row}
    residuals['charger-versus-port-copy'] = report['port_charger'].pop('remaining_diff')
    args.output.with_suffix('.residuals.json').write_text(json.dumps(residuals, indent=2) + '\n')
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'patches': len(patches), 'helpers': len(helpers), 'helper_candidates': len(candidates)}))
if __name__ == '__main__':
    main()
