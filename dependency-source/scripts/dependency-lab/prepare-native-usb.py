#!/usr/bin/env python3
"""Reconstruct pinned native USB owner source offline; never install or run it."""
import argparse
import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    'usb_service.py': ('f63d296d45035f2d6f0ecb4df88630e04a8f4d8276ce75529ace59c8777375d6', '9ce8fb54bcb9f9e8bd3546ff2e9832e489842965fea78876f727341cce3f224d'),
    'dock_service.py': ('e519d2cc014bd8783e281d8915fff3e61b0883b0a9ab6ea91b104d5757139b80', '93f8c91c73a16347b66912308a2de49955f54cfafbe247236926a7207c566ac0'),
}
PROFILES = """    '#19 SMP': '0985712534ee16fbf59a2c83ecd281fce734b5208997ce41c1c24f448bafbfe8',
    '#20 SMP': '0c73b00a99d603490c4ceed1c6b0a353a040beece205626653e8aea14b5033e3',
    '#21 SMP': '18ac22529463caf191c1f7be73374175df7a6bdd79146fbbc45e25c6a6c48aec',
"""
MODULE = "('/usr/local/lib/omarchy-native/s9p-dp-pll-native21.ko' if '#21 SMP' in Path('/proc/version').read_text() else ('/usr/local/lib/omarchy-native/s9p-dp-pll-native20.ko' if '#20 SMP' in Path('/proc/version').read_text() else ('/usr/local/lib/omarchy-native/s9p-dp-pll-native19.ko' if '#19 SMP' in Path('/proc/version').read_text() else '/var/tmp/s9p-dp-pll-lab.ko')))"

def sha(data):
    return hashlib.sha256(data).hexdigest()

def transform(name, data):
    before, after = SOURCES[name]
    if sha(data) != before:
        raise ValueError('Source drift: ' + name)
    source = data.decode('utf-8')
    if name == 'usb_service.py':
        marker = "    '#17 SMP': '0cfe7163d71e409d215b9c822ebcb7c66b86d522df5f157b04a8e4864c7b24a4',\n"
        if source.count(marker) != 1:
            raise ValueError('Profile marker mismatch')
        source = source.replace(marker, marker + PROFILES)
    marker = "'/var/tmp/s9p-dp-pll-lab.ko'"
    if source.count(marker) != 1:
        raise ValueError('Module marker mismatch')
    result = source.replace(marker, MODULE).encode('utf-8')
    ast.parse(result)
    if sha(result) != after:
        raise ValueError('Output pin mismatch: ' + name)
    return result

def prepare(root, output):
    if output.exists():
        raise ValueError('Output must not exist')
    results = {}
    for name in SOURCES:
        path = root / 'build/arch-arm/usb' / name
        if any(p.is_symlink() for p in [path, *path.parents]):
            raise ValueError('Symlink source')
        results[name] = transform(name, path.read_bytes())
    output.mkdir(parents=True)
    for name, data in results.items():
        (output / name).write_bytes(data)
        (output / name).chmod(0o644)
    receipt = {'schema': 1, 'outputs': {n: sha(d) for n, d in results.items()},
               'scope': 'Two pinned owner sources only; hardware helpers, kernel modules, readiness units and runtime validation are separate. No installation.'}
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(ROOT, args.output), indent=2))
