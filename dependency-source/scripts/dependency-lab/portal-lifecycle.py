#!/usr/bin/env python3
"""Isolated lifecycle contract laboratory; no real service adapter or activation CLI."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('portal_transaction', Path(__file__).with_name('portal-transaction.py'))
tx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tx)


def checkpoint(label):
    """Process-interruption test hook."""


def require(value, message):
    if value is not True:
        raise RuntimeError(message)


def expected(journal, version):
    return {row['target']: tx.identity(row[version]) for row in journal['entries'][:-1]}


def phase(txfd, journal, value):
    journal['lifecycle'] = {'schema': 1, 'phase': value}
    tx.save(txfd, journal)
    checkpoint('lifecycle:'+value)


def stopped(hooks):
    require(hooks.quiesce(), 'Quiesce failed; explicit lifecycle recovery required')
    checkpoint('service:quiesced')
    require(hooks.stopped(), 'Service or clients still active; refusing file mutation')
    checkpoint('service:stopped')


def started(hooks, identity):
    require(hooks.start(identity), 'Service start failed; explicit lifecycle recovery required')
    checkpoint('service:started')
    require(hooks.healthy(identity), 'Service health failed; explicit lifecycle recovery required')
    checkpoint('service:healthy')


def apply(root, hooks):
    """Upgrade an already-owned running fixture; any failure requires recover()."""
    with tx.transaction(root) as (fd, txfd, journal):
        if journal['state'] != 'prepared' or 'lifecycle' in journal:
            raise ValueError('Expected fresh prepared transaction')
        if any(row['old'] is None for row in journal['entries']):
            raise ValueError('Lifecycle lab requires an existing owned installation')
        if any(tx.snapshot(fd, row['target'])[1] != row['old'] for row in journal['entries']):
            raise ValueError('Partial update requires recovery')
        # No side-effecting hook may run before durable recovery intent exists.
        require(hooks.healthy(expected(journal, 'old')), 'Existing service is not healthy')
        phase(txfd, journal, 'stopping')
        stopped(hooks)
        phase(txfd, journal, 'applying')
        def health():
            phase(txfd, journal, 'starting-new')
            started(hooks, expected(journal, 'new'))
            return True
        tx.apply_locked(fd, txfd, journal, health)
        phase(txfd, journal, 'committed')
        return journal


def recover(root, hooks):
    """Stop the fixture before restoring files, then prove old-service health."""
    with tx.transaction(root) as (fd, txfd, journal):
        value = journal.get('lifecycle')
        if not isinstance(value, dict) or value.get('schema') != 1 or value.get('phase') not in (
                'stopping', 'applying', 'starting-new', 'committed',
                'recovering', 'starting-old', 'restored'):
            raise ValueError('Missing or invalid lifecycle recovery intent')
        if any(row['old'] is None for row in journal['entries']):
            raise ValueError('Missing prior owned installation')
        phase(txfd, journal, 'recovering')
        stopped(hooks)
        tx.recover_locked(fd, txfd, journal)
        phase(txfd, journal, 'starting-old')
        started(hooks, expected(journal, 'old'))
        # A callback cannot authorize changed target bytes/metadata.
        tx.load(fd, txfd)
        if any(tx.snapshot(fd, row['target'])[1] != row['old'] for row in journal['entries']):
            raise RuntimeError('Restored files changed during service recovery')
        phase(txfd, journal, 'restored')
        return journal
