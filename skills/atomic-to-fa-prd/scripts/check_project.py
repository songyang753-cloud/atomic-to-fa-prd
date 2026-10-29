#!/usr/bin/env python3
"""Run every project gate; integrity, runtime and publication remain separate."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

SCRIPTS = Path(__file__).resolve().parent
REQUIRED = {'collaboration', 'discovery', 'continuity', 'product', 'interaction',
            'corpus', 'execution', 'acceptance', 'defects', 'semantic_review'}


def check(path):
    path = Path(path).resolve()
    data = json.loads(path.read_text())
    errors, reports, loaded, paths = [], {}, {}, {}
    def need(ok, message):
        if not ok:
            errors.append(message)
    need(data.get('project_version') == 1, 'project_version must be 1')
    need(bool(data.get('revision')), 'missing project revision')
    refs = data.get('inputs', {})
    need(set(refs) == REQUIRED, 'missing or unknown project inputs')
    for key in REQUIRED:
        ref = refs.get(key, {})
        p = path.parent / ref.get('path', '')
        need(p.is_file(), key + ': missing input file')
        if not p.is_file():
            continue
        need(hashlib.sha256(p.read_bytes()).hexdigest() == ref.get('sha256'), key + ': stale input hash')
        need(ref.get('revision') == data.get('revision'), key + ': stale input revision')
        paths[key] = p
        loaded[key] = json.loads(p.read_text())
    if errors:
        return {'passed': False, 'errors': errors, 'gates': reports,
                'runtime': 'not-evaluated', 'delivery': 'not-evaluated'}
    need(loaded['collaboration'].get('state') in {'reviewed', 'delivered'}, 'collaboration not ready for final gate')
    need(loaded['continuity'].get('state') == 'reviewed', 'continuity not independently reviewed')
    need(loaded['collaboration'].get('schema_version') == 4, 'current collaboration requires schema 4')
    need(loaded['discovery'].get('discovery_version') == 2, 'current discovery requires version 2')
    need(loaded['continuity'].get('continuity_version') == 2, 'current continuity requires version 2')
    for key in REQUIRED - {'semantic_review'}:
        need(loaded[key].get('revision') == data['revision'], key + ': internal revision mismatch')
    def same_ref(ref, base, key):
        return (base / ref.get('path', '')).resolve() == paths[key].resolve() and ref.get('sha256') == refs[key]['sha256']
    need(same_ref(loaded['execution'].get('corpus', {}), paths['execution'].parent, 'corpus'), 'execution consumes another corpus')
    need(same_ref(loaded['acceptance'].get('corpus', {}), paths['acceptance'].parent, 'corpus'), 'acceptance consumes another corpus')
    for source, key in [('handoff', 'product'), ('interaction', 'interaction')]:
        need(same_ref(loaded['corpus'].get('sources', {}).get(source, {}), paths['corpus'].parent, key), 'corpus consumes another ' + source)
    registered = { (paths['collaboration'].parent / a.get('path', '')).resolve(): a.get('sha256')
                   for a in loaded['collaboration'].get('artifacts', []) }
    for key in REQUIRED - {'collaboration', 'semantic_review'}:
        need(registered.get(paths[key].resolve()) == refs[key]['sha256'], key + ': absent or stale collaboration registration')
    for ref in loaded['continuity'].get('artifacts', []):
        target = (paths['continuity'].parent / ref.get('path', '')).resolve()
        need(registered.get(target) == ref.get('sha256'), 'continuity source absent or stale in collaboration')
    for ref in loaded['corpus'].get('sources', {}).values():
        target = (paths['corpus'].parent / ref.get('path', '')).resolve()
        need(registered.get(target) == ref.get('sha256'), 'corpus source absent or stale in collaboration')
    art_by_id = {a.get('id'): a for a in loaded['collaboration'].get('artifacts', [])}
    cap_ref = art_by_id.get(loaded['collaboration'].get('capability_validation'))
    need(bool(cap_ref), 'missing capability validation artifact')
    if cap_ref:
        cap = json.loads((paths['collaboration'].parent / cap_ref['path']).read_text())
        discovery_ref = art_by_id.get(cap.get('discovery_artifact_id'), {})
        need(same_ref(discovery_ref, paths['collaboration'].parent, 'discovery'), 'capability consumes another discovery')
    commands = {
        'collaboration': [SCRIPTS/'check_collaboration.py', paths['collaboration']],
        'discovery': [SCRIPTS/'check_discovery.py', paths['discovery']],
        'continuity': [SCRIPTS/'check_continuity.py', paths['continuity'], '--require-baseline'],
        'handoff': [SCRIPTS/'check_handoff.py', paths['product'], paths['interaction']],
        'cases': [SCRIPTS/'check_cases.py', paths['corpus']],
        'execution': [SCRIPTS/'check_execution.py', paths['execution'], paths['acceptance']],
        'defects': [SCRIPTS.parent.parent/'fa-test-engineering/scripts/check_defects.py', paths['defects']],
    }
    for name, args in commands.items():
        result = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)
        try:
            report = json.loads(result.stdout)
        except ValueError:
            report = {'passed': False, 'errors': ['validator did not return JSON', result.stderr[-1000:]]}
        reports[name] = report
        need(result.returncode == 0 and report.get('passed') is True, name + ': validation failed')
    review = loaded['semantic_review']
    need(review.get('revision') == data['revision'], 'semantic review revision mismatch')
    producer_ids = set(data.get('producer_agent_ids', []))
    actual_producers = {r.get('agent_id') for r in loaded['collaboration'].get('receipts', []) if r.get('agent_id')}
    need(bool(producer_ids) and actual_producers <= producer_ids, 'missing actual producer agent IDs')
    need(bool(review.get('reviewer_agent_id')) and review.get('reviewer_agent_id') not in producer_ids,
         'semantic reviewer must be independent of producers')
    need(review.get('status') == 'pass', 'semantic review not passed')
    expected_checks = {'original-requirements', 'capability-boundaries', 'body-appendix',
                       'flow-text', 'rules-cases', 'metrics', 'correctness'}
    checks = review.get('checks', {})
    need(set(checks) == expected_checks and all(isinstance(v, dict) and v.get('status') == 'pass'
         and v.get('evidence') for v in checks.values()), 'missing semantic findings or evidence')
    expected = {k: refs[k]['sha256'] for k in REQUIRED - {'semantic_review'}}
    need(review.get('input_hashes') == expected, 'semantic review inputs are stale or incomplete')
    runs = loaded['execution'].get('runs', [])
    runtime = 'blocked'
    if runs and all(r.get('status') == 'pass' for r in runs):
        runtime = 'recorded-pass'
    elif any(r.get('status') == 'fail' for r in runs):
        runtime = 'recorded-fail'
    delivery = 'not-run'
    if data.get('mode') == 'published':
        need(loaded['collaboration'].get('state') == 'delivered', 'published mode requires delivered collaboration')
        publication = data.get('publication', {})
        need(publication.get('revision') == data['revision'], 'missing or stale publication revision')
        need(publication.get('corpus_sha256') == refs['corpus']['sha256'], 'publication consumes another corpus')
        need(bool(publication.get('table_url')) and publication.get('status') == 'readback-pass', 'missing Query table readback')
        sheets = publication.get('sheets', {})
        need(set(sheets) == {'标注query', '泛化query'}, 'missing Query sheets')
        cases_ref = loaded['corpus'].get('cases', {})
        cases_path = paths['corpus'].parent / cases_ref.get('path', '')
        raw_cases = cases_path.read_bytes()
        need(hashlib.sha256(raw_cases).hexdigest() == cases_ref.get('sha256'), 'publication cases hash mismatch')
        cases = [json.loads(line) for line in raw_cases.decode('utf-8').splitlines() if line.strip()]
        for name, sheet in sheets.items():
            snapshots = []
            for kind in ('expected', 'readback'):
                ref = sheet.get(kind, {})
                snapshot = path.parent / ref.get('path', '')
                need(snapshot.is_file(), name + ': missing ' + kind + ' snapshot')
                if snapshot.is_file():
                    raw = snapshot.read_bytes()
                    need(hashlib.sha256(raw).hexdigest() == ref.get('sha256'), name + ': stale ' + kind + ' snapshot')
                    snapshots.append(json.loads(raw))
            need(len(snapshots) == 2 and snapshots[0] == snapshots[1], name + ': readback content differs')
            case_kind = {'标注query': 'annotated', '泛化query': 'generalized'}.get(name)
            expected_rows = sorted([c for c in cases if c.get('kind') == case_kind], key=lambda c: c['id'])
            need(bool(expected_rows) and bool(snapshots) and snapshots[0] == expected_rows,
                 name + ': expected snapshot differs from corpus rows')
        delivery = 'recorded-readback' if not errors else 'blocked'
    else:
        need(data.get('mode') == 'local', 'mode must be local or published')
        need(loaded['collaboration'].get('state') != 'delivered', 'local mode cannot claim remote delivery')
    return {'passed': not errors, 'errors': errors, 'gates': reports, 'runtime': runtime,
            'delivery': delivery, 'scope': 'recorded integrity and review; runtime methods and actual publication evidence must be read separately'}


if __name__ == '__main__':
    try:
        if len(sys.argv) != 2:
            raise ValueError('usage: check_project.py project.json')
        result = check(sys.argv[1])
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        result = {'passed': False, 'errors': ['invalid project: ' + str(exc)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(not result['passed'])
