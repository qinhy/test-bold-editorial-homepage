# Bold Editorial — Markdown to homepage

**Edit one Markdown file. Invoke a Codex or Claude Code skill. Get a polished, deployable static homepage.**

This open-source-ready starter is a **Markdown website compiler**, not a chat UI and not a conventional Markdown viewer. The LLM chooses the layout; a deterministic Python renderer generates safe HTML and CSS from the user's original content.

- **Input:** `content.md` + `style.yaml` + `view-rules.yaml`
- **Design intelligence:** Codex `$build-homepage` or Claude Code `/build-homepage`
- **Output:** `dist/index.html` + `dist/style.css` + published assets
- **Hosting:** GitHub Pages with GitHub Actions; no separate server or API key required
- **Theme:** Bold Editorial: warm paper, large serif headlines, rust-red accents, asymmetrical grids


### Prediction image asset

The original model README linked to `./asset/ChatGPTImage16_02_44-prediction.jpg` but did **not** include the JPEG file in the supplied Markdown. The homepage link is restored as `assets/ChatGPTImage16_02_44-prediction.jpg` to match this generator's asset-copying convention.

This repository temporarily bundles a **visibly labeled placeholder**, not a reproduction or a model output. **Before public release, replace `assets/ChatGPTImage16_02_44-prediction.jpg` with the original JPEG.** Do not change the Markdown image path. Running the homepage skill or `python -m homepage.cli build` copies the file into `dist/assets/`. If you remove the asset without replacing it, the build intentionally fails rather than publishing a broken image.

## Quick start

Extract the ZIP, open the repository folder in your terminal or agent, and create a Python environment:

```bash
python -m venv .venv
# macOS / Linux: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

1. Edit **`content.md`**. Keep its first heading in the form `# Site name`.
2. Open **Codex** in this repository and invoke **`$build-homepage`**, or open **Claude Code** and invoke **`/build-homepage`**.
3. The skill inspects your Markdown, writes `page-plan.json`, chooses component variants, builds your static site, and validates output.
4. Preview it locally:

```bash
python -m homepage.cli serve
# Open http://127.0.0.1:8000/
```

You can always build without an AI agent:

```bash
python -m homepage.cli plan
python -m homepage.cli build --require-plan
python -m homepage.cli validate
python -m pytest -q
```

`python -m homepage.cli build` also works *without* a plan. In that case, it uses safe heuristics derived from headings and rules. This makes CI repeatable even when Codex or Claude Code is unavailable.

## What will the skill do?

```text
content.md ───┐
style.yaml ───┼──> Codex / Claude Code skill ───> page-plan.json
view-rules.yaml┘                                      │
                                                      ▼
                                      Deterministic Python renderer
                                                      │
                                                      ▼
                                       dist/index.html + style.css
                                                      │
                                                      ▼
                                           GitHub Pages deploy
```

**The model does not author unchecked HTML.** It chooses from validated page components and variants by referencing existing Markdown section IDs. The renderer reuses the Markdown as the only factual content source.

The workflow has two independent automation layers:

- **Local agent skill (AI):** Generates/updates the page plan and validates the site. Invoke manually after editing Markdown.
- **GitHub Action (no AI):** Rebuilds and deploys on pushes to `main` or when you choose *Run workflow* in GitHub Actions. A missing or stale plan falls back to safe automatic section selection, so your latest content is not silently dropped.

## Publish to `github.io`

1. Create a GitHub repository, ideally named **`YOUR_USERNAME.github.io`** for the root site, or any other name for a project site.
2. Unzip and commit **all files including hidden `.agents/`, `.claude/`, and `.github/` folders**. Push to the `main` branch. Do not commit `.venv`.
3. In GitHub → **Settings → Pages**, select **GitHub Actions** as the publishing source.
4. In **Actions**, select **Build and Deploy Homepage** → **Run workflow** if it did not automatically deploy after setup.
5. Visit `https://YOUR_USERNAME.github.io/` (user site) or `https://YOUR_USERNAME.github.io/REPOSITORY_NAME/` (project site).

All page resources use relative URLs, so the same build works for both address types. Deployment permissions in `.github/workflows/pages.yml` follow the standard GitHub Pages workflow. **No OpenAI or Anthropic API key is needed in GitHub Actions.**

## Editing your content

Use normal Markdown:

```markdown
# My Brand

A short bold statement for the hero.

An introduction describing what we actually do.

[Explore our work](#selected-work)

## What we build

- **Service A** — A short explanation.
- **Service B** — Another explanation.

## Selected work

### Project One

A factual project description.

## Contact

[Email our team](mailto:hello@example.com)
```

The example email above is illustrative; replace it with a real address before publishing. Image links must point to real local files under `assets/`, for example `![Alt text](assets/workshop.webp)`; the build refuses missing or remote images. Link destinations must be valid.

## Customization

- **`style.yaml`:** Brand colors and safe font stacks, site language, page width, design intent and layout tokens. The renderer currently applies palette, font stacks and max width from this file; the remaining entries guide the agent.
- **`view-rules.yaml`:** Declarative content-to-layout design contract for the agent. For non-agent builds, add explicit `section_overrides` with source IDs returned by `python -m homepage.cli inspect`.
- **`page-plan.json`:** Model-authored choices, validated against the current `content.md` and `view-rules.yaml` SHA-256 fingerprints. Editing Markdown makes this plan stale; calling the skill refreshes it. Never put HTML or invented copy here.
- **`homepage/render.py`:** The deterministic HTML templates and responsive CSS.

Allowed view components are `hero_masthead`, `editorial_intro`, `feature_grid`, `project_showcase`, `prose`, `image_feature`, `pull_quote`, `responsive_table`, `code_block`, `call_to_action`, `faq`, and `footer`.

More detail: [Architecture and safety](docs/ARCHITECTURE.md) and [Agent invocation](docs/AGENT-SKILLS.md).

## Production-readiness scope

Included: source-preserving rendering, responsive CSS, semantic HTML, keyboard focus styles, a skip link, safe Markdown parsing with raw HTML disabled, blocked remote/unsafe assets, link/anchor checking, a restrictive CSP, local preview, tests, source-addressed layouts, and GitHub Pages CI/CD.

You should still visually review your published site and confirm its content, licensing, image rights and links. Accessibility compliance and search engine ranking are **not** guaranteed by a static validator. No generated page has been deployed to your account automatically.

## Requirements and support

Python 3.11+ and the libraries in `requirements.txt`. A Codex or Claude Code environment is needed **only** for AI-guided layout selection. GitHub Pages hosting requires a GitHub account/repository.

## License

MIT (see `LICENSE`).
