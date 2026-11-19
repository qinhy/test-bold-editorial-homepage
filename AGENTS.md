# Repository agent instructions

This repository is a Markdown-to-static-homepage compiler. The canonical source is `content.md`; the visual identity is `style.yaml`; the design contract is `view-rules.yaml`.

- To rebuild: invoke the local `$build-homepage` skill, or run `python -m homepage.cli plan && python -m homepage.cli build --require-plan && python -m homepage.cli validate`.
- Use `requirements-dev.txt` for development; use `requirements.txt` in CI.
- Preserve every content section, source order, original facts, local links, and image alt text. Generated text must not replace the user's source.
- A page plan is only layout decisions tied to `source_sha256`; it cannot contain arbitrary HTML or invented copy.
- Do not make network requests, add script tags, or push changes without user authorization.
- When changing behavior, run `python -m pytest -q` and rebuild `dist/`.
- Generated output: `dist/index.html`, `dist/style.css`, `dist/.nojekyll`, referenced safe assets, and `dist/assets/fonts/` (fonts + licences).
