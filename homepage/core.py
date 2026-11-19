"""Parse Markdown source, plan section views, and strictly validate page plans."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from markdown_it import MarkdownIt

COMPONENTS = {
    'hero_masthead', 'editorial_intro', 'feature_grid', 'project_showcase',
    'prose', 'image_feature', 'pull_quote', 'responsive_table', 'code_block',
    'call_to_action', 'faq', 'footer',
}
VARIANTS = {
    'hero_masthead': {'masthead_split', 'masthead_full', 'type_only'},
    'feature_grid': {'numbered_three_up', 'numbered_grid'},
    'project_showcase': {'two_column_editorial', 'single_column_editorial'},
    'editorial_intro': {'asymmetric_prose', 'regular'},
    'call_to_action': {'dark_band', 'light_band'},
    'prose': {'regular', 'asymmetric_prose'},
    'image_feature': {'split', 'regular'},
    'pull_quote': {'regular'},
    'responsive_table': {'regular'},
    'code_block': {'regular'},
    'faq': {'regular'},
    'footer': {'regular'},
}
SECTION_HEADER_RE = re.compile(r'^\s*#{1,6}\s+')


class BuildError(Exception):
    """A user-correctable build or validation problem."""


def markdown_engine() -> MarkdownIt:
    # Raw HTML is never executed; markdown-it also checks dangerous link schemes.
    return MarkdownIt('commonmark', {'html': False, 'linkify': False, 'typographer': False}).enable(['table', 'strikethrough'])


def slugify(value: str) -> str:
    text = re.sub(r'[^\w\- ]+', '', value.casefold(), flags=re.UNICODE)
    return re.sub(r'[\s_]+', '-', text).strip('-') or 'section'


def tokens_plain_text(tokens: list) -> str:
    parts = []
    for token in tokens:
        if token.type == 'inline':
            parts.append(token.content)
    return '\n'.join(parts).strip()


@dataclass
class Section:
    source_id: str
    heading: str
    level: int
    tokens: list = field(default_factory=list)

    def body_tokens(self) -> list:
        return self.tokens[3:] if len(self.tokens) >= 3 else []


@dataclass
class Source:
    text: str
    digest: str
    title: str
    sections: list[Section]


def read_source(path: Path) -> Source:
    if not path.is_file():
        raise BuildError(f'Missing Markdown input: {path}')
    text = path.read_text(encoding='utf-8')
    if not text.strip():
        raise BuildError('content.md is empty')
    tokens = markdown_engine().parse(text)
    sections: list[Section] = []
    current: Section | None = None
    counts: dict[str, int] = {}
    title: str | None = None
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.type == 'heading_open' and token.tag in {'h1', 'h2'}:
            if i + 2 >= len(tokens):
                raise BuildError('Malformed Markdown heading')
            heading = tokens[i+1].content.strip()
            level = int(token.tag[1:])
            if level == 1:
                if title is not None:
                    raise BuildError('Use one level-1 heading (#) for the site title')
                if sections:
                    raise BuildError('Place the page H1 before all H2 sections')
                title = heading
            if not heading:
                raise BuildError('Headings must not be empty')
            slug = slugify(heading)
            counts[slug] = counts.get(slug, 0) + 1
            current = Section(f'{slug}:{counts[slug]}', heading, level, list(tokens[i:i+3]))
            sections.append(current)
            i += 3
            continue
        if current is None:
            # Keep content before the first heading by inserting a leading section.
            if not sections:
                current = Section('preamble:1', '', 0, [])
                sections.append(current)
        assert current is not None
        current.tokens.append(token)
        i += 1
    if not title:
        raise BuildError('content.md needs one top-level title (# Your Site)')
    if not sections:
        raise BuildError('No Markdown content found')
    if sections[0].level == 0:
        # Keep preamble before main title, but prevent a hero misidentified as the first section.
        raise BuildError('Start content.md with a level-1 heading (# Your Site)')
    return Source(text, hashlib.sha256(text.encode('utf-8')).hexdigest(), title, sections)


def text_digest(path: Path) -> str:
    """SHA-256 of a text file with line endings normalized to LF.

    Windows checkouts (``core.autocrlf``) rewrite LF as CRLF; hashing raw bytes
    would make an unchanged view-rules.yaml look edited and invalidate the plan.
    """
    data = path.read_bytes().replace(b'\r\n', b'\n')
    return hashlib.sha256(data).hexdigest()


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise BuildError(f'Missing config: {path}')
    try:
        value = yaml.safe_load(path.read_text(encoding='utf-8'))
    except yaml.YAMLError as exc:
        raise BuildError(f'YAML error in {path.name}: {exc}') from exc
    if not isinstance(value, dict) or value.get('version') != 1:
        raise BuildError(f'{path.name} must be a version: 1 YAML mapping')
    return value


def inferred_component(section: Section, *, first: bool, last: bool) -> str:
    if first:
        return 'hero_masthead'
    heading = section.heading.casefold()
    bodytypes = {t.type for t in section.body_tokens()}
    if any(w in heading for w in ('faq', 'questions', 'よくある質問', '常见问题')):
        return 'faq'
    if any(w in heading for w in ('service', 'feature', 'what we build', 'capabilit', 'offer', 'solution', 'サービス', '事業', 'サービス内容', '機能')) and 'bullet_list_open' in bodytypes:
        return 'feature_grid'
    if any(w in heading for w in ('work', 'project', 'portfolio', 'case stud', '事例', '実績', 'プロジェクト', '作品')) and ('heading_open' in bodytypes or 'bullet_list_open' in bodytypes):
        return 'project_showcase'
    if last and any(w in heading for w in ('contact', 'get in touch', 'build something', 'start', 'reach us', 'explore', 'try ', 'download', 'join', 'sign up', '問い合わせ', '連絡', 'お問い合わせ')):
        return 'call_to_action'
    if 'image' in bodytypes or any(t.type == 'inline' and any(c.type == 'image' for c in (t.children or [])) for t in section.body_tokens()):
        return 'image_feature'
    if any(t.type == 'blockquote_open' for t in section.body_tokens()):
        return 'pull_quote'
    if any(t.type == 'table_open' for t in section.body_tokens()):
        return 'responsive_table'
    if any(t.type == 'fence' for t in section.body_tokens()):
        return 'code_block'
    if len(section.body_tokens()) <= 6:
        return 'editorial_intro'
    return 'prose'


def automatic_plan(source: Source, theme: str = 'bold-editorial', rules: dict[str, Any] | None = None, rules_sha256: str | None = None) -> dict[str, Any]:
    planned = []
    overrides = (rules or {}).get('section_overrides', {})
    if not isinstance(overrides, dict):
        raise BuildError('view-rules.yaml section_overrides must be a mapping')
    known = {s.source_id for s in source.sections}
    for section_id in overrides:
        if section_id not in known:
            raise BuildError(f'Unknown section_overrides source ID: {section_id}')
    for i, section in enumerate(source.sections):
        component = inferred_component(section, first=i == 0, last=i == len(source.sections)-1)
        variant = {
            'hero_masthead': 'masthead_split', 'feature_grid': 'numbered_three_up',
            'project_showcase': 'two_column_editorial', 'editorial_intro': 'asymmetric_prose',
            'call_to_action': 'dark_band',
        }.get(component, 'regular')
        if section.source_id in overrides:
            override = overrides[section.source_id]
            if not isinstance(override, dict) or set(override) - {'component','variant'}:
                raise BuildError(f'Invalid section_overrides for {section.source_id}')
            component = override.get('component', component)
            default_variants = {'hero_masthead': 'masthead_split', 'feature_grid': 'numbered_three_up',
                                'project_showcase': 'two_column_editorial', 'editorial_intro': 'asymmetric_prose',
                                'call_to_action': 'dark_band', 'image_feature': 'split'}
            variant = override.get('variant', variant if component == inferred_component(section, first=i==0, last=i==len(source.sections)-1) else default_variants.get(component, 'regular'))
        planned.append({'source_id': section.source_id, 'component': component, 'variant': variant})
    return {
        'version': 1,
        'theme': theme,
        'source_sha256': source.digest,
        'rules_sha256': rules_sha256,
        'sections': planned,
    }


def validate_plan(plan: dict[str, Any], source: Source, expected_theme: str, expected_rules_sha256: str | None = None) -> None:
    if not isinstance(plan, dict) or plan.get('version') != 1:
        raise BuildError('page-plan.json must be an object with version: 1')
    if plan.get('source_sha256') != source.digest:
        raise BuildError('page-plan.json is stale; rerun `python -m homepage.cli plan`')
    if expected_rules_sha256 is not None and plan.get('rules_sha256') != expected_rules_sha256:
        raise BuildError('page-plan.json is stale after view-rules.yaml changed; rerun `python -m homepage.cli plan`')
    if plan.get('theme') != expected_theme:
        raise BuildError(f'page-plan.json theme must be {expected_theme!r}')
    sections = plan.get('sections')
    if not isinstance(sections, list) or len(sections) != len(source.sections):
        raise BuildError('Plan must include exactly one entry for each Markdown section')
    wanted = [section.source_id for section in source.sections]
    received = []
    for i, entry in enumerate(sections):
        if not isinstance(entry, dict):
            raise BuildError(f'Plan section {i} must be a JSON object')
        if set(entry) != {'source_id', 'component', 'variant'}:
            raise BuildError(f'Plan section {i} must contain only source_id, component, variant')
        sid = entry['source_id']
        component = entry['component']
        variant = entry['variant']
        if component not in COMPONENTS:
            raise BuildError(f'Unknown component for {sid}: {component}')
        if variant not in VARIANTS[component]:
            raise BuildError(f'Unsupported variant {variant!r} for {component!r}')
        if i == 0 and component != 'hero_masthead':
            raise BuildError('The first section must be hero_masthead')
        if i > 0 and component == 'hero_masthead':
            raise BuildError('There must be exactly one hero_masthead')
        if component == 'feature_grid' and not any(t.type == 'bullet_list_open' for t in source.sections[i].body_tokens()):
            raise BuildError(f'feature_grid requires a Markdown bullet list: {sid}')
        received.append(sid)
    if received != wanted:
        raise BuildError('Plan must preserve the order and identity of every Markdown section')


def write_plan(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def read_plan(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (json.JSONDecodeError, OSError) as exc:
        raise BuildError(f'Cannot read page plan {path}: {exc}') from exc
    return data
