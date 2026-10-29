#!/usr/bin/env python3
"""Validate recorded handoff coverage; semantic coverage needs independent review."""
import hashlib
import json
import sys
from pathlib import Path

STAGES = {'product', 'interaction', 'flows', 'cases', 'final'}


def check(data, base, require_baseline=False):
    errors = []
    def need(ok, message):
        if not ok:
            errors.append(message)
    need(bool(data.get('revision')), 'missing revision')
    need(data.get('state') in {'draft', 'reviewed'}, 'invalid state')
    artifacts = {}
    for row in data.get('artifacts', []):
        aid = row.get('id')
        need(bool(aid) and aid not in artifacts, 'missing/duplicate artifact id')
        artifacts[aid] = row
        need(row.get('revision') == data.get('revision'), f'{aid}: revision mismatch')
        p = base / row.get('path', '')
        need(p.is_file(), f'{aid}: missing file')
        if p.is_file():
            need(hashlib.sha256(p.read_bytes()).hexdigest() == row.get('sha256'), f'{aid}: stale hash')
    standard = artifacts.get(data.get('standard_artifact_id'), {})
    standard_path = base / standard.get('path', '')
    need(bool(standard) and standard_path.is_file(), 'missing downstream coverage standard')
    expected = {}
    standard_data = {}
    if standard and standard_path.is_file():
        standard_data = json.loads(standard_path.read_text())
        for row in standard_data.get('continuity_requirements', []):
            key = row.get('id')
            stages = row.get('required_stages', [])
            need(bool(key) and key not in expected and bool(stages) and set(stages) <= STAGES,
                 'invalid/duplicate standard requirement')
            expected[key] = set(stages)
    need(bool(expected), 'empty downstream coverage standard')
    ids = set()
    need(bool(data.get('items')), 'missing coverage items')
    for row in data.get('items', []):
        key = row.get('id')
        need(bool(key) and key not in ids, 'missing/duplicate item id')
        ids.add(key)
        need(row.get('source_artifact_id') in artifacts and bool(row.get('source_locator')), f'{key}: missing source')
        required = row.get('required_stages', [])
        need(bool(required) and set(required) <= STAGES, f'{key}: invalid required stages')
        need(key in expected and set(required) == expected.get(key), f'{key}: required stages differ from downstream standard')
        stages = row.get('stages', {})
        need(set(stages) == STAGES, f'{key}: missing/unknown stage')
        for stage, entry in stages.items():
            label = f'{key}/{stage}'
            disposition = entry.get('disposition')
            need(disposition in {'carried', 'reference', 'not-applicable', 'blocked'}, f'{label}: invalid disposition')
            if stage in required:
                need(disposition == 'carried', f'{label}: required content omitted')
            if disposition in {'carried', 'reference'}:
                refs = entry.get('artifact_ids', [])
                need(bool(refs) and set(refs) <= set(artifacts), f'{label}: missing target')
                need(bool(entry.get('locator')), f'{label}: missing locator')
                if stage == 'flows' and disposition == 'carried':
                    loc = entry.get('locator')
                    need(isinstance(loc, dict) and all(loc.get(k) for k in ['user-flow', 'business-flow']), f'{label}: missing diagram locator')
            else:
                need(bool(entry.get('reason')), f'{label}: missing reason')
                if data.get('state') == 'reviewed':
                    need(disposition != 'blocked', f'{label}: unresolved block')
    need(ids == set(expected), 'coverage items differ from downstream standard')
    if require_baseline or data.get('continuity_version') == 2:
        need(data.get('continuity_version') == 2, 'current project requires continuity_version 2')
        raw = {}
        for row in standard_data.get('raw_requirements', []):
            key = row.get('id')
            need(bool(key) and key not in raw, 'missing/duplicate raw requirement id')
            need(row.get('source_artifact_id') in artifacts and bool(row.get('source_locator')),
                 f'{key}: raw requirement source missing')
            raw[key] = row
        need(bool(raw), 'frozen raw requirements missing')
        decisions = {}
        for row in data.get('requirement_decisions', []):
            key = row.get('id')
            need(bool(key) and key not in decisions, 'missing/duplicate requirement decision id')
            decisions[key] = row
            disposition = row.get('decision')
            need(disposition in {'adopted', 'merged', 'replaced', 'deferred', 'not-applicable'},
                 f'{key}: invalid requirement decision')
            need(bool(row.get('owner')) and bool(row.get('reason')), f'{key}: decision owner/reason missing')
            need(row.get('evidence_artifact_id') in artifacts and bool(row.get('evidence_locator')),
                 f'{key}: decision evidence missing')
            targets = row.get('item_ids', [])
            successors = row.get('successor_ids', [])
            need(isinstance(targets, list) and isinstance(successors, list), f'{key}: invalid decision references')
            targets = targets if isinstance(targets, list) else []
            successors = successors if isinstance(successors, list) else []
            if disposition == 'adopted':
                need(bool(targets) and set(targets) <= ids and not successors,
                     f'{key}: adopted requirement lacks known implementation items')
            elif disposition in {'merged', 'replaced'}:
                need(bool(successors) and set(successors) <= set(raw) and not targets,
                     f'{key}: missing/unknown successor requirement')
            else:
                need(not targets and not successors, f'{key}: inactive requirement has active targets')
        need(set(decisions) == set(raw), 'requirement decisions differ from frozen raw requirements')
        def reaches_adopted(key, trail):
            if key in trail:
                need(False, f'{key}: requirement inheritance cycle')
                return False
            row = decisions.get(key, {})
            if row.get('decision') == 'adopted':
                return True
            if row.get('decision') not in {'merged', 'replaced'}:
                return False
            successors = row.get('successor_ids', [])
            return bool(successors) and all(reaches_adopted(n, trail | {key}) for n in successors)
        for key, row in decisions.items():
            if row.get('decision') in {'merged', 'replaced'}:
                need(reaches_adopted(key, set()), f'{key}: inheritance does not resolve to adopted requirement')
    return errors


if __name__ == '__main__':
    try:
        path = Path(sys.argv[1]).resolve()
        errors = check(json.loads(path.read_text()), path.parent, require_baseline='--require-baseline' in sys.argv[2:])
    except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
        errors = [f'invalid continuity record: {exc}']
    print(json.dumps({'status': 'FAIL' if errors else 'PASS', 'errors': errors}, ensure_ascii=False, indent=2))
    sys.exit(bool(errors))
