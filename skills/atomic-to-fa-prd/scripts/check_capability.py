#!/usr/bin/env python3
"""Validate capability evidence and four independent handoffs; not business truth."""
import json
from pathlib import Path


def check(data, base):
    errors = []
    def need(ok, message):
        if not ok: errors.append('capability: ' + message)
    artifacts = {a['id']: a for a in data.get('artifacts', [])}
    aid = data.get('capability_validation')
    need(aid in artifacts, 'validation artifact missing')
    if aid not in artifacts: return errors
    report = json.loads((Path(base) / artifacts[aid]['path']).read_text())
    need(report.get('revision') == data.get('revision'), 'stale report')
    def rows(key):
        value = report.get(key, [])
        need(isinstance(value, list), key + ' must be list')
        return value if isinstance(value, list) else []
    def refs(ids, label):
        need(bool(ids) and set(ids) <= artifacts.keys(), label + ' evidence missing/unknown')
    docs = rows('documents')
    need(bool(docs), 'document inventory missing')
    docids = {d.get('id') for d in docs}
    need(None not in docids and len(docids) == len(docs), 'document ids missing/duplicate')
    for d in docs:
        need(all(d.get(k) for k in ('source','version','status')), 'document metadata incomplete')
        need(d.get('status') in {'read','unavailable'}, 'document status invalid')
        refs([d.get('evidence_artifact_id')], 'document')
        if d.get('status') == 'unavailable': need(bool(d.get('impact')), 'unavailable document needs impact')
    caps = rows('inventory')
    capmap = {c.get('id'): c for c in caps}
    need(bool(caps) and None not in capmap and len(capmap) == len(caps), 'capability ids missing/duplicate')
    for c in caps:
        refs([c.get('source_artifact_id')], 'inventory')
        need(isinstance(c.get('required_inputs'), list), 'required inputs missing')
        need(c.get('verification') in {'current-query','historical','definition-only','pending','failed'}, 'verification invalid')
        need('limitations' in c, 'limitations missing')
    def load_artifact(key):
        ref = report.get(key)
        need(ref in artifacts, key + ' missing/unknown')
        if ref not in artifacts: return {}
        return json.loads((Path(base) / artifacts[ref]['path']).read_text())
    snapshot = load_artifact('inventory_source_artifact_id')
    expected_ids = snapshot.get('capability_ids', [])
    need(bool(expected_ids) and len(expected_ids) == len(set(expected_ids)), 'source inventory missing/duplicate')
    need(set(expected_ids) == set(capmap), 'source inventory coverage mismatch')
    refs(snapshot.get('raw_evidence_artifact_ids', []), 'raw source inventory')
    discovery = load_artifact('discovery_artifact_id')
    need(discovery.get('revision') == data.get('revision'), 'stale discovery')
    included = {c.get('id'): c for c in discovery.get('candidates', []) if c.get('decision') == 'include'}
    need(bool(included), 'included discovery candidates missing')
    need({c.get('id') for c in discovery.get('capabilities', [])} <= set(capmap), 'discovery unknown capabilities')
    examples = rows('examples')
    need(bool(examples) or bool(report.get('examples_absence_reason')), 'examples or absence reason missing')
    need(all(ex.get('id') for ex in examples) and len({ex.get('id') for ex in examples}) == len(examples), 'example ids missing/duplicate')
    for ex in examples:
        need(ex.get('document_id') in docids and bool(ex.get('task')), 'example source/task missing')
        need(bool(ex.get('capability_ids')) and set(ex['capability_ids']) <= capmap.keys(), 'example unknown capabilities')
        need(ex.get('decision') in {'adopt','merge','reject'} and bool(ex.get('reason')), 'example decision missing')
    paths = rows('paths')
    need(bool(paths), 'business paths missing')
    for p in paths:
        c = capmap.get(p.get('capability_id'))
        need(c is not None, 'path unknown capability')
        need(all(p.get(k) for k in ('feature_id','action','result_use')), 'path action/result incomplete')
        bindings = p.get('bindings', {})
        need(isinstance(bindings, dict), 'bindings must be object')
        if c and isinstance(bindings, dict):
            need(set(c.get('required_inputs', [])) <= {k for k,v in bindings.items() if v}, 'required input unbound')
        refs(p.get('evidence_artifact_ids', []), 'path')
    need({p.get('feature_id') for p in paths} <= set(included), 'unknown/excluded feature path')
    need(set(included) <= {p.get('feature_id') for p in paths}, 'included feature lacks path')
    for fid, candidate in included.items():
        mapped = {p.get('capability_id') for p in paths if p.get('feature_id') == fid}
        need(set(candidate.get('capabilities', [])) <= mapped, 'feature capability lacks action path: ' + str(fid))
    gates = rows('gates')
    producers = {'requirements':'product','interaction':'interaction','cases':'test','final':'owner'}
    need(len(gates) == 4 and {g.get('name') for g in gates} == set(producers), 'four gates missing/duplicate')
    receipts = {r['id']: r for r in data.get('receipts', [])}
    standards = {s['id']: s for s in data.get('standards', [])}
    sequences = {}
    for g in gates:
        r = receipts.get(g.get('receipt_id'), {})
        name = g.get('name')
        need(r.get('consumer') == 'capability' and r.get('producer') == producers.get(name), 'gate parties mismatch')
        need(r.get('status') in {'accepted','accepted-with-limits'}, 'gate not accepted')
        criteria = standards.get(r.get('standard_id'), {}).get('criteria', [])
        need({'capability-coverage','inputs-results','evidence-boundaries'} <= set(criteria), 'gate criteria incomplete')
        consumed = {i.get('artifact_id') for i in r.get('inputs', [])}
        need(aid in consumed and report.get('inventory_source_artifact_id') in consumed and report.get('discovery_artifact_id') in consumed,
             'gate did not consume inventory and discovery')
        targets = g.get('target_artifact_ids', [])
        need(bool(targets) and set(targets) <= artifacts.keys() and set(targets) <= set(r.get('outputs', [])),
             'gate stage delivery missing/unbound')
        acceptance_artifact = artifacts.get(r.get('acceptance_artifact_id'), {})
        acceptance_path = Path(base) / acceptance_artifact.get('path', '')
        acceptance = json.loads(acceptance_path.read_text()) if acceptance_path.is_file() else {}
        accepted_inputs = {item.get('artifact_id'): item.get('sha256') for item in acceptance.get('inputs', [])}
        required_sources = [aid, report.get('inventory_source_artifact_id'), report.get('discovery_artifact_id')]
        need(all(source in artifacts and accepted_inputs.get(source) == artifacts[source].get('sha256') for source in required_sources),
             'capability consumer did not bind current report and sources')
        capability_agents = {item.get('agent_id') for item in receipts.values() if item.get('producer') == 'capability' and item.get('status') in {'accepted','accepted-with-limits'}}
        need(bool(acceptance.get('consumer_agent_id')) and acceptance.get('consumer_agent_id') in capability_agents, 'gate consumer is not capability expert')
        sequences[name] = (r.get('sequence', -1), acceptance.get('sequence', -1))
    order = [value for n in producers for value in sequences.get(n, (-1, -1))]
    need(all(x >= 0 for x in order) and order == sorted(set(order)), 'gate order invalid')
    return errors
