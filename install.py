#!/usr/bin/env python3
"""Install shared skills without overwriting existing files."""
from pathlib import Path
import shutil

source = Path(__file__).resolve().parent / "skills"
names = sorted(p.name for p in source.iterdir() if p.is_dir())
shared = Path.home() / ".agents/skills"
hosts = [Path.home() / ".codex/skills", Path.home() / ".claude/skills"]
targets = [shared / n for n in names] + [h / n for h in hosts for n in names]
conflicts = [str(p) for p in targets if p.exists() or p.is_symlink()]
if conflicts:
    raise SystemExit("Existing skills found; no changes made:\n" + "\n".join(conflicts))
shared.mkdir(parents=True, exist_ok=True)
for name in names:
    shutil.copytree(source / name, shared / name)
for host in hosts:
    host.mkdir(parents=True, exist_ok=True)
    for name in names:
        (host / name).symlink_to(shared / name, target_is_directory=True)
print(f"Installed {len(names)} skills; Codex and Claude discovery links ready.")
