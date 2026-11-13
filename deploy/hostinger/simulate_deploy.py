#!/usr/bin/env python3
"""Dry-run the server half of .github/workflows/deploy.yml on this machine.

No VPS, Docker or network needed: `docker`, `curl` and `sleep` are replaced
by small shims, and the "VPS checkout" is a clone of a throwaway repository.
It checks the parts that are easy to get wrong in shell:

  1. a normal deploy moves the checkout to the new commit and leaves a
     backup/production-* branch at the old one;
  2. a failed health check rolls the code back, and when the deploy
     included migrations it prints the restore command for the backup;
  3. the next deploy after a rollback records the commit that was actually
     running (the rolled-back one), not the broken tip of main;
  4. local edits on the server stop the deploy before anything changes;
  5. a failed backup stops a deploy that contains migrations.

    python3 deploy/hostinger/simulate_deploy.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/deploy.yml"


def remote_script() -> str:
    wf = yaml.safe_load(WORKFLOW.read_text())
    for step in wf["jobs"]["deploy"]["steps"]:
        if "appleboy/ssh-action" in step.get("uses", ""):
            return step["with"]["script"]
    raise SystemExit("deploy step not found")


def sh(cmd: str, cwd: Path, env=None, check=True) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", "-c", cmd], cwd=cwd, env=env, check=check, capture_output=True, text=True)


SHIMS = {
    # docker: record the call; "up" fails if FAIL_UP is set; pg_dump prints bytes;
    # the backup fails if FAIL_BACKUP is set.
    "docker": r"""#!/bin/bash
echo "docker $*" >> "$SIM_LOG"
case "$*" in
  *pg_dump*) [ -n "${FAIL_BACKUP:-}" ] && exit 1; echo "PGDMP-fake" ;;
  *"compose up"*) [ -n "${FAIL_UP:-}" ] && exit 1 ;;
esac
exit 0
""",
    # curl: healthy unless the running checkout is the commit named in BAD_SHA.
    "curl": r"""#!/bin/bash
[ -n "${BAD_SHA:-}" ] && [ "$(git rev-parse HEAD)" = "$BAD_SHA" ] && exit 22
exit 0
""",
    "sleep": "#!/bin/sh\nexit 0\n",
}


def main() -> int:
    script = remote_script()
    failures: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        bin_dir = t / "bin"
        bin_dir.mkdir()
        for name, body in SHIMS.items():
            p = bin_dir / name
            p.write_text(body)
            p.chmod(0o755)

        origin = t / "origin.git"
        work = t / "dev"
        project = t / "vps" / "groundkart"
        backups = t / "backups"
        log = t / "sim.log"
        sh(f"git init -q --bare -b main {origin}", t)
        sh(f"git clone -q {origin} {work}", t)
        git_id = "-c user.name=sim -c user.email=sim@example.invalid"

        def commit(msg: str, path: str, content: str) -> str:
            f = work / path
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(content)
            sh(f"git add -A && git {git_id} commit -q -m '{msg}' && git push -q origin HEAD:main", work)
            return sh("git rev-parse HEAD", work).stdout.strip()

        (work / ".gitignore").write_text(".env\n")
        # The workflow calls the backup script from the checkout.
        (work / "deploy/hostinger").mkdir(parents=True)
        (work / "deploy/hostinger/backup-db.sh").write_text((ROOT / "deploy/hostinger/backup-db.sh").read_text())
        c1 = commit("c1", "backend/alembic/versions/a.py", "a\n")
        sh(f"git clone -q {origin} {project}", t)
        (project / ".env").write_text(f"API_PORT=5001\nWEB_PORT=3002\nBACKUP_DIR={backups}\n")

        run_script = script.replace('PROJECT="/home/deploy/apps/groundkart"', f'PROJECT="{project}"')

        def deploy(**flags) -> subprocess.CompletedProcess:
            env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "SIM_LOG": str(log), **flags}
            return subprocess.run(["bash", "-c", run_script], cwd=project, env=env, capture_output=True, text=True)

        def head() -> str:
            return sh("git rev-parse HEAD", project).stdout.strip()

        def expect(cond: bool, label: str, res: subprocess.CompletedProcess | None = None):
            print(("PASS " if cond else "FAIL ") + label)
            if not cond:
                failures.append(label)
                if res is not None:
                    print(res.stdout[-3000:], res.stderr[-2000:], sep="\n")

        # 1. Normal deploy.
        c2 = commit("c2", "frontend/a.txt", "x\n")
        r = deploy()
        branches = sh("git branch --list 'backup/production-*' --format='%(objectname)'", project).stdout.split()
        expect(r.returncode == 0 and head() == c2, "1. normal deploy reaches the new commit", r)
        expect(c1 in branches, "1. rollback branch points at the previous commit", r)
        expect(any(backups.glob("groundkart-predeploy-*.dump")), "1. database backup taken before building", r)
        expect("down -v" not in log.read_text(), "1. never runs docker compose down -v")

        # 2. Broken release with a migration: health fails, code rolls back.
        c3 = commit("c3", "backend/alembic/versions/b.py", "b\n")
        r = deploy(BAD_SHA=c3)
        expect(r.returncode != 0 and head() == c2 and "Rollback completed" in r.stdout, "2. failed health check rolls the code back", r)
        expect("restore-db.sh" in r.stdout, "2. migration deploy prints the restore command", r)

        # 3. Next deploy after a rollback records the commit that was running.
        c4 = commit("c4", "frontend/b.txt", "y\n")
        r = deploy()
        expect(r.returncode == 0 and head() == c4, "3. fixed release deploys after a rollback", r)
        expect(f"Previous production commit: {c2}" in r.stdout, "3. previous commit is the rolled-back one, not the broken tip", r)

        # 4. Local edits on the server stop the deploy.
        (project / "frontend/b.txt").write_text("edited on the server\n")
        c5 = commit("c5", "frontend/c.txt", "z\n")
        r = deploy()
        expect(r.returncode != 0 and head() == c4 and "local changes exist" in r.stdout, "4. local changes stop the deploy", r)
        sh("git checkout -q -- frontend/b.txt", project)

        # 5. Backup fails on a deploy with migrations: stop before building.
        c6 = commit("c6", "backend/alembic/versions/c.py", "c\n")
        log.write_text("")
        r = deploy(FAIL_BACKUP="1")
        expect(r.returncode != 0 and head() == c4 and "Backup failed" in r.stdout, "5. failed backup stops a migration deploy", r)
        expect("compose up" not in log.read_text(), "5. nothing was rebuilt", r)

        # And the same release goes out once the backup works.
        r = deploy()
        expect(r.returncode == 0 and head() == c6, "5. retry with a working backup deploys", r)
        _ = c5

    print(f"\n{'All checks passed' if not failures else f'{len(failures)} check(s) failed'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
