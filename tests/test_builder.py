"""Regression tests for the Markdown -> plan -> safe static site pipeline."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from homepage.cli import main
from homepage.core import BuildError, automatic_plan, load_yaml, read_source, validate_plan
from homepage.render import css_for

PROJECT = Path(__file__).resolve().parents[1]


def create_project(tmp_path: Path, markdown: str | None = None) -> Path:
    for filename in ('content.md', 'style.yaml', 'view-rules.yaml'):
        shutil.copyfile(PROJECT / filename, tmp_path / filename)
    (tmp_path / 'assets').mkdir(exist_ok=True)
    shutil.copytree(PROJECT / 'assets', tmp_path / 'assets', dirs_exist_ok=True)
    if markdown is not None:
        (tmp_path / 'content.md').write_text(markdown, encoding='utf-8')
    return tmp_path


def run_cmd(root: Path, *args: str) -> int:
    return main(['--root', str(root), *args])


def read_html(root: Path) -> BeautifulSoup:
    return BeautifulSoup((root / 'dist/index.html').read_text(encoding='utf-8'), 'html.parser')


def test_sample_homepage_with_plan(tmp_path):
    # Test a stable fixture, not whatever content.md the site author chooses.
    root = create_project(tmp_path, """# A Billion Intelligence

Practical intelligence for the physical world.

## What we build

- **Computer Vision** — Visual recognition systems.
- **Robotics** — Perception for machines.
- **AI Systems** — Practical software.

## Selected work

### Warehouse Inspection

Vision models for crack detection.

### Robotic Perception

Camera-based detection and depth processing.

### 3D Visualization

Interactive tools for point-cloud data.

## Our approach

Working software over unnecessary complexity.

## Contact

