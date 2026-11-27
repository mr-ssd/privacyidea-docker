# check-case.py --id ID --repo REPO --base BASE_SHA --head HEAD_SHA --manifest JSON_MANIFEST
import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--id', required=True, choices=['FEAT-1','FEAT-2','FEAT-3','BUG-1','BUG-2','BUG-3','BUG-4','IDEA-1','IDEA-2','IDEA-3','IDEA-4','IDEA-5'])
p.add_argument('--repo', required=True)
p.add_argument('--base', required=True)
p.add_argument('--head', required=True)
p.add_argument('--manifest', required=True)
a = p.parse_args()
repo = Path(a.repo).resolve()
m = json.loads(Path(a.manifest).read_text(encoding='utf-8'))
ids = {'feature':['FEAT-1','FEAT-2','FEAT-3'], 'bug':['BUG-1','BUG-2','BUG-3','BUG-4'], 'idea':['IDEA-1','IDEA-2','IDEA-3','IDEA-4','IDEA-5']}
key = m.get('case_key', '')
kind = m.get('case_type')
assert kind in ids, 'unknown case_type'
expected = ids[kind]
assert re.fullmatch(r'pers-[0-9]+-[a-z0-9-]+', key) and m.get('reviewed_baseline_sha') == a.base
assert m.get('acceptance_ids') == expected and m.get('approved_check_ids') == expected, 'manifest acceptance/check IDs must exactly match case type'
assert a.id in expected
if kind == 'feature': assert m.get('feature_directory') == f'specs/{key}', 'feature_directory must be derived from case_key'

def git(*args):
    return subprocess.check_output(['git', '-C', str(repo), *args])

trace_path = f'.specify/traceability/cases/{key}.yml'
if kind == 'feature':
    required_paths = {'Makefile', f'specs/{key}/', f'.specify/features/{key}/', trace_path}
elif kind == 'bug':
    required_paths = {'README.md', f'.specify/bugs/{key}/', trace_path}
else:
    required_paths = {f'.specify/assessments/{key}/{name}.md'
                      for name in ('intake','research','problem','concept','decision')}
    required_paths.add(trace_path)
assert isinstance(m.get('allowed_paths'), list) and set(m['allowed_paths']) == required_paths, 'manifest allowed_paths must exactly match trusted case policy'
changed = set(git('diff','--no-renames','--name-only',f'{a.base}...{a.head}').decode().splitlines())
def path_allowed(path):
    return any(path == item or (item.endswith('/') and path.startswith(item))
               for item in required_paths)
assert all(path_allowed(path) for path in changed), 'PR changed path outside case allowed_paths: ' + repr(sorted(path for path in changed if not path_allowed(path)))

def blob(commit, path):
    row = git('ls-tree', commit, '--', path).decode().rstrip('\n')
    meta, found = row.split('\t', 1)
    fields = meta.split()
    mode, oid = fields[0], fields[2]
    assert found == path and mode in ('100644', '100755'), 'required path is not a tracked regular file: ' + path
    return git('cat-file', 'blob', oid)

if a.id.startswith('FEAT-'):
    makefile = blob(a.head, 'Makefile').decode()
    assert re.search(r'(?m)^test-release-input:\n\tbash tests/test-release-input\.sh\s*$', makefile), 'target recipe mismatch'
    if a.id == 'FEAT-2':
        run = subprocess.run(['make', '-n', 'test-release-input'], cwd=repo, text=True, capture_output=True)
        assert run.returncode == 0 and run.stdout.strip() == 'bash tests/test-release-input.sh'
    elif a.id == 'FEAT-3':
        good = subprocess.run(['make', 'test-release-input'], cwd=repo)
        assert good.returncode == 0, 'target did not propagate success'
        with tempfile.TemporaryDirectory() as td:
            marker = Path(td) / 'stub-called'
            stub = Path(td) / 'bash'
            stub.write_text('#!/bin/sh\nif [ "$1" = tests/test-release-input.sh ]; then printf called > "$MULTICA_STUB_MARKER"; exit 37; fi\nexec /bin/bash "$@"\n')
            stub.chmod(0o755)
            env = {**os.environ, 'PATH': td + ':' + os.environ['PATH'], 'MULTICA_STUB_MARKER': str(marker)}
            bad = subprocess.run(['make', 'test-release-input'], cwd=repo, env=env)
            assert bad.returncode != 0 and marker.read_text() == 'called', 'failure stub did not run or Make target swallowed its failure'
elif a.id.startswith('BUG-'):
    readme = blob(a.head, 'README.md').decode()
    if a.id == 'BUG-1':
        assert 'will update privacyIDEA to the latest version' in blob(a.base, 'README.md').decode()
    elif a.id == 'BUG-2':
        assert 'PI_AUTO_UPDATE set to **true** will run the privacyIDEA schema upgrade.' in readme and 'will update privacyIDEA to the latest version' not in readme
    elif a.id == 'BUG-3':
        assert 'Make sure you have backup your data before setting `PI_AUTO_UPDATE` to **true**.' in readme
    elif a.id == 'BUG-4':
        assert b'privacyidea-schema-upgrade' in blob(a.head, 'rootfs/usr/local/bin/configure_privacyidea.sh')
else:
    reports = [f'.specify/assessments/{key}/{x}.md' for x in ('intake','research','problem','concept','decision')]
    data = [blob(a.head, path).decode() for path in reports]
    if a.id == 'IDEA-1':
        assert all(x.strip() for x in data), 'all five reports nonempty'
    elif a.id == 'IDEA-2':
        text = data[1].lower()
        assert all(word in text for word in ('source','confidence','for','against'))
    elif a.id == 'IDEA-3':
        assert 'tradeoff' in data[3].lower()
    elif a.id == 'IDEA-4':
        assert len(re.findall(r'(?m)^Verdict: (go|needs-clarification|kill)$', data[4])) == 1
    elif a.id == 'IDEA-5':
        actual = sorted(git('diff','--no-renames','--name-only',f'{a.base}...{a.head}').decode().splitlines())
        allowed = sorted(reports + [f'.specify/traceability/cases/{key}.yml'])
        assert actual == allowed, f'PR paths mismatch: {actual}'
print(json.dumps({'acceptance_id':a.id, 'check_id':a.id, 'outcome':'PASS', 'head':a.head}))
