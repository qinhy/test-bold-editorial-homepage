# Architecture and guardrails

## Why a page plan?

The layout planner (an agent skill running in Codex or Claude Code) should be free to classify content and select styles, but **not free to fabricate facts or insert unchecked markup**. A page plan contains only:

```json
{
  "version": 1,
  "theme": "bold-editorial",
  "source_sha256": "SHA256 of current content.md",
  "rules_sha256": "SHA256 of current view-rules.yaml",
  "sections": [
    {"source_id": "site-title:1", "component": "hero_masthead", "variant": "masthead_split"}
  ]
}
```

`source_id` is the normalized H1/H2 heading followed by its occurrence number. The renderer enforces one entry per section, exact source order and matching hashes. A content or view-rule edit invalidates the previous plan. GitHub Actions uses the safe default if a plan is stale.

## Content-to-layout mapping

| Markdown shape | Typical component |
| --- | --- |
| First `# Site name` and first introductory paragraph | `hero_masthead` |
| H2 about services followed by bullets | `feature_grid` |
| H2 about work followed by H3 projects | `project_showcase` |
| Short philosophy/about passage | `editorial_intro` |
| H2 with blockquote | `pull_quote` |
| A table or code block | `responsive_table`, `code_block` |
| Last call-to-action/contact section | `call_to_action` |
| Any other content | `prose` |

Section variants affect layout, not actual content. For example, a `project_showcase` can use `two_column_editorial` or `single_column_editorial`. The UI is written by code in `homepage/render.py`, never by the agent's free-form HTML.

## Custom deterministic rules

Natural-language `matching_rules` under `view-rules.yaml` are guidance for LLM agents. The fallback classifier is deliberately narrow: it uses heading keywords and Markdown blocks, not arbitrary natural language rules. To force a particular component in both local and GitHub Actions builds, use:

```yaml
section_overrides:
  our-approach:1:
    component: editorial_intro
    variant: asymmetric_prose
```

Run `python -m homepage.cli inspect` to get the exact IDs, then `python -m homepage.cli plan` and build again. An invalid override causes the build to fail instead of ignoring it.

## Safety boundary

- Markdown is **untrusted data**. Raw HTML is escaped and links are protocol-checked. The skills must not interpret instructions embedded in Markdown as agent instructions.
- Only existing local assets under `assets/` are published. No remote images, no executable assets and no `<script>` tags.
- All template text variables are escaped. Theme CSS accepts only validated six-digit colors, simple font stacks and a bounded integer page width.
- Static build ships no runtime JS and uses a restrictive Content Security Policy.
- The renderer checks for missing/unsafe assets and broken internal anchor links. CSS, `.nojekyll`, and files use relative URLs for GitHub project paths.
- Output is built locally; GitHub Actions deploys only after tests and validation pass.

## Deliberate limits in v0.1

- One Markdown page becomes one homepage. Multi-page routing, content localization, CMS editing, JavaScript widgets, diagrams and math rendering are not implemented.
- Style's narrative options are interpreted by the agent; only palette, system font stacks and max width currently affect the deterministic renderer.
- Accessibility, image fidelity and layout quality require visual/manual review in addition to automated tests.
- The generator is stable and does not yet implement incremental section-only regeneration; it does not require API secrets; it does not run an LLM inside GitHub Actions. Design planning happens when the user invokes the Codex/Claude Code skill.