[Explore selected work](#selected-work)
""")
    assert run_cmd(root, 'inspect') == 0
    assert run_cmd(root, 'plan') == 0
    assert run_cmd(root, 'build', '--require-plan') == 0
    assert run_cmd(root, 'validate') == 0
    page = read_html(root)
    assert page.title.text == 'A Billion Intelligence'
    assert len(page.find_all('h1')) == 1
    assert len(page.select('main > section')) == 5
    assert page.select_one('section#what-we-build .cards')
    assert len(page.select('section#what-we-build .card')) == 3
    assert len(page.select('section#selected-work .work-item')) == 3
    assert 'Warehouse Inspection' in page.get_text()
    assert page.select_one('a[href="#selected-work"]')
    assert (root / 'dist/style.css').is_file()
    assert (root / 'dist/.nojekyll').is_file()


def test_html_and_javascript_links_are_not_executable(tmp_path):
    root = create_project(tmp_path, '''# My Website

A simple introduction for visitors.

## Features

<img src=x onerror=alert(1)>

<script>alert(1)</script>

[bad](javascript:alert(1))

```html
<script>hello</script>
```
''')
    assert run_cmd(root, 'build') == 0
    page = read_html(root)
    assert not page.find('script')
    assert not page.find('img')
    assert not page.select_one('a[href^="javascript:"]')
    assert 'onerror=alert(1)' in page.get_text()
    assert '&lt;script&gt;' in (root / 'dist/index.html').read_text()


def test_remote_image_is_rejected(tmp_path):
    root = create_project(tmp_path, '# My Site\n\nIntro text.\n\n## Gallery\n\n![Photo](https://example.com/x.png)\n')
    assert run_cmd(root, 'build') == 2
    assert not (root / 'dist/index.html').exists()


def test_missing_local_image_is_rejected(tmp_path):
    root = create_project(tmp_path, '# My Site\n\nIntro text.\n\n## Gallery\n\n![Photo](assets/not-present.png)\n')
    assert run_cmd(root, 'build') == 2


def test_safe_local_image_is_copied(tmp_path):
    root = create_project(tmp_path, '# My Site\n\nIntro text.\n\n## Gallery\n\n![A safe sample](assets/example.png)\n')
    (root / 'assets/example.png').write_bytes(b'\x89PNG\r\n\x1a\nFAKE TEST DATA')
    assert run_cmd(root, 'build') == 0
    assert (root / 'dist/assets/example.png').read_bytes() == (root / 'assets/example.png').read_bytes()
    assert read_html(root).find('img')['alt'] == 'A safe sample'


def test_content_edit_rejects_stale_plan_in_strict_mode(tmp_path):
    root = create_project(tmp_path)
    original_sections = len(read_source(root / 'content.md').sections)
    assert run_cmd(root, 'plan') == 0
    with (root / 'content.md').open('a', encoding='utf-8') as file:
        file.write('\n## New Chapter\n\nNew information preserved.\n')
    assert run_cmd(root, 'build', '--require-plan') == 2
    assert run_cmd(root, 'build') == 0  # CI never deploys an old design for new content.
    assert 'New information preserved.' in read_html(root).get_text()
    assert len(read_html(root).select('main > section')) == original_sections + 1


def test_plan_section_omission_is_invalid(tmp_path):
    root = create_project(tmp_path)
    assert run_cmd(root, 'plan') == 0
    path = root / 'page-plan.json'
    plan = json.loads(path.read_text(encoding='utf-8'))
    plan['sections'].pop()
    path.write_text(json.dumps(plan), encoding='utf-8')
    assert run_cmd(root, 'build', '--require-plan') == 2
    assert run_cmd(root, 'build') == 0


def test_unknown_component_is_rejected(tmp_path):
    root = create_project(tmp_path)
    source = read_source(root / 'content.md')
    plan = automatic_plan(source)
    plan['sections'][1]['component'] = 'raw_generated_html'
    with pytest.raises(BuildError, match='Unknown component'):
        validate_plan(plan, source, 'bold-editorial')


def test_same_heading_twice_has_stable_anchors(tmp_path):
    root = create_project(tmp_path, '# Example\n\nA simple headline.\n\n## Results\n\nFirst.\n\n## Results\n\nSecond.\n')
    assert run_cmd(root, 'build') == 0
    html_doc = read_html(root)
    assert html_doc.select_one('section#results')
    assert html_doc.select_one('section#results--2')
    assert 'Second.' in html_doc.get_text()


def test_broken_internal_anchor_fails(tmp_path):
    root = create_project(tmp_path, '# Example\n\nA simple headline.\n\n## More\n\n[Broken](#unknown-section)\n')
    assert run_cmd(root, 'build') == 2


def test_safe_css_tokens_reject_injection():
    style = load_yaml(PROJECT / 'style.yaml')
    style['colors']['canvas'] = '#FFF000; background:url(https://example.com/x)'
    with pytest.raises(BuildError, match='six-digit hex'):
        css_for(style)


def test_rules_explicit_override_is_applied(tmp_path):
    root = create_project(tmp_path, '# Example\n\nIntro.\n\n## Our approach\n\nText.\n')
    rules = load_yaml(root / 'view-rules.yaml')
    rules['section_overrides'] = {'our-approach:1': {'component': 'prose', 'variant': 'regular'}}
    import yaml
    (root / 'view-rules.yaml').write_text(yaml.safe_dump(rules, sort_keys=False), encoding='utf-8')
    assert run_cmd(root, 'plan') == 0
    plan = json.loads((root / 'page-plan.json').read_text())
    assert plan['sections'][1]['component'] == 'prose'
    assert run_cmd(root, 'build', '--require-plan') == 0


def test_generated_output_contains_all_source_paragraphs(tmp_path):
    root = create_project(tmp_path, '''# Title

A striking little introduction.

## What we build

- **Item One** — important detail never omitted
- **Item Two** — another important detail

## Selected work

### Project Alpha

This project has a carefully preserved explanation.

### Project Beta

This other project has a second explanation.

## Closing

Every last paragraph must stay.
''')
    assert run_cmd(root, 'build') == 0
    text = read_html(root).get_text(' ', strip=True)
    for phrase in ('A striking little introduction.', 'important detail never omitted', 'another important detail',
                   'This project has a carefully preserved explanation.',
                   'This other project has a second explanation.', 'Every last paragraph must stay.'):
        assert phrase in text


def test_rule_edit_invalidates_plan_and_reapplies_override(tmp_path):
    root = create_project(tmp_path)
    assert run_cmd(root, 'plan') == 0
    path = root / 'view-rules.yaml'
    path.write_text(path.read_text(encoding='utf-8') + '\n# User edited the view rules\n', encoding='utf-8')
    assert run_cmd(root, 'build', '--require-plan') == 2
    assert run_cmd(root, 'build') == 0


def test_missing_image_alt_is_rejected(tmp_path):
    root = create_project(tmp_path, '# My Site\n\nIntro text.\n\n## Gallery\n\n![](assets/example.png)\n')
    (root / 'assets/example.png').write_bytes(b'\x89PNG\r\n\x1a\n')
    assert run_cmd(root, 'build') == 2


def test_current_content_end_to_end(tmp_path):
    # Regression against accidental omission of meaningful source claims.
    root = create_project(tmp_path)
    assert run_cmd(root, 'plan') == 0
    assert run_cmd(root, 'build', '--require-plan') == 0
    page = read_html(root)
    assert page.title.get_text(strip=True) == read_source(root / 'content.md').title
    text = page.get_text(' ', strip=True)
    for phrase in ('1.58-bit', 'AP@0.5 = 0.3540', '3,226', 'R18', 'R50'):
        assert phrase in text


def test_training_example_image_is_preserved(tmp_path):
    root = create_project(tmp_path)
    assert run_cmd(root, 'plan') == 0
    assert run_cmd(root, 'build', '--require-plan') == 0
    image = read_html(root).select_one('#training-example img')
    assert image is not None
    assert image.get('src') == 'assets/ChatGPTImage16_02_44-prediction.jpg'
    assert 'training prediction' in image.get('alt', '').lower()
    src = root / image['src']
    dest = root / 'dist' / image['src']
    assert src.is_file() and dest.is_file()
    assert src.read_bytes() == dest.read_bytes()
    assert run_cmd(root, 'validate') == 0


def test_removing_prediction_image_fails_instead_of_publishing_broken_url(tmp_path):
    root = create_project(tmp_path)
    (root / 'assets/ChatGPTImage16_02_44-prediction.jpg').unlink()
    assert run_cmd(root, 'build') == 2
    assert not (root / 'dist/index.html').exists()
