#!/usr/bin/env python3
"""Run one unittest module and emit structured, fail-closed results."""
import argparse
import importlib.util
import json
from pathlib import Path
import unittest

def main():
 p=argparse.ArgumentParser();p.add_argument('file',type=Path);p.add_argument('output',type=Path);args=p.parse_args()
 spec=importlib.util.spec_from_file_location('acceptance_case',args.file);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
 result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(module))
 data=dict(tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),
           expected_failures=len(result.expectedFailures),unexpected_successes=len(result.unexpectedSuccesses))
 tmp=args.output.with_suffix('.tmp');tmp.write_text(json.dumps(data,sort_keys=True)+'\n');tmp.replace(args.output)
 raise SystemExit(0 if result.wasSuccessful() and not result.skipped and not result.expectedFailures else 1)
if __name__=='__main__':main()
