#!/usr/bin/env python3
"""Check discovery records and evidence references, not product semantics."""
import hashlib
import json
import sys
from pathlib import Path


def check(data, base):
    errors = []

    def require(ok, message):
        if not ok:
            errors.append(message)

    def nonempty(row, keys, label):
        for key in keys:
            require(bool(row.get(key)), f'{label}: missing {key}')

    nonempty(data, ['revision', 'run_mode', 'source_files', 'capabilities',
                    'candidates', 'lens_review', 'omission_review'], 'discovery')
    require(data.get('run_mode') in {'live-query', 'evidence-replay', 'definition-only'},
            'invalid run_mode')
    version = data.get('discovery_version', 1)
    require(version in {1, 2}, 'unsupported discovery_version')
    groups = {}
    for key in ['capabilities', 'platform_dependencies', 'candidates']:
        rows = data.get(key, [])
        ids = [r.get('id') for r in rows]
        require(all(ids) and len(ids) == len(set(ids)) if rows else key == 'platform_dependencies',
                f'{key}: missing/duplicate id')
        groups[key] = {r.get('id'): r for r in rows}
    for row in data.get('source_files', []):
        nonempty(row, ['path', 'sha256', 'source_date'], 'source')
        path = base / row.get('path', '')
        require(path.is_file(), f'evidence file missing: {path}')
        if path.is_file():
            require(hashlib.sha256(path.read_bytes()).hexdigest() == row.get('sha256'),
                    f'evidence hash mismatch: {path}')
    for row in data.get('capabilities', []):
        nonempty(row, ['source', 'verification', 'limits'], str(row.get('id')))
    for row in data.get('platform_dependencies', []):
        nonempty(row, ['source', 'status', 'fallback'], str(row.get('id')))
        require(row.get('status') in {'confirmed', 'unverified'}, 'invalid platform status')
    candidates = groups['candidates']
    included = {i for i, r in candidates.items() if r.get('decision') == 'include'}
    require(bool(included), 'no included candidates')
    for row in candidates.values():
        label = str(row.get('id'))
        nonempty(row, ['name', 'need', 'demand', 'decision', 'reason', 'limits'], label)
        demand = row.get('demand', {})
        require(demand.get('kind') in {'user-request', 'observed', 'research', 'hypothesis'},
                f'{label}: invalid demand kind')
        require(bool(demand.get('source')), f'{label}: missing demand source')
        require(row.get('decision') in {'include', 'merge', 'rule', 'gap', 'reject'},
                f'{label}: invalid decision')
        for cap in row.get('capabilities', []):
            require(cap in groups['capabilities'], f'{label}: unknown capability {cap}')
        for dep in row.get('platform_dependencies', []):
            require(dep in groups['platform_dependencies'], f'{label}: unknown platform dependency {dep}')
        if row.get('decision') == 'include':
            nonempty(row, ['capabilities', 'end_condition', 'voice_fit', 'readiness'], label)
            require(row.get('priority') in {'P0', 'P1', 'P2'}, f'{label}: invalid priority')
            require(row.get('readiness') in {'query-supported', 'definition-supported-pending-validation'},
                    f'{label}: invalid readiness')
        if row.get('decision') in {'merge', 'rule'}:
            targets = row.get('target_ids', [])
            require(bool(targets) and set(targets) <= included, f'{label}: invalid target_ids')
    if version == 2:
        errors.extend(check_routes_and_steps(data, groups))
    for row in data.get('baseline_mapping', []):
        require(bool(row.get('old_id')) and bool(row.get('change')) and bool(row.get('reason')),
                'incomplete baseline mapping')
        targets = row.get('target_ids', [])
        require(bool(targets) and set(targets) <= set(candidates), 'unknown baseline mapping target')
    return errors


ROUTES = {'atomic', 'high-frequency', 'orchestration', 'developer-examples'}
OPERATIONS = {'filter', 'sort', 'calculate', 'compare', 'summarize', 'group', 'join', 'plan'}


