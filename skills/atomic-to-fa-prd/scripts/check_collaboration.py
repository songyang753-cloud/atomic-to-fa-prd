#!/usr/bin/env python3
"""Check collaboration receipts, file hashes and closure; not semantic correctness."""
import hashlib
import json
import sys
from pathlib import Path

CORE = {'product', 'technical', 'algorithm', 'interaction'}
OPTIONAL = {'ceo', 'cfo', 'coo', 'operations'}
STAGES = {'capability', 'research', 'product', 'interaction', 'review', 'owner'}

def check(path, archive=False):
    path = Path(path)
    data = json.loads(path.read_text())
    errors = []
    def need(ok, msg):
        if not ok: errors.append(msg)
    def index(rows, label):
        need(isinstance(rows, list), label + ': must be list')
        if not isinstance(rows, list): return {}
        ids = [r.get('id') for r in rows]
        need(all(ids) and len(ids) == len(set(ids)), label + ': missing/duplicate id')
        return {r.get('id'): r for r in rows}
    revision = data.get('revision')
    version = data.get('schema_version')
    need(version in {1, 2, 3, 4} and bool(revision), 'schema/revision missing')
    need(version == 4 or archive, 'current project requires schema 4; use --archive only for historical review')
    state = data.get('state')
    need(state in {'draft', 'blocked', 'reviewed', 'delivered'}, 'invalid state')
    ready = state in {'reviewed', 'delivered'}
    need(type(data.get('repair_rounds')) is int and 0 <= data['repair_rounds'] <= 2, 'repair rounds must be 0..2')
    artifacts = index(data.get('artifacts', []), 'artifacts')
    for aid, a in artifacts.items():
        p = path.parent / a.get('path', '')
        need(a.get('revision') == revision, f'{aid}: stale revision')
        need(p.is_file(), f'{aid}: missing file')
        if p.is_file(): need(a.get('sha256') == hashlib.sha256(p.read_bytes()).hexdigest(), f'{aid}: hash mismatch')
        if a.get('kind') in {'body', 'appendix'}: need(a.get('owner') == 'owner', f'{aid}: formal writer must be owner')
    def refs(rows, label):
        need(bool(rows), label + ': no inputs')
        for r in rows:
            a = artifacts.get(r.get('artifact_id'))
            need(a is not None, label + ': unknown artifact')
            if a: need(r.get('sha256') == a.get('sha256'), label + ': stale input hash')
    standards = index(data.get('standards', []), 'standards')
    for sid, s in standards.items():
        need(bool(s.get('producer')) and bool(s.get('consumer')) and bool(s.get('criteria')), f'{sid}: incomplete standard')
    receipts = index(data.get('receipts', []), 'receipts')
    for rid, r in receipts.items():
        s = standards.get(r.get('standard_id'))
        need(s is not None, f'{rid}: unknown standard')
        if s:
            need(r.get('producer') == s.get('producer') and r.get('consumer') == s.get('consumer'), f'{rid}: parties mismatch')
            need(s.get('sequence', 0) < r.get('sequence', 0), f'{rid}: standard must precede delivery')
            need(set(s.get('criteria', [])) == set(r.get('checks', {})), f'{rid}: acceptance checks incomplete')
        need(r.get('revision') == revision and bool(r.get('agent_id')), f'{rid}: stale revision/agent missing')
        refs(r.get('inputs', []), str(rid))
        need(bool(r.get('outputs')) and set(r.get('outputs', [])) <= artifacts.keys(), f'{rid}: invalid outputs')
        need(r.get('status') in {'accepted', 'accepted-with-limits', 'returned'}, f'{rid}: invalid acceptance')
        if r.get('status') != 'returned': need(all(v == 'pass' for v in r.get('checks', {}).values()), f'{rid}: acceptance failed')
        if r.get('status') == 'accepted-with-limits': need(bool(r.get('limitations')), f'{rid}: missing limitations')
        if version >= 2 and r.get('status') in {'accepted', 'accepted-with-limits'}:
            acceptance = artifacts.get(r.get('acceptance_artifact_id'), {})
            ap = path.parent / acceptance.get('path', '')
            need(bool(acceptance) and ap.is_file(), f'{rid}: consumer acceptance file missing')
            if acceptance and ap.is_file():
                a = json.loads(ap.read_text())
                need(bool(a.get('consumer_agent_id')) and a.get('consumer_agent_id') != r.get('agent_id'), f'{rid}: actual independent consumer missing')
                need(a.get('consumer') == r.get('consumer') and a.get('receipt_id') == rid, f'{rid}: acceptance parties/receipt mismatch')
                need(a.get('revision') == revision and a.get('sequence', 0) > r.get('sequence', 0), f'{rid}: stale or premature consumer acceptance')
                expected = {x: artifacts[x].get('sha256') for x in r.get('outputs', []) if x in artifacts}
                consumed = {x.get('artifact_id'): x.get('sha256') for x in a.get('inputs', [])}
                need(all(consumed.get(k) == v for k,v in expected.items()), f'{rid}: consumer did not bind delivered outputs')
                refs(a.get('inputs', []), str(rid) + ' consumer')
                need(a.get('checks') == r.get('checks') and a.get('status') == r.get('status'), f'{rid}: consumer verdict mismatch')
                need(bool(a.get('observations')), f'{rid}: consumer observations missing')

    if ready:
        accepted = [r for r in receipts.values() if r.get('status') in {'accepted', 'accepted-with-limits'}]
        stages = STAGES | ({'test'} if version >= 3 else set())
        need(stages <= {r.get('producer') for r in accepted}, 'required stage receipts missing')
        stage_agents = {stage: {r.get('agent_id') for r in accepted if r.get('producer') == stage} for stage in stages}
        need(all(stage_agents.values()) and all(not stage_agents[a] & stage_agents[b] for a in stages for b in stages if a != b), 'stages require independent agents')
        need({'body', 'appendix'} <= {a.get('kind') for a in artifacts.values()}, 'body/appendix missing')
    findings = index(data.get('findings', []), 'findings')
    for fid, f in findings.items():
        need(f.get('severity') in {'blocker', 'major', 'minor'}, f'{fid}: invalid severity')
        need(f.get('status') in {'open', 'resolved', 'deferred'}, f'{fid}: invalid closure')
        need(bool(f.get('owner')), f'{fid}: missing owner')
        if f.get('status') != 'open': need(bool(f.get('evidence')) and bool(f.get('decision')), f'{fid}: closure evidence missing')
        if f.get('status') == 'deferred': need(f.get('category') == 'validation-gap' and bool(f.get('limitation')), f'{fid}: only explicit validation gaps may defer')
        if ready: need(not (f.get('severity') in {'blocker', 'major'} and f.get('status') == 'open'), f'{fid}: unresolved blocker/major')
        if f.get('category') in {'capability-boundary', 'fact-error'}: need(f.get('status') == 'resolved' or not ready, f'{fid}: immutable constraint unresolved')
    reviews = index(data.get('reviews', []), 'reviews')
    roles = {r.get('role') for r in reviews.values()}
    for rid, r in reviews.items():
        need(r.get('revision') == revision and bool(r.get('agent_id')), f'{rid}: reviewer/revision missing')
        refs(r.get('inputs', []), str(rid))
        need(set(r.get('finding_ids', [])) <= findings.keys(), f'{rid}: unknown finding')
    if ready:
        need(CORE <= roles, 'core reviews missing')
        core_agents = {role: {r.get('agent_id') for r in reviews.values() if r.get('role') == role} for role in CORE}
        need(all(not core_agents[a] & core_agents[b] for a in CORE for b in CORE if a != b), 'core reviews require different agents')
        decisions = data.get('optional_reviews', {})
        need(OPTIONAL == set(decisions), 'optional review applicability missing')
        for role, d in decisions.items():
            need(isinstance(d.get('applicable'), bool) and bool(d.get('reason')), role + ': applicability reason missing')
            if d.get('applicable'): need(role in roles, role + ': applicable review missing')
    for c in data.get('changes', []):
        need(c.get('decided_by') == 'owner' and bool(c.get('reason')), 'change must be owner decision')
        rr = [receipts.get(x, {}) for x in c.get('reacceptance_receipt_ids', [])]
        need(set(c.get('affected_roles', [])) <= {r.get('consumer') for r in rr if r.get('status') in {'accepted', 'accepted-with-limits'}}, 'change lacks impacted role reacceptance')
        if version >= 2:
            need(bool(c.get('id')) and bool(c.get('affected_artifact_ids')) and set(c.get('affected_artifact_ids', [])) <= artifacts.keys(), 'change delta missing/unknown artifacts')
            for r in rr:
                a = artifacts.get(r.get('acceptance_artifact_id'), {})
                ap = path.parent / a.get('path', '')
                accepted_delta = json.loads(ap.read_text()) if a and ap.is_file() else {}
                need(c.get('id') in accepted_delta.get('change_ids', []), 'reacceptance not bound to current change')

    final = data.get('final_review', {})
    if ready:
        need(final.get('revision') == revision and final.get('status') == 'pass' and bool(final.get('agent_id')), 'final review missing/stale')
        need(final.get('agent_id') not in {r.get('agent_id') for r in receipts.values() if r.get('producer') == 'owner'}, 'final reviewer must be independent of formal writer')
        refs(final.get('inputs', []), 'final review')
        need(set(artifacts) <= {r.get('artifact_id') for r in final.get('inputs', [])}, 'final review must cover all final artifacts')
        need({'capability-boundaries', 'body-appendix', 'flow-text', 'rules-cases', 'metrics', 'correctness'} <= {k for k,v in final.get('checks', {}).items() if v == 'pass'}, 'final consistency checks incomplete')
    delivery = data.get('delivery', {})
    if state == 'delivered':
        need(delivery.get('state') == 'verified' and str(delivery.get('url', '')).startswith('https://'), 'delivery not verified')
        refs(delivery.get('readback_inputs', []), 'delivery readback')
        need({aid for aid,a in artifacts.items() if a.get('kind') in {'body', 'appendix'}} <= {r.get('artifact_id') for r in delivery.get('readback_inputs', [])}, 'body/appendix readback missing')
        need(bool(delivery.get('readback_evidence')), 'readback evidence missing')
        diagrams = delivery.get('diagrams', [])
        need({d.get('kind') for d in diagrams} == {'user-flow', 'business-flow'} and len(diagrams) == 2, 'two required diagrams missing')
        for d in diagrams:
            need(d.get('native_editable') is True and bool(d.get('node_evidence')) and bool(d.get('preview_evidence')), 'diagram verification evidence missing')
    if version == 4 and ready:
        from check_capability import check as check_capability
        errors.extend(check_capability(data, path.parent))
    return errors

if __name__ == '__main__':
    try: errors = check(sys.argv[1], archive="--archive" in sys.argv[2:])
    except (IndexError, ValueError, TypeError, KeyError, OSError, AttributeError) as exc: errors = ['invalid input: ' + str(exc)]
    print(json.dumps({'passed': not errors, 'scope': 'structure, references, bytes and recorded acceptance only', 'errors': errors}, ensure_ascii=False, indent=2))
    sys.exit(bool(errors))
