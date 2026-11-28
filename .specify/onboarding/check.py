import argparse, hashlib, json, re, subprocess, sys
PIN = '6ba8beefff8d6408cadd62038e92d459093e33a8'
URL = 'https://github.com/github/spec-kit'
POLICIES = ('docs/project-profile.md', '.specify/memory/constitution.md',
            '.specify/onboarding-policy.json', '.specify/retention.yml')
RECEIPT = '.specify/bootstrap-receipt.json'
HEX = re.compile(r'^[0-9a-f]{64}$')
def git(repo, *args):
    return subprocess.check_output(['git', '-C', repo, *args])
def require(ok, message):
    if not ok: raise ValueError(message)
def read_tree(repo, commit):
    out = {}
    for row in git(repo, 'ls-tree', '-rz', commit).split(b'\0'):
        if not row: continue
        meta, path = row.split(b'\t', 1)
        mode, kind, oid = meta.decode().split()
        if kind == 'blob': out[path.decode()] = (mode, oid)
    return out
def tree(repo, commit):
    require(git(repo, 'rev-parse', 'HEAD').decode().strip() == commit,
            'HEAD differs from reviewed commit')
    require(not git(repo, 'status', '--porcelain', '--untracked-files=all'),
            'dirty checkout')
    return read_tree(repo, commit)
def blob(repo, t, path):
    require(path in t, 'missing tracked path: ' + path)
    mode, oid = t[path]
    require(mode in ('100644', '100755'), 'not regular file: ' + path)
    return git(repo, 'cat-file', 'blob', oid)
def json_at(repo, t, path):
    try: return json.loads(blob(repo, t, path))
    except Exception as e: raise ValueError('invalid JSON ' + path + ': ' + str(e))
def normal(path, raw):
    if path.startswith('.specify/integrations/') and path.endswith('.manifest.json'):
        obj = json.loads(raw); obj.pop('installed_at', None)
        return (json.dumps(obj, sort_keys=True, separators=(',', ':')) + '\n').encode()
    if path == '.specify/extensions/.registry':
        obj = json.loads(raw)
        for item in obj.get('extensions', {}).values(): item.pop('installed_at', None)
        return (json.dumps(obj, sort_keys=True, separators=(',', ':')) + '\n').encode()
    if path == '.specify/workflows/workflow-registry.json':
        obj = json.loads(raw)
        for item in obj.get('workflows', {}).values():
            item.pop('installed_at', None); item.pop('updated_at', None)
        return (json.dumps(obj, sort_keys=True, separators=(',', ':')) + '\n').encode()
    return raw
def sha(path, raw):
    return hashlib.sha256(normal(path, raw)).hexdigest()
def reserved(path):
    codex = path.startswith('.agents/skills/speckit-') and '/' in path[len('.agents/skills/'):]
    opencode = path.startswith('.opencode/commands/speckit.')
    omp = path.startswith('.omp/commands/speckit.')
    return codex or opencode or omp
def load(path, expected_pin=PIN):
    m = json.load(open(path, encoding='utf-8'))
    require(m.get('upstream_commit') == expected_pin, 'trusted pin mismatch')
    files = m.get('owned_files')
    require(isinstance(files, dict) and files, 'empty trusted owned-file map')
    for p, x in files.items():
        require(not p.startswith('/') and '..' not in p.split('/'), 'unsafe path: ' + p)
        require(x.get('mode') in ('100644', '100755'), 'invalid file mode: ' + p)
        require(isinstance(x.get('sha256'), str) and HEX.fullmatch(x['sha256']),
                'invalid SHA256: ' + p)
    return m
def capture(repo, base, commit, output):
    t = tree(repo, commit); read_tree(repo, base)
    require(git(repo, 'merge-base', '--is-ancestor', base, commit) == b'',
            'reference base is not ancestor of generation commit')
    changed = git(repo, 'diff', '--name-only', '-z', base, commit).decode().split('\0')
    owned = {}
    for p in sorted(x for x in changed if x and x not in POLICIES):
        raw = blob(repo, t, p)
        owned[p] = {'mode': t[p][0], 'sha256': sha(p, raw)}
    init = json_at(repo, t, '.specify/init-options.json')
    require(all(k in init for k in ('ai', 'integration', 'script', 'speckit_version')),
            'pinned init metadata fields missing')
    require(init['ai'] == 'codex' and init['integration'] == 'codex'
            and init['speckit_version'] == '1.4.5', 'unexpected pinned init values')
    manifests = {}
    for key in ('codex', 'opencode', 'omp'):
        p = '.specify/integrations/' + key + '.manifest.json'
        obj = json_at(repo, t, p)
        require(obj.get('integration') == key and obj.get('version') == '1.4.5',
                'wrong integration manifest: ' + key)
        obj.pop('installed_at', None)
        manifests[p] = obj
    bundled = '.specify/integrations/speckit.manifest.json'
    bundled_obj = json_at(repo, t, bundled); bundled_obj.pop('installed_at', None)
    manifests[bundled] = bundled_obj
    event_path = '.specify/integration-events.yml'
    events = blob(repo, t, event_path).decode() if event_path in t else None
    out = {'upstream_commit': PIN, 'base_commit': base, 'generation_commit': commit,
           'owned_files': owned, 'init_options': init,
           'integration_manifests': manifests, 'integration_events_yaml': events,
           'event_options': {'codex': '--events false', 'opencode': '--events false', 'omp': 'omitted'}}
    open(output, 'w', encoding='utf-8').write(json.dumps(out, sort_keys=True, indent=2) + '\n')
