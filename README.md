# Dagger skill

The official agent skill for Dagger.

Install the module in a project with an existing skill directory:

```sh
dagger module install dagger.io/skill
dagger generate
```

The module detects `.agents/skills`, `.claude/skills`, `.cursor/skills`,
`.gemini/skills`, `.github/skills`, and `.opencode/skills` at the workspace root.
It skips symbolic links. It does not create agent settings directories.

Generation returns a changeset for review. An ownership marker identifies
installed skills. Existing skills without that marker cause an error.
Updates replace managed files; review the changeset to keep local edits.

The generator selects the latest stable Git release. `dagger.lock` records
the selected release and commit. Commit that file with the generated skill.
To select a newer release, run:

```sh
dagger lock update
dagger generate
```

Skill content lives in `content`. Publish stable semantic version tags
such as `v0.1.0` to release updates. Module and skill content can update separately:
the installed module stays pinned while its content lookup follows the lockfile.

Run the module checks with `dagger check`. Run `python3 tests/lock-update.py`
to test pinned generation, conflict handling, and release updates. The update
command is tested against a public repository. The generation test uses a
local Git service with two releases and checks both release pins.