def check_routes_and_steps(data, groups):
    """Version 2 checks provenance coverage and typed steps; meaning needs review."""
    errors = []
    routes = data.get('demand_routes', {})
    if not isinstance(routes, dict) or set(routes) != ROUTES:
        return ['demand_routes: require exactly the four discovery routes']
    candidates = groups['candidates']
    reverse = {key: set() for key in ROUTES}
    for row in candidates.values():
        label = str(row.get('id'))
        sources = row.get('discovery_sources', [])
        if (not isinstance(sources, list) or not sources
                or any(source not in ROUTES for source in sources)
                or len(sources) != len(set(sources))):
            errors.append(f'{label}: invalid discovery_sources')
        else:
            for source in sources:
                reverse[source].add(row['id'])
        steps = row.get('steps', [])
        if row.get('decision') == 'include' and (not isinstance(steps, list) or not steps):
            errors.append(f'{label}: included candidate needs steps')
        if not isinstance(steps, list):
            errors.append(f'{label}: steps must be a list')
            continue
        ids = [step.get('id') for step in steps]
        if steps and (not all(ids) or len(ids) != len(set(ids))):
            errors.append(f'{label}: missing/duplicate step id')
        for step in steps:
            name = f"{label}/{step.get('id')}"
            for key in ['rule', 'result', 'limits']:
                if not step.get(key):
                    errors.append(f'{name}: missing {key}')
            inputs = step.get('inputs')
            if not isinstance(inputs, list) or not inputs or not all(inputs):
                errors.append(f'{name}: inputs must be a nonempty list')
            kind = step.get('kind')
            if kind not in {'external', 'derive', 'pa'}:
                errors.append(f'{name}: invalid kind')
            cap = step.get('capability_id')
            dep = step.get('dependency_id')
            if cap is not None and (cap not in groups['capabilities'] or cap not in row.get('capabilities', [])):
                errors.append(f'{name}: capability_id absent from candidate/inventory')
            if dep is not None and (dep not in groups['platform_dependencies'] or dep not in row.get('platform_dependencies', [])):
                errors.append(f'{name}: dependency_id absent from candidate/inventory')
            if kind == 'external' and not cap:
                errors.append(f'{name}: external step needs capability_id')
            if kind == 'pa' and not dep:
                errors.append(f'{name}: pa step needs dependency_id')
            if kind == 'derive':
                if 'capability_id' in step:
                    errors.append(f'{name}: derive step must not invent capability_id')
                if step.get('operation') not in OPERATIONS:
                    errors.append(f'{name}: invalid derive operation')
    for key, route in routes.items():
        if not isinstance(route, dict):
            errors.append(f'{key}: route must be an object')
            continue
        status = route.get('status')
        if status not in {'reviewed', 'not-applicable', 'unavailable'} or not route.get('reason'):
            errors.append(f'{key}: invalid route status/reason')
        ids = route.get('candidate_ids')
        if (not isinstance(ids, list) or any(item not in candidates for item in ids)
                or len(ids) != len(set(ids))):
            errors.append(f'{key}: invalid candidate_ids')
            continue
        if status == 'reviewed' and not ids:
            errors.append(f'{key}: reviewed route needs candidates')
        if set(ids) != reverse[key]:
            errors.append(f'{key}: candidate/source coverage mismatch')
    return errors


if __name__ == '__main__':
    path = Path(sys.argv[1]).resolve()
    try:
        data = json.loads(path.read_text())
        errors = check(data, path.parent)
    except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
        errors = [f'invalid discovery record: {exc}']
    print(json.dumps({'status': 'FAIL' if errors else 'PASS',
                      'discovery_version': data.get('discovery_version', 1) if isinstance(locals().get('data'), dict) else None,
                      'errors': errors}, ensure_ascii=False, indent=2))
    sys.exit(bool(errors))