def collision(repo, base, manifest, previous=None):
    t = read_tree(repo, base)
    previous_paths = set(previous['owned_files']) if previous else set()
    if previous:
        expected_old = {p for p in previous_paths if reserved(p)}
        actual_old = {p for p in t if reserved(p)}
        require(actual_old == expected_old,
                'upgrade base has an unapproved reserved-path collision')
    else:
        reserved_collisions = sorted(p for p in t if reserved(p))
        require(not reserved_collisions,
                'reviewed-base reserved Spec Kit namespace collision: ' + repr(reserved_collisions))
    for managed in manifest['owned_files']:
        for existing in t:
            if previous and existing == managed and existing in previous_paths:
                continue
            require(existing != managed and not existing.startswith(managed + '/')
                    and not managed.startswith(existing + '/'),
                    'reviewed-base file/prefix collision: ' + managed + ' vs ' + existing)
def verify(repo, commit, manifest, runbook):
    t = tree(repo, commit)
    trusted_paths = set(manifest['owned_files'])
    expected_reserved = {p for p in trusted_paths if reserved(p)}
    actual_reserved = {p for p in t if reserved(p)}
    require(actual_reserved == expected_reserved,
            'reserved Spec Kit namespace differs from trusted set: extra=' +
            repr(sorted(actual_reserved - expected_reserved)) + ' missing=' +
            repr(sorted(expected_reserved - actual_reserved)))
    for p, rec in manifest['owned_files'].items():
        require(t.get(p, (None,))[0] == rec['mode'], 'managed mode mismatch: ' + p)
        require(sha(p, blob(repo, t, p)) == rec['sha256'], 'managed digest mismatch: ' + p)
    init = json_at(repo, t, '.specify/init-options.json')
    require(init == manifest['init_options'], 'init metadata differs from pinned clean generation')
    for p, expected in manifest['integration_manifests'].items():
        actual = json_at(repo, t, p); actual.pop('installed_at', None)
        require(actual == expected, 'normalized integration manifest mismatch: ' + p)
        claimed = actual.get('files', {})
        require(set(claimed) <= set(manifest['owned_files']),
                'manifest claims unapproved files: ' + p)
        for owned_path, recorded_sha in claimed.items():
            require(recorded_sha == sha(owned_path, blob(repo, t, owned_path)),
                    'integration manifest content hash mismatch: ' + owned_path)
    actual_manifest_paths = sorted(p for p in t if p.startswith('.specify/integrations/')
                                   and p.endswith('.manifest.json'))
    require(actual_manifest_paths == sorted(manifest['integration_manifests']),
            'integration manifest path set mismatch')
    ep = '.specify/integration-events.yml'
    events = blob(repo, t, ep).decode() if ep in t else None
    require(events == manifest['integration_events_yaml'], 'persisted event override differs')
    for p in POLICIES:
        require(bool(blob(repo, t, p).strip()), 'missing or empty repo-owned file: ' + p)
    receipt = json_at(repo, t, RECEIPT)
    expected = {'runbook_version': runbook, 'upstream_url': URL,
                'upstream_commit': PIN, 'integrations': ['codex', 'opencode', 'omp'],
                'event_options': manifest['event_options'],
                'generated_files': manifest['owned_files']}
    require(receipt == expected, 'bootstrap receipt mismatch')
ap = argparse.ArgumentParser()
ap.add_argument('mode', choices=('capture', 'preflight', 'receipt', 'verify'))
ap.add_argument('--repo', required=True); ap.add_argument('--commit', required=True)
ap.add_argument('--base'); ap.add_argument('--expected'); ap.add_argument('--output')
ap.add_argument('--previous'); ap.add_argument('--previous-pin')
ap.add_argument('--runbook', required=True)
a = ap.parse_args()
try:
    if a.mode == 'capture':
        require(a.base and a.output, 'capture requires --base and --output')
        capture(a.repo, a.base, a.commit, a.output)
    else:
        require(a.expected, 'mode requires --expected')
        m = load(a.expected)
        if a.mode == 'preflight':
            require(a.base == a.commit, 'preflight commit must equal reviewed base')
            require(not a.previous or a.previous_pin, 'upgrade preflight requires --previous-pin')
            prev = load(a.previous, a.previous_pin) if a.previous else None
            tree(a.repo, a.commit); collision(a.repo, a.commit, m, prev); print('PASS preflight')
        elif a.mode == 'receipt':
            t = tree(a.repo, a.commit)
            for p, rec in m['owned_files'].items():
                require(sha(p, blob(a.repo, t, p)) == rec['sha256'],
                        'candidate differs from trusted generation: ' + p)
            receipt = {'runbook_version': a.runbook, 'upstream_url': URL,
                       'upstream_commit': PIN, 'integrations': ['codex', 'opencode', 'omp'],
                       'event_options': m['event_options'], 'generated_files': m['owned_files']}
            open(a.output, 'w', encoding='utf-8').write(json.dumps(receipt, sort_keys=True, indent=2) + '\n')
        else:
            verify(a.repo, a.commit, m, a.runbook); print('PASS verify ' + a.commit)
except Exception as e:
    print('FAIL: ' + str(e), file=sys.stderr); sys.exit(1)

