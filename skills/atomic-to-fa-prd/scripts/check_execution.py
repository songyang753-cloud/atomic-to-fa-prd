#!/usr/bin/env python3
"""Check execution receipts, not evidence authenticity or business semantics."""
import collections
import hashlib
import json
import pathlib
import sys
import check_cases


def check(execution_path, acceptance_path=None):
    errors = []
    def need(condition, message):
        if not condition:
            errors.append(message)
    def read(ref, base, structured=True):
        p = pathlib.Path(ref['path'])
        if not p.is_absolute():
            p = base / p
        raw = p.read_bytes()
        need(hashlib.sha256(raw).hexdigest() == ref['sha256'], f'stale hash: {p}')
        return (json.loads(raw) if structured else raw), p
    p = pathlib.Path(execution_path).resolve()
    e = json.loads(p.read_text())
    corpus, cp = read(e['corpus'], p.parent)
    errors.extend(check_cases.check(str(cp)))
    case_path = pathlib.Path(corpus['cases']['path'])
    if not case_path.is_absolute():
        case_path = cp.parent / case_path
    cases = {c['id']: c for c in map(json.loads, case_path.read_text().splitlines())}
    need(e['revision'] == corpus['revision'], 'execution revision mismatch')
    target = e['target']
    need(target['kind'] in ('implementation', 'reference-agent', 'mock'), 'invalid target kind')
    need(all(target.get(k) for k in ('version', 'entrypoint')), 'missing target identity')
    need(bool(e['consumer']['agent_id']), 'missing consumer')
    intake, ip = read(e['consumer']['intake'], p.parent)
    need(intake.get('revision') == e['revision'] and intake.get('consumer_agent_id') == e['consumer']['agent_id'], 'intake identity mismatch')
    need(intake.get('corpus') == e['corpus'] and intake.get('sources') == corpus['sources'], 'intake inputs mismatch')
    for ref in intake.get('sources', {}).values():
        read(ref, cp.parent, False)
    modes = intake.get('capability_modes', {})
    runs = e['runs']
    need(collections.Counter(r['case_id'] for r in runs) == collections.Counter(cases.keys()), 'runs must cover corpus exactly once')
    run_map = {}
    for r in runs:
        cid = r['case_id']
        if cid not in cases:
            continue
        run_map[cid] = r
        method, status = r['method'], r['status']
        need(method in ('design', 'mock', 'evidence-replay', 'live-query', 'live-write', 'device', 'performance'), cid + ': invalid method')
        need(status in ('pass', 'fail', 'blocked', 'not-run'), cid + ': invalid status')
        if status in ('blocked', 'not-run'):
            need(bool(r.get('reason')), cid + ': missing blocker/next step')
        if status not in ('pass', 'fail'):
            continue
        need(method != 'design', cid + ': design cannot execute')
        need(target['version'] != 'not-provided' and target['entrypoint'] != 'not-provided', cid + ': no target')
        refs = r.get('evidence', [])
        need(bool(refs), cid + ': missing execution evidence')
        actual = collections.Counter()
        failed = False
        kinds = set()
        for ref in refs:
            ev, _ = read(ref, p.parent)
            need(ev.get('target_version') == target['version'] and ev.get('case_id') == cid and ev.get('method') == method, cid + ': evidence identity mismatch')
            obs = ev['observed']
            need(bool(obs.get('outcome')), cid + ': no observed outcome')
            for action in obs['actions']:
                actual[action['capability_id']] += 1
                need(bool(action.get('target')), cid + ': action object missing')
            failed |= bool(obs['forbidden_effects'])
            for a in ev['assertions']:
                need(a['kind'] in ('outcome', 'forbidden') and a['status'] in ('pass', 'fail') and bool(a.get('basis')), cid + ': invalid assertion')
                kinds.add(a['kind'])
                failed |= a['status'] == 'fail'
        need({'outcome', 'forbidden'} <= kinds, cid + ': outcome/forbidden assertions required')
        expected = {a['capability_id']: a for a in cases[cid]['expected']['actions']}
        failed |= bool(set(actual) - set(expected))
        for cap, a in expected.items():
            failed |= not a['min_calls'] <= actual[cap] <= a['max_calls']
        need((status == 'fail') == failed, cid + ': verdict disagrees with assertions/actions')
        if method == 'live-query':
            need(target['kind'] == 'implementation' and all(modes.get(cap) == 'read-only' for cap in actual), cid + ': live-query actions not verified read-only')
        if method == 'mock':
            need(bool(r.get('isolation')), cid + ': mock isolation missing')
        if method in ('live-query', 'live-write', 'device', 'performance'):
            need(all(modes.get(cap) in ('read-only', 'write') for cap in actual), cid + ': unknown action risk blocks live execution')
        if method == 'live-write' or (method in ('device', 'performance') and any(modes.get(cap) == 'write' for cap in actual)):
            need(target['kind'] == 'implementation', cid + ': live-write needs implementation')
            if r.get('authorization'):
                read(r['authorization'], p.parent)
            else:
                errors.append(cid + ': missing explicit write authorization')
    if acceptance_path:
        ap = pathlib.Path(acceptance_path).resolve()
        a = json.loads(ap.read_text())
        _, acp = read(a['corpus'], ap.parent)
        need(acp == cp and a['revision'] == e['revision'], 'acceptance source mismatch')
        handoff, _ = read(corpus['sources']['handoff'], cp.parent)
        rules = {x['id'] for x in handoff['critical_rules']}
        need(collections.Counter(x['rule_id'] for x in a['rules']) == collections.Counter(rules), 'acceptance must cover critical rules exactly once')
        for rule in a['rules']:
            rid = rule['rule_id']
            need(all(rule.get(k) for k in ('owner', 'inputs', 'guard', 'on_reject', 'assertion')), rid + ': incomplete dev contract')
            pos, neg = rule.get('positive_case_ids', []), rule.get('negative_case_ids', [])
            need(bool(pos) or bool(rule.get('positive_exception')), rid + ': missing positive branch')
            need(bool(neg) and not set(pos) & set(neg), rid + ': missing/distinct negative branch')
            for cid in pos + neg:
                need(cid in cases and rid in cases[cid]['rule_ids'], rid + ': invalid case reference ' + cid)
            need(rule['status'] in ('pass', 'fail', 'blocked'), rid + ': invalid acceptance status')
            if rule['status'] != 'pass':
                need(bool(rule.get('reason')), rid + ': missing reason')
                continue
            imp = rule['implementation']
            need(imp['status'] == 'implemented' and imp.get('entrypoint') == target['entrypoint'] and imp.get('version') == target['version'] and target['kind'] == 'implementation', rid + ': missing actual implementation')
            need(bool(rule.get('evidence')), rid + ': missing implementation evidence')
            for ref in rule.get('evidence', []):
                read(ref, ap.parent)
            for cid in pos + neg:
                run = run_map.get(cid, {})
                need(run.get('status') == 'pass' and run.get('method') in ('mock', 'live-query', 'live-write', 'device', 'performance'), rid + ': branch not executed against implementation ' + cid)
    return errors


if __name__ == '__main__':
    try:
        if len(sys.argv) not in (2, 3):
            raise ValueError('usage: check_execution.py execution.json [acceptance.json]')
        errors = check(*sys.argv[1:])
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        errors = ['invalid receipt: ' + str(exc)]
    print(json.dumps({'passed': not errors, 'errors': errors, 'scope': 'receipt integrity and declared assertions; independent semantic review required'}, ensure_ascii=False, indent=2))
    sys.exit(bool(errors))
