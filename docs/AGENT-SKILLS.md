# Invoking the local homepage skill

## Codex

Run Codex from the repository root (or a subdirectory within the Git checkout). Repository skills live under `.agents/skills/build-homepage/SKILL.md`.

Invoke by typing **`$build-homepage`** in the agent prompt, or select it from the skill picker where supported.

Suggested request:

> `$build-homepage` — Read my latest content.md, choose the Bold Editorial layout, generate the site, run tests and tell me which files to commit.

## Claude Code

Run Claude Code inside the repository. Project skills live under `.claude/skills/build-homepage/SKILL.md`.

Invoke **`/build-homepage`** (or ask Claude to use the build-homepage skill).

Suggested request:

> `/build-homepage` — Regenerate and verify the production-ready homepage from content.md.

## Without either agent

```bash
python -m homepage.cli plan
python -m homepage.cli build --require-plan
python -m homepage.cli validate
python -m homepage.cli serve
```

The deterministic fallback is designed to be useful on its own; no API key is needed.

## How publishing differs from building

The local skill produces the site in `dist/`. It does **not** publish automatically. Committing and pushing the repository to `main` starts `.github/workflows/pages.yml`, which builds, tests, validates and deploys the page. You can also run the workflow manually in the GitHub Actions tab. GitHub Pages must use the GitHub Actions deployment source.
