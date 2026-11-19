"""CLI: inspect, plan, build, validate, serve."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from functools import partial
from pathlib import Path

from .core import BuildError, automatic_plan, load_yaml, read_plan, read_source, validate_plan, write_plan
from .render import render_page, validate_output


def load_project(root: Path):
    source = read_source(root / 'content.md')
    style = load_yaml(root / 'style.yaml')
    rules = load_yaml(root / 'view-rules.yaml')
    if not isinstance(style.get('id'), str) or style.get('id') != rules.get('theme'):
        raise BuildError('style.yaml id and view-rules.yaml theme must match')
    return source, style, rules


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Bold Editorial Markdown → production-ready static homepage')
    parser.add_argument('--root', type=Path, default=Path.cwd(), help='Repository directory (default: current directory)')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('inspect', help='Show source sections, stable IDs, and suggested components')
    plan_parser = sub.add_parser('plan', help='Generate a source-addressed, editable page-plan.json')
    plan_parser.add_argument('--output', default='page-plan.json')
    build_parser = sub.add_parser('build', help='Build the static site; stale plans fall back to safe automatic layouts')
    build_parser.add_argument('--require-plan', action='store_true', help='Fail rather than regenerate if plan missing or stale')
    build_parser.add_argument('--out', default='dist')
    validate_parser = sub.add_parser('validate', help='Check output structure and internal navigation')
    validate_parser.add_argument('--out', default='dist')
    serve_parser = sub.add_parser('serve', help='Run local preview HTTP server')
    serve_parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    try:
        if args.command == 'validate':
            info = validate_output(root / args.out)
            print('VALID:', json.dumps(info, ensure_ascii=False))
            return 0
        if args.command == 'serve':
            validate_output(root / 'dist')
            handler = partial(SimpleHTTPRequestHandler, directory=str(root / 'dist'))
            with ThreadingHTTPServer(('127.0.0.1', args.port), handler) as server:
                print(f'Preview: http://127.0.0.1:{args.port}/ (Ctrl+C to stop)', flush=True)
                try:
                    server.serve_forever()
                except KeyboardInterrupt:
                    pass
            return 0
        source, style, rules = load_project(root)
        theme = style['id']
        rules_digest = hashlib.sha256((root / 'view-rules.yaml').read_bytes()).hexdigest()
        auto = automatic_plan(source, theme, rules, rules_sha256=rules_digest)
        if args.command == 'inspect':
            print(json.dumps({
                'site_title': source.title,
                'source_sha256': source.digest,
                'sections': [
                    {'id': s.source_id, 'heading': s.heading, 'suggested_component': p['component'],
                     'sample': ' '.join(t.content for t in s.body_tokens() if t.type == 'inline')[:220]}
                    for s, p in zip(source.sections, auto['sections'])
                ]}, ensure_ascii=False, indent=2))
            return 0
        if args.command == 'plan':
            target = root / args.output
            validate_plan(auto, source, theme, rules_digest)
            write_plan(target, auto)
            print(f'Created {target} ({len(auto["sections"])} sections). You may now customize its component and variant fields.')
            return 0
        if args.command == 'build':
            plan_file = root / 'page-plan.json'
            if plan_file.is_file():
                try:
                    candidate = read_plan(plan_file)
                    validate_plan(candidate, source, theme, rules_digest)
                    plan = candidate
                    print('Using validated, current page-plan.json')
                except BuildError as exc:
                    if args.require_plan:
                        raise
                    print(f'NOTICE: {exc}; using safe automatic plan instead', file=sys.stderr)
                    plan = auto
            else:
                if args.require_plan:
                    raise BuildError('Missing page-plan.json; run `python -m homepage.cli plan` first')
                print('Using automatic section layout (no page-plan.json supplied)')
                plan = auto
            validate_plan(plan, source, theme, rules_digest)
            output = root / args.out
            render_page(source, plan, style, root, output)
            info = validate_output(output)
            print(f'BUILT {output / "index.html"} ({info["sections"]} sections; {info["bytes"]} HTML bytes)')
            return 0
        raise BuildError(f'Unknown command: {args.command}')
    except BuildError as exc:
        print(f'BUILD FAILED: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
