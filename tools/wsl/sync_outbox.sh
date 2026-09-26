#!/usr/bin/env bash
# Publishes batches that the cloud Claude session writes into the Windows outbox
# (C:\Users\lenya\arc_extended_arga\cloud_outbox) to the public GitHub repo.
# Each batch: <outbox>/<batch_id>/{MANIFEST.json, files/..., READY}. MANIFEST.json =
# {"message": "...", "files": {"rel/path": "<sha256>"}, "delete": ["rel/path", ...]}.
# Guards: complete batches only (READY + every sha256 matches), relative paths only,
# extension allow-list, 10 MB per file, secret-pattern scan, never touches .git or this
# sync tooling, pause switch ~/arc/SYNC_PAUSED. Kaggle actions are never automated here.
set -uo pipefail
OUTBOX="${OUTBOX:-/mnt/c/Users/lenya/arc_extended_arga/cloud_outbox}"
REPO="${REPO:-$HOME/arc/arc2-object-dsl}"
export PATH="$HOME/.local/bin:$PATH"
[ -e "$HOME/arc/SYNC_PAUSED" ] && exit 0
[ -d "$OUTBOX" ] && [ -d "$REPO/.git" ] || exit 0
exec 9>"$HOME/arc/.sync.lock"; flock -n 9 || exit 0
for dir in "$OUTBOX"/*/; do
  dir="${dir%/}"; id="$(basename "$dir")"
  [ -f "$dir/READY" ] || continue
  [ -f "$dir/RESULT.json" ] && continue
  result=$(python3 - "$dir" "$REPO" <<'PY'
import hashlib, json, os, re, shutil, subprocess, sys
src, repo = sys.argv[1], sys.argv[2]
ALLOWED = {".py", ".md", ".json", ".ipynb", ".txt", ".sh", ".cfg", ".toml", ".yml", ".yaml", ".ttl", ".gitignore", ""}
SECRET = re.compile(rb'(ghp_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-ant-[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"key"\s*:\s*"[0-9a-f]{32}")')
PROTECTED = ("tools/wsl/", ".git/")
def fail(msg):
    print(json.dumps({"status": "rejected", "reason": msg})); sys.exit(0)
try:
    m = json.load(open(os.path.join(src, "MANIFEST.json")))
except Exception as e:
    fail(f"bad manifest: {e}")
archive = os.path.join(src, "files.tar.gz")
if os.path.isfile(archive):
    import tarfile, tempfile
    tmp = tempfile.mkdtemp(prefix="arcbatch_")
    with tarfile.open(archive, "r:gz") as tf:
        for member in tf.getmembers():
            if not member.isfile() or member.name.startswith("/") or ".." in member.name.split("/"):
                fail(f"unsafe archive member {member.name}")
            tf.extract(member, os.path.join(tmp, "files"))
    src = tmp
files, deletes = m.get("files", {}), m.get("delete", [])
for rel in list(files) + list(deletes):
    if rel.startswith("/") or ".." in rel.split("/") or rel.startswith(PROTECTED):
        fail(f"forbidden path {rel}")
for rel, digest in files.items():
    p = os.path.join(src, "files", rel)
    if not os.path.isfile(p): fail(f"missing {rel}")
    ext = os.path.splitext(rel)[1] if not os.path.basename(rel).startswith(".") else os.path.basename(rel)
    if ext not in ALLOWED: fail(f"extension not allowed: {rel}")
    data = open(p, "rb").read()
    if len(data) > 10 * 1024 * 1024: fail(f"too large: {rel}")
    if hashlib.sha256(data).hexdigest() != digest: fail(f"sha256 mismatch: {rel}")
    if SECRET.search(data): fail(f"secret-like pattern in {rel}")
for rel in files:
    dst = os.path.join(repo, rel); os.makedirs(os.path.dirname(dst) or repo, exist_ok=True)
    shutil.copyfile(os.path.join(src, "files", rel), dst)
for rel in deletes:
    p = os.path.join(repo, rel)
    if os.path.isfile(p): os.remove(p)
def git(*a): return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True)
git("add", "-A")
if not git("status", "--porcelain").stdout.strip():
    print(json.dumps({"status": "no_changes"})); sys.exit(0)
c = git("commit", "-m", m.get("message", "cloud batch")[:500])
if c.returncode:
    git("reset", "--hard", "HEAD"); git("clean", "-fd")
    fail("commit failed: " + c.stderr[-300:])
p = git("push", "origin", "HEAD")
sha = git("rev-parse", "HEAD").stdout.strip()
if p.returncode:
    print(json.dumps({"status": "committed_not_pushed", "commit": sha, "error": p.stderr[-300:]})); sys.exit(0)
print(json.dumps({"status": "pushed", "commit": sha}))
PY
)
  [ -n "$result" ] || result='{"status": "error"}'
  printf '{"batch": "%s", "time": "%s", "result": %s}\n' "$id" "$(date -Is)" "$result" > "$dir/RESULT.json"
  echo "$(date -Is) $id ${result}" >> "$HOME/arc/sync_outbox.log"
done
