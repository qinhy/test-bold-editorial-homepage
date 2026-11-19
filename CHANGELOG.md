# Changelog

## 0.2.0

### Fixed
- `page-plan.json` no longer goes stale on Windows checkouts: content and rule fingerprints ignore CRLF vs LF, and `.gitattributes` pins LF.
- Feature-grid cards on the second row no longer pick up a stray left border and offset.
- Mobile pages no longer overflow sideways when a section holds a wide table (grid tracks use `minmax(0, 1fr)`).
- Hyphenated words in the display headline (e.g. "1.58-bit") no longer break across lines.
- The README no longer describes the training-example image as a placeholder.

### Changed
- New layout: a sticky left rail (section number and heading) beside an 8-column content area; feature lists, project collections and full-width figures span the page.
- Self-hosted Newsreader, IBM Plex Sans and IBM Plex Mono (SIL OFL), with system font fallbacks.
- Hero art is now a deterministic content fingerprint instead of generic shapes; the theme name is no longer printed on the page.
- Link-only paragraphs render as an action row (button plus text links); `**Label:** value` lists render as label/value tables; code blocks show their language; images get intrinsic sizes and lazy loading; tables get a scroll-edge shadow on narrow screens.
- The automatic planner recognises closing sections named "Explore…", "Try…", "Download…", "Join…" and "Sign up" as calls to action.
- Footer shows a "Back to top" link instead of generator branding. Print styles added.

### Added
- `fonts.local_faces` in `style.yaml`, validated and copied to `dist/assets/fonts/` with licences.
- `validate` now fails if the page or stylesheet references a file that was not published.
- The build rejects inline `style` attributes.
- 13 new tests (31 total).
