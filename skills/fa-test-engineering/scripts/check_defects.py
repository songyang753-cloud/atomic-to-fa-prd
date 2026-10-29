"""Check defect lifecycle receipts; semantic closure still needs independent review."""
import hashlib
import json
from pathlib import Path
import sys


def check(path):
    path = Path(path)
    data = json.loads(path.read_text())
    errors, seen = [], set()
    def receipt(ref, label):
        if not isinstance(ref, dict) or not ref.get('path') or not ref.get('sha256'):
            errors.append(label + ': missing receipt')
            return None
        file = path.parent / ref['path']
        if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest() != ref['sha256']:
            errors.append(label + ': missing or stale evidence')
            return None
        return file
    for d in data['defects']:
        label = d.get('id', '?')
        if label in seen:
            errors.append(label + ': duplicate ID')
        seen.add(label)
        if d.get('status') not in ['open', 'assigned', 'fixed-pending-retest', 'closed']:
            errors.append(label + ': invalid status')
        for key in ['id', 'severity', 'case_ids', 'expected', 'actual', 'owner', 'close_when']:
            if not d.get(key):
                errors.append(label + ': missing ' + key)
        if not d.get('evidence'):
            errors.append(label + ': missing reproduction evidence')
        for ref in d.get('evidence', []):
            receipt(ref, label)
        if d.get('status') in ['fixed-pending-retest', 'closed'] and not d.get('fix_version'):
            errors.append(label + ': missing fix version')
        if d.get('status') == 'closed':
            if not d.get('reviewer') or not d.get('reruns'):
                errors.append(label + ': missing independent review or reruns')
            for run in d.get('reruns', []):
                if run.get('status') != 'pass' or run.get('target_version') != d.get('fix_version'):
                    errors.append(label + ': rerun not passed at fix version')
                if not set(d['case_ids']).issubset(set(run.get('case_ids', []))):
                    errors.append(label + ': original cases missing from rerun')
                if not run.get('regression_case_ids') or not run.get('environment'):
                    errors.append(label + ': regression scope or environment missing')
                execution_path = receipt(run.get('execution'), label)
                if execution_path:
                    try:
                        execution = json.loads(execution_path.read_text())
                        scripts = Path(__file__).resolve().parents[2] / 'atomic-to-fa-prd' / 'scripts'
                        sys.path.insert(0, str(scripts))
                        import check_execution
                        errors.extend(label + ': execution: ' + e for e in check_execution.check(execution_path))
                        if execution.get('target', {}).get('version') != run.get('target_version'):
                            errors.append(label + ': execution version differs from rerun')
                        if execution.get('environment') != run.get('environment'):
                            errors.append(label + ': execution environment differs from rerun')
                        rows = {r['case_id']: r for r in execution.get('runs', [])}
                        for cid in set(run.get('case_ids', []) + run.get('regression_case_ids', [])):
                            row = rows.get(cid, {})
                            if row.get('status') != 'pass' or row.get('method') in (None, 'design', 'evidence-replay'):
                                errors.append(label + ': case not executed and passed: ' + cid)
                    except (OSError, ValueError, KeyError, TypeError, AttributeError, ImportError) as exc:
                        errors.append(label + ': invalid execution: ' + str(exc))
    return errors


if __name__ == '__main__':
    result = check(sys.argv[1])
    print(json.dumps({'passed': not result, 'errors': result}, ensure_ascii=False, indent=2))
    sys.exit(bool(result))
