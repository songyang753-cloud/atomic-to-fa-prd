#!/usr/bin/env python3
"""Check a frozen query corpus and its traceability. Never executes business actions."""
import hashlib
import json
import sys
from pathlib import Path

METHODS = {'design', 'mock', 'evidence-replay', 'live-query', 'live-write', 'device', 'performance'}
STATUSES = {'not-run', 'pass', 'fail', 'blocked'}
KINDS = ('user-flow', 'business-flow')


def _check(manifest_path):
    mp = Path(manifest_path).resolve()
    errors = []

    def need(ok, message):
        if not ok:
            errors.append(message)
        return bool(ok)

    def read_ref(ref, label, json_file=True):
        if not isinstance(ref, dict) or not ref.get('path') or not ref.get('sha256'):
            need(False, label + ': path/sha256 required')
            return None
        p = mp.parent / ref['path']
        try:
            raw = p.read_bytes()
            need(hashlib.sha256(raw).hexdigest() == ref['sha256'], label + ': hash mismatch')
            return json.loads(raw) if json_file else raw.decode('utf-8')
        except (OSError, ValueError, UnicodeError) as exc:
            need(False, label + ': unreadable ' + str(exc))
            return None

    try:
        m = json.loads(mp.read_text())
    except (OSError, ValueError) as exc:
        return ['manifest: unreadable ' + str(exc)]
    if not isinstance(m, dict):
        return ['manifest: object required']
    need(m.get('schema_version') == 1, 'schema version')
    revision = m.get('revision')
    need(isinstance(revision, str) and bool(revision), 'revision required')
    oracle = m.get('oracle', {})
    need(isinstance(oracle, dict) and all(oracle.get(k) for k in ('owner', 'frozen_at', 'basis')),
         'oracle: owner/frozen_at/basis required')
    sources = m.get('sources', {})
    if not isinstance(sources, dict):
        return errors + ['sources: object required']
    data = {k: read_ref(sources.get(k), 'source ' + k, k not in ('body', 'appendix'))
            for k in ('handoff', 'interaction', 'flow_source', 'body', 'appendix')}
    h, r, flow = (data[k] for k in ('handoff', 'interaction', 'flow_source'))
    if not all(isinstance(x, dict) for x in (h, r, flow)):
        return errors
    for name, obj in (('handoff', h), ('interaction', r), ('flow_source', flow)):
        need(obj.get('revision') == revision, name + ': revision mismatch')
    need(r.get('input_sha256') == sources['handoff'].get('sha256'), 'interaction: input hash mismatch')
    if flow.get('input_sha256'):
        need(flow['input_sha256'] == sources['handoff'].get('sha256'), 'flow_source: input hash mismatch')
    features = {x['id']: x for x in h.get('features', [])}
    feature_ids = set(features)
    rule_ids = {x['id'] for x in h.get('critical_rules', [])}
    capability_ids = {x['id'] for x in h.get('capabilities', [])}
    node_ids = {x['id'] for x in r.get('nodes', [])}
    diagrams = {d.get('kind'): d for d in flow.get('diagrams', [])}
    for kind in KINDS:
        need(kind in diagrams, 'flow_source: missing ' + kind)
    raw_cases = read_ref(m.get('cases'), 'cases', False)
    if raw_cases is None:
        return errors
    cases = []
    for i, line in enumerate(raw_cases.splitlines(), 1):
        if line.strip():
            try:
                row = json.loads(line)
                if not isinstance(row, dict):
                    raise ValueError('object required')
                cases.append(row)
            except ValueError as exc:
                need(False, f'cases line {i}: {exc}')
    need(bool(cases), 'cases: empty corpus')
    seen, families = set(), {}
    covered_features, covered_rules = set(), set()
    covered_edges = {kind: set() for kind in KINDS}
    for c in cases:
        cid = c.get('id')
        label = str(cid or '<missing id>')
        need(isinstance(cid, str) and bool(cid) and cid not in seen, label + ': empty/duplicate ID')
        seen.add(cid)
        need(c.get('revision') == revision, label + ': revision mismatch')
        need(c.get('kind') in ('annotated', 'generalized'), label + ': kind')
        family, split = c.get('semantic_family'), c.get('split')
        need(isinstance(family, str) and bool(family), label + ': semantic_family')
        need(split in ('dev', 'test'), label + ': split')
        if family in families:
            need(families[family] == split, label + ': semantic family leaks across splits')
        families[family] = split
        for field, allowed, covered, nonempty in (
                ('feature_ids', feature_ids, covered_features, True),
                ('rule_ids', rule_ids, covered_rules, False),
                ('node_ids', node_ids, set(), True)):
            value = c.get(field)
            if need(isinstance(value, list) and (bool(value) or not nonempty), label + ': ' + field + ' list required'):
                need(all(isinstance(x, str) and x in allowed for x in value), label + ': unknown ' + field)
                covered.update(x for x in value if isinstance(x, str))
        need(isinstance(c.get('context'), dict) and bool(c['context']), label + ': context required')
        need(isinstance(c.get('query'), str) and bool(c['query'].strip()), label + ': query required')
        need(isinstance(c.get('events'), list) and bool(c['events']), label + ': events required')
        need(isinstance(c.get('forbidden_effects'), list) and bool(c['forbidden_effects']), label + ': forbidden_effects required')
        expected = c.get('expected', {})
        if not isinstance(expected, dict):
            need(False, label + ': expected object required')
            expected = {}
        need(isinstance(expected.get('outcome'), str) and bool(expected['outcome'].strip()), label + ': expected outcome required')
        scoped_capabilities = {cap for fid in c.get('feature_ids', []) if fid in features
                               for cap in features[fid].get('capabilities', [])}
        actions = expected.get('actions')
        if need(isinstance(actions, list), label + ': expected actions list required'):
            for a in actions:
                if not isinstance(a, dict):
                    need(False, label + ': action object required')
                    continue
                need(a.get('capability_id') in capability_ids, label + ': unknown action capability')
                need(a.get('capability_id') in scoped_capabilities, label + ': action outside case feature capabilities')
                low, high = a.get('min_calls'), a.get('max_calls')
                need(type(low) is int and type(high) is int and 0 <= low <= high, label + ': invalid call bounds')
                need(isinstance(a.get('target'), str) and bool(a['target']), label + ': action target required')
        mapped = c.get('flow_nodes', {})
        exemptions = c.get('flow_exemptions', {})
        if not isinstance(mapped, dict) or not isinstance(exemptions, dict):
            need(False, label + ': flow mapping object required')
            mapped, exemptions = {}, {}
        for kind in KINDS:
            diagram = diagrams.get(kind, {})
            dn = {x['id']: x for x in diagram.get('nodes', [])}
            refs = mapped.get(kind, [])
            if not refs:
                need(isinstance(exemptions.get(kind), str) and bool(exemptions[kind].strip()), label + ': missing ' + kind + ' mapping/reason')
            elif need(isinstance(refs, list) and all(isinstance(x, str) and x in dn for x in refs), label + ': invalid ' + kind + ' nodes'):
                projected = {n for x in refs for n in dn[x].get('interaction_nodes', [])}
                need(bool(projected.intersection(c.get('node_ids', []))), label + ': ' + kind + ' has no interaction overlap')
            actual_edges = {(e.get('source'), e.get('target'), e.get('label', '')) for e in diagram.get('edges', [])}
            flow_edges = c.get('flow_edges', {})
            if not isinstance(flow_edges, dict):
                need(False, label + ': flow_edges object required')
                continue
            for edge in flow_edges.get(kind, []):
                key = (edge.get('source'), edge.get('target'), edge.get('label', ''))
                need(key in actual_edges, label + ': unknown ' + kind + ' edge')
                need(key[0] in refs and key[1] in refs, label + ': ' + kind + ' edge endpoints outside case flow_nodes')
                covered_edges[kind].add(key)
        verification = c.get('verification', {})
        if not isinstance(verification, dict):
            need(False, label + ': verification object required')
            verification = {}
        method, status = verification.get('method'), verification.get('status')
        need(method in METHODS, label + ': verification method')
        need(status in STATUSES, label + ': execution status')
        if method == 'design':
            need(status == 'not-run', label + ': design is not executed PASS/FAIL')
        evidence = verification.get('evidence', [])
        need(isinstance(evidence, list), label + ': evidence list required')
        if status in ('pass', 'fail'):
            need(method != 'design' and bool(evidence), label + ': executed result needs evidence')
        if isinstance(evidence, list):
            for j, ref in enumerate(evidence):
                read_ref(ref, f'{label} evidence {j}', False)
        if method == 'live-write' and status in ('pass', 'fail'):
            need(isinstance(verification.get('authorization'), dict) and all(verification['authorization'].get(k) for k in ('source', 'scope')),
                 label + ': live-write needs explicit authorization source/scope')
    exceptions = m.get('coverage_exceptions', [])
    excluded = {'feature_ids': set(), 'rule_ids': set()}
    for x in exceptions:
        kind, xid = x.get('kind'), x.get('id')
        allowed = feature_ids if kind == 'feature_ids' else rule_ids if kind == 'rule_ids' else set()
        need(kind in excluded and xid in allowed and x.get('reason') and x.get('owner'), 'invalid coverage exception')
        if kind in excluded:
            excluded[kind].add(xid)
    need(feature_ids <= covered_features | excluded['feature_ids'], 'uncovered features: ' + ','.join(sorted(feature_ids - covered_features - excluded['feature_ids'])))
    need(rule_ids <= covered_rules | excluded['rule_ids'], 'uncovered critical rules: ' + ','.join(sorted(rule_ids - covered_rules - excluded['rule_ids'])))
    required = m.get('coverage', {}).get('required_flow_edges', {})
    for kind in KINDS:
        for e in required.get(kind, []):
            need((e.get('source'), e.get('target'), e.get('label', '')) in covered_edges[kind], 'uncovered required ' + kind + ' edge')
    return errors


def check(manifest_path):
    try:
        return _check(manifest_path)
    except (TypeError, KeyError, AttributeError, ValueError) as exc:
        return ['invalid corpus structure: ' + str(exc)]


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: check_cases.py <corpus.json>')
    failures = check(sys.argv[1])
    print(json.dumps({'passed': not failures, 'errors': failures,
                      'scope': 'structure, source hashes and declared trace coverage; not semantic/business/device/performance acceptance'}, ensure_ascii=False, indent=2))
    raise SystemExit(bool(failures))
