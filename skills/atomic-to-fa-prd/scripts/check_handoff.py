#!/usr/bin/env python3
"""Validate a versioned design handoff. Does not execute tools or certify semantics."""
import hashlib
import json
import sys
from pathlib import Path

METRICS = dict(precision_min=.95, recall_min=.95, first_audio_p50_max_ms=1000,
               first_audio_p95_lt_ms=1500, task_completion_min=.90)

def check(input_path, output_path):
    ip, op = Path(input_path), Path(output_path)
    h, r = json.loads(ip.read_text()), json.loads(op.read_text())
    errors = []
    def need(ok, message):
        if not ok:
            errors.append(message)
    def indexed(rows, label):
        ids = [x.get('id') for x in rows]
        need(all(ids) and len(ids) == len(set(ids)), label + ': empty/duplicate IDs')
        return {x.get('id'): x for x in rows}
    def fields(row, names, label):
        for name in names:
            need(bool(row.get(name)), label + ': missing ' + name)
    need(h.get('schema_version') == r.get('schema_version') == 1, 'schema version')
    need(bool(h.get('revision')) and h.get('revision') == r.get('revision'), 'revision mismatch')
    need(r.get('input_sha256') == hashlib.sha256(ip.read_bytes()).hexdigest(), 'input hash mismatch')
    need(bool(h.get('approval')), 'approval missing')
    need(h.get('mode') in ('capability-bounded', 'target-experience'), 'scope mode')
    if h.get('mode') == 'target-experience':
        need(bool(h.get('target_experience_authorization')), 'target experience authorization missing')
    caps = indexed(h.get('capabilities', []), 'capabilities')
    features = indexed(h.get('features', []), 'input features')
    returned = indexed(r.get('features', []), 'returned features')
    rules = indexed(h.get('critical_rules', []), 'rules')
    nodes = indexed(r.get('nodes', []), 'nodes')
    cases = indexed(r.get('cases', []), 'cases')
    need(bool(features), 'no features')
    need(set(features) == set(returned), 'scope drift')
    need(bool(h.get('platform')), 'platform missing')
    for fid, f in features.items():
        fields(f, ['goal','end_condition','capabilities','limits'], str(fid))
        need(f.get('priority') in ('P0','P1','P2'), str(fid) + ': priority')
        need(f.get('priority') == returned.get(fid, {}).get('priority'), str(fid) + ': priority drift')
        need(set(f.get('capabilities', [])) <= caps.keys(), str(fid) + ': unknown capability')
        need(any(fid in n.get('feature_ids', []) for n in nodes.values()), str(fid) + ': no node')
    for nid, n in nodes.items():
        fields(n, ['feature_ids','role','trigger','utterance'], str(nid))
        need(set(n.get('feature_ids', [])) <= features.keys(), str(nid) + ': unknown feature')
        need(set(n.get('next', [])) <= nodes.keys(), str(nid) + ': dangling transition')
        need(bool(n.get('next')) or n.get('terminal') is True, str(nid) + ': unclosed path')
        allowed = {c for f in n.get('feature_ids', []) for c in features.get(f, {}).get('capabilities', [])}
        need(set(n.get('actions', [])) <= allowed, str(nid) + ': unsupported action')
    coverage = r.get('rule_coverage', [])
    need(len(coverage) == len({c.get('rule_id') for c in coverage}), 'duplicate rule coverage')
    cov = {c.get('rule_id'): c for c in coverage}
    need(set(cov) == set(rules), 'critical rule coverage mismatch')
    for rid, rule in rules.items():
        fields(rule, ['feature_ids','statement','owner','condition','allowed_action','forbidden_effect','fallback'], str(rid))
        need(set(rule.get('feature_ids', [])) <= features.keys(), str(rid) + ': unknown feature')
        c = cov.get(rid, {})
        fields(c, ['guard','node_ids','case_ids','status'], str(rid))
        need(c.get('owner') == rule.get('owner'), str(rid) + ': owner drift')
        need(set(c.get('node_ids', [])) <= nodes.keys(), str(rid) + ': unknown node')
        need(set(c.get('case_ids', [])) <= cases.keys(), str(rid) + ': unknown case')
        for cid in c.get('case_ids', []):
            need(rid in cases.get(cid, {}).get('rule_ids', []), str(rid) + ': asymmetric case ' + str(cid))
        for nid in c.get('node_ids', []):
            need(bool(set(nodes.get(nid, {}).get('feature_ids', [])) & set(rule.get('feature_ids', []))), str(rid) + ': unrelated node')
    for cid, case in cases.items():
        fields(case, ['rule_ids','given','events','expected','forbidden_effects','verification','evidence'], str(cid))
        need(set(case.get('rule_ids', [])) <= rules.keys(), str(cid) + ': unknown rule')
        need(case.get('verification') in ('design','mock','live-query','live-write','device','performance','not-run'), str(cid) + ': verification level')
        for rid in case.get('rule_ids', []):
            need(cid in cov.get(rid, {}).get('case_ids', []), str(cid) + ': asymmetric rule ' + str(rid))
    for source, data in [('input', h), ('output', r)]:
        need(data.get('metrics') == METRICS, source + ': metric drift')
    artifacts = r.get('artifacts', [])
    need({'body','appendix','flow-source'} <= {a.get('kind') for a in artifacts}, 'required artifacts missing')
    for a in artifacts:
        p = op.parent / a.get('path', '')
        need(a.get('revision') == h.get('revision'), 'artifact revision mismatch: ' + str(p))
        need(p.is_file(), 'artifact missing: ' + str(p))
        if p.is_file():
            need(a.get('sha256') == hashlib.sha256(p.read_bytes()).hexdigest(), 'artifact hash mismatch: ' + str(p))
    return errors

if __name__ == '__main__':
    try:
        result = check(*sys.argv[1:])
    except (ValueError, TypeError, KeyError, OSError) as exc:
        result = ['invalid input: ' + str(exc)]
    print(json.dumps({'passed': not result, 'errors': result}, ensure_ascii=False, indent=2))
    sys.exit(bool(result))
