#!/usr/bin/env python3
"""Check the generator against a pinned release and a newer upstream release."""

import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def run(work, *args):
    return subprocess.check_output(
        ["dagger", *([] if args[0] == "lock" else ["--silent"]), *args], cwd=work, text=True
    ).strip()


with tempfile.TemporaryDirectory(prefix="dagger-skill-") as temp:
    work = Path(temp)
    subprocess.run(["git", "init", "-q", temp], check=True)
    for name in ("dagger-module.toml", "main.dang"):
        shutil.copy(ROOT / name, work / name)
    shutil.copytree(ROOT / "tests", work / "tests")
    (work / "dagger.toml").write_text(
        '[modules.dagger-skill]\nsource = "."\n'
        '[modules.dagger-skill.settings]\nrepository = "dag://skill-tests/repository"\n'
        '[modules.skill-tests]\nsource = "tests"\n'
    )
    (work / ".agents/skills").mkdir(parents=True)
    unreleased = subprocess.run(
        ["dagger", "--silent", "api", "call", "skill-tests", "unreleased", "is-empty"],
        cwd=work, capture_output=True, text=True,
    )
    assert unreleased.returncode != 0, "Installed unreleased content"
    assert "No stable skill release is available" in unreleased.stderr
    hostname = run(work, "api", "call", "skill-tests", "server", "hostname")
    old_commit = run(work, "api", "call", "skill-tests", "repository", "tag", "--name=v1.0.0", "commit")
    old_ref = "refs/tags/v1.0.0"
    identity = hostname + "/skill"
    entries = [
        [["version", "2"]],
        ["", "git-latest", [identity], old_ref],
        ["", "git-sha", [identity, old_ref], old_commit],
    ]
    lock = work / "dagger.lock"
    lock.write_text("\n".join(json.dumps(row) for row in entries) + "\n")
    unmanaged = work / ".agents/skills/dagger"
    unmanaged.mkdir()
    (unmanaged / "SKILL.md").write_text("user skill\n")
    rejected = subprocess.run(
        ["dagger", "--silent", "generate", "-y"], cwd=work,
        capture_output=True, text=True,
    )
    assert rejected.returncode != 0, "Replaced an unmanaged skill"
    assert "not managed by this module" in rejected.stderr
    assert (unmanaged / "SKILL.md").read_text() == "user skill\n"
    shutil.rmtree(unmanaged)
    run(work, "generate", "-y")
    skill = work / ".agents/skills/dagger/SKILL.md"
    assert skill.read_text() == "released skill\n", "Did not use the old release pin"
    first_lock = lock.read_text()
    run(work, "generate", "-y")
    assert skill.read_text() == "released skill\n", "Generation followed the newer release"
    assert lock.read_text() == first_lock, "Generation changed the lockfile"
    # The fixture uses a private engine service. lock update cannot reconstruct
    # its service binding from a canonical lock identity. Test the update command
    # against a public repository, then test generation with a refreshed fixture pin.
    public = work / "public"
    public.mkdir()
    (public / "dagger.toml").write_text("")
    query = public / "latest.graphql"
    query.write_text('{ git(url: "https://github.com/dagger/go") { latest { ref commit } } }')
    public_entries = [
        [["version", "2"]],
        ["", "git-latest", ["github.com/dagger/go"], "refs/tags/v0.1.0"],
    ]
    public_lock = public / "dagger.lock"
    public_lock.write_text("\n".join(json.dumps(row) for row in public_entries) + "\n")
    pinned = json.loads(run(public, "query", "--doc", str(query)))
    assert pinned["git"]["latest"]["ref"] == "refs/tags/v0.1.0"
    run(public, "lock", "update")
    refreshed = json.loads(run(public, "query", "--doc", str(query)))
    assert refreshed["git"]["latest"]["ref"] != "refs/tags/v0.1.0", "Lock update kept the old release"
    new_commit = run(work, "api", "call", "skill-tests", "repository", "tag", "--name=v2.0.0", "commit")
    entries[1][3] = "refs/tags/v2.0.0"
    entries[2] = ["", "git-sha", [identity, "refs/tags/v2.0.0"], new_commit]
    lock.write_text("\n".join(json.dumps(row) for row in entries) + "\n")
    run(work, "generate", "-y")
    assert skill.read_text() == "released skill two\n", "Lock update did not select the new release"
    run(work, "check", "--generated=true")
    print("Pinned generation, repeat generation, lock update, and stale-file checks passed.")
