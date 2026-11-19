"""Deterministic, source-preserving HTML/CSS generator; no network dependencies."""
from __future__ import annotations

import html
import re
import shutil
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup, Tag

from .core import BuildError, Source, markdown_engine, slugify

ALLOWED_IMAGE_EXT = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.avif'}
COLOR_RE = re.compile(r'^#[0-9A-Fa-f]{6}$')
LANG_RE = re.compile(r'^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$')
SAFE_FONT_RE = re.compile(r"^[\w\s\-',\".]+$")
CSS_TEMPLATE = r'''/* Bold Editorial: all CSS generated locally, zero external fonts or scripts. */
:root {
  --paper: __CANVAS__; --surface: __SURFACE__; --ink: __INK__; --muted: __MUTED__;
  --line: __BORDER__; --red: __ACCENT__; --inverse: __INVERTED__; --inverse-text: __INVERTED_TEXT__;
  --focus: __FOCUS__; --serif: __DISPLAY_FONT__; --sans: __BODY_FONT__; --mono: __MONO_FONT__;
  --max-width: __MAX_WIDTH__px;
}
*,*::before,*::after{box-sizing:border-box}
html{scroll-behavior:smooth} body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);-webkit-font-smoothing:antialiased}
img{max-width:100%;height:auto;display:block} a{color:inherit;text-decoration-thickness:1px;text-underline-offset:4px}
a:focus-visible,button:focus-visible{outline:3px solid var(--focus);outline-offset:4px}
.skip{position:absolute;left:12px;top:-80px;padding:14px 18px;background:var(--inverse);color:var(--inverse-text);z-index:999}.skip:focus{top:12px}
.wrap{width:min(calc(100% - clamp(2.2rem,8vw,7.5rem)),var(--max-width));margin-inline:auto}
.micro{font-size:.73rem;text-transform:uppercase;letter-spacing:.135em;font-weight:750}
.rule{border-top:1px solid var(--line)}
.nav{min-height:86px;display:flex;justify-content:space-between;align-items:center;gap:24px;border-bottom:1px solid var(--line)}
.brand{display:flex;align-items:center;gap:13px;font-weight:800;font-size:.96rem;letter-spacing:-.035em;text-decoration:none}
.brandmark{height:37px;width:37px;background:var(--ink);color:var(--surface);display:grid;place-items:center;font-family:var(--serif);font-size:1.45rem}
.navlinks{display:flex;gap:25px;flex-wrap:wrap;align-items:center;font-size:.81rem;font-weight:650}.navlinks a{text-decoration:none}.navlinks a:hover{text-decoration:underline;text-underline-offset:5px}
.hero{padding:clamp(65px,10vw,140px) 0 clamp(78px,10vw,125px)}.hero-top{display:flex;justify-content:space-between;gap:24px;align-items:center;border-bottom:1px solid var(--line);padding-bottom:26px}
.hero-kicker{display:flex;align-items:center;gap:13px}.hero-kicker:before{content:'';width:40px;height:1px;background:var(--red)}
.hero-grid{display:grid;grid-template-columns:1.24fr .76fr;gap:clamp(30px,5vw,70px);align-items:center;padding-top:38px}
h1,h2,h3,h4,p{margin-top:0}h1,h2,h3{overflow-wrap:anywhere}
h1{font:500 clamp(3.3rem,7vw,7.65rem)/.99 var(--serif);letter-spacing:-.068em;margin:0 0 38px}
.hero-copy{font-size:clamp(1.08rem,1.55vw,1.35rem);line-height:1.63;max-width:58ch}.hero-copy p{margin:0 0 17px}
.hero-copy a{display:inline-block;font-size:.88rem;font-weight:730;margin-top:12px;text-underline-offset:8px}
.art{min-height:380px;aspect-ratio:4/4.1;position:relative;overflow:hidden;background:#D7D3C6;isolation:isolate}
.art:before{content:'';position:absolute;width:83%;height:83%;border:1px solid var(--ink);transform:rotate(-23deg);top:6%;left:12%}
.art:after{content:'';position:absolute;width:90%;height:90%;border:clamp(22px,3vw,40px) solid var(--ink);border-radius:50%;top:23%;left:33%}
.art-circle{position:absolute;width:53%;aspect-ratio:1;border-radius:50%;background:var(--red);top:4%;left:-12%;z-index:2}
.art-lines{position:absolute;inset:0;background:repeating-linear-gradient(45deg,transparent 0,transparent 15px,rgba(29,33,30,.17) 16px,transparent 17px);opacity:.34}
.art-note{position:absolute;bottom:22px;left:22px;background:var(--paper);padding:12px 14px;z-index:3;font-size:.68rem;letter-spacing:.1em;text-transform:uppercase;font-weight:800}
.content-section{padding:clamp(85px,12vw,165px) 0}.section-head{display:grid;grid-template-columns:1fr 1.35fr;gap:clamp(30px,5vw,70px);align-items:end;margin-bottom:42px}
.section-head h2{font:500 clamp(3rem,6vw,6rem)/1.02 var(--serif);letter-spacing:-.063em;margin:12px 0 0}
.section-no{color:var(--red)}.section-lead{line-height:1.7;max-width:62ch;justify-self:end}.prose{font-size:1.05rem;line-height:1.82;max-width:75ch;color:var(--ink);overflow-wrap:anywhere}
.prose p,.prose ul,.prose ol,.prose blockquote{margin-top:0;margin-bottom:1.3em}.prose li+li{margin-top:.5em}
.prose a{text-decoration-color:var(--red)}.prose h3{font:500 clamp(1.6rem,2.5vw,2.6rem)/1.16 var(--serif);letter-spacing:-.04em;margin:1.5em 0 .6em}
.prose h4{font-size:1.15rem;margin:1.4em 0 .6em}.prose code{font-family:var(--mono);font-size:.85em;background:rgba(80,70,50,.09);padding:.15em .27em}
.prose pre{max-width:100%;overflow-x:auto;background:var(--ink);color:var(--surface);padding:24px;line-height:1.6;border-radius:0}
.prose pre code{background:none;color:inherit;padding:0;font-size:.86rem;white-space:pre}
.prose blockquote{border-left:3px solid var(--red);padding:8px 0 8px 23px;font:italic 500 clamp(1.4rem,2.3vw,2.15rem)/1.35 var(--serif)}
.prose table{width:100%;border-collapse:collapse;min-width:480px}.prose th,.prose td{padding:13px 17px;border-bottom:1px solid var(--line);text-align:left}.prose th{font-weight:750}
.table-scroll{max-width:100%;overflow-x:auto}.prose img{margin:20px 0}.prose hr{border:0;border-top:1px solid var(--line);margin:30px 0}
.section-feature_grid .prose,.section-project_showcase .prose{max-width:none}
.hero.variant-type_only .hero-grid,.hero.variant-masthead_full .hero-grid{grid-template-columns:1fr}
.hero.variant-type_only .art,.hero.variant-masthead_full .art{display:none}
.section-project_showcase.variant-single_column_editorial .work-grid{grid-template-columns:1fr}
.section-editorial_intro.variant-regular .prose{font:inherit;max-width:75ch}
.cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));border-top:1px solid var(--ink);border-bottom:1px solid var(--ink)}
.card{padding:30px 28px 45px 0;min-width:0}.card+.card{border-left:1px solid var(--line);padding-left:28px}
.card .num{font-size:.76rem;color:var(--red);font-weight:780;letter-spacing:.13em}
.card-copy{margin-top:50px;font-size:.96rem;line-height:1.76;color:var(--muted);overflow-wrap:anywhere}
.card-copy strong{display:block;font:500 clamp(1.65rem,2.5vw,2.3rem)/1.12 var(--serif);letter-spacing:-.045em;color:var(--ink);margin-bottom:14px}
.card-copy p{margin:0}.section-intro{margin-bottom:30px}
.work-band{background:var(--inverse);color:var(--inverse-text)}.work-band .section-head{margin-bottom:35px}.work-band .section-no{color:#E8B7A8}
.work-band .section-head h2{color:var(--inverse-text)}.work-band .prose{color:var(--inverse-text)}
.work-grid{display:grid;grid-template-columns:1fr 1fr;column-gap:40px;border-top:1px solid #686C65}
.work-item{display:grid;grid-template-columns:65px 1fr;gap:22px;padding:34px 0 40px;border-bottom:1px solid #686C65;min-width:0}
.work-item .num{font:500 2rem var(--serif);color:#DBB8AE}.work-item h3{font:500 clamp(1.6rem,2.4vw,2.4rem)/1.15 var(--serif);letter-spacing:-.035em;margin:0 0 13px}
.work-item p{font-size:.94rem;line-height:1.75;color:#D4D8D1}.work-item a{color:#FBE0D8}
.work-item pre{background:#353B35}
.editorial-intro .prose{font:400 clamp(1.38rem,2.45vw,2.25rem)/1.44 var(--serif);letter-spacing:-.025em;max-width:34ch}
.editorial-intro .prose strong{color:var(--red)}
.cta-band{border-top:1px solid var(--ink)}.cta-band .section-head{margin-bottom:15px}.cta-band .prose a{font-weight:750}
.cta-band.dark{background:var(--inverse);color:var(--inverse-text);border-top-color:var(--inverse)}.cta-band.dark .prose{color:var(--inverse-text)}.cta-band.dark .section-no{color:#E8B7A8}
.page-footer{border-top:1px solid var(--line);padding:25px 0 40px;display:flex;justify-content:space-between;gap:20px;flex-wrap:wrap;color:var(--muted);font-size:.78rem}
@media(max-width:960px){.hero-grid,.section-head{grid-template-columns:1fr}.section-lead{justify-self:start}.art{min-height:310px;width:min(100%,560px);aspect-ratio:5/3}.cards{grid-template-columns:repeat(2,minmax(0,1fr))}.card:nth-child(3){border-left:0;padding-left:0;border-top:1px solid var(--line)}}
@media(max-width:640px){.wrap{width:calc(100% - 38px)}.nav{min-height:72px}.brand{font-size:.83rem}.navlinks{gap:12px;font-size:.7rem}.navlinks a:nth-child(n+3){display:none}
.hero{padding:58px 0 76px}.hero-top{padding-bottom:20px}.hero-grid{padding-top:27px}.hero h1{font-size:clamp(3.35rem,13vw,5.25rem);margin-bottom:27px}
.art{min-height:290px;aspect-ratio:1.25}.cards{grid-template-columns:1fr}.card,.card:nth-child(3){border:0;border-bottom:1px solid var(--line);padding:25px 0 35px}.card+.card{border-left:0;padding-left:0}.card:last-child{border:0}.card-copy{margin-top:20px}
.work-grid{grid-template-columns:1fr}.work-item{grid-template-columns:50px 1fr}.section-head h2{font-size:clamp(3rem,11vw,4.6rem)}.content-section{padding:86px 0}.prose{font-size:1rem}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}*,*::before,*::after{transition:none!important;animation:none!important}}
'''


def esc(text: object) -> str:
    return html.escape(str(text), quote=True)


def css_for(style: dict) -> str:
    colors = style.get('colors', {})
    keys = ['canvas','surface','ink','muted','border','accent','inverted','inverted_text','focus']
    if not isinstance(colors, dict) or any(not COLOR_RE.fullmatch(str(colors.get(k, ''))) for k in keys):
        raise BuildError('style.yaml colors must be six-digit hex codes')
    fonts = style.get('fonts', {})
    if not isinstance(fonts, dict):
        raise BuildError('style.yaml fonts must be a mapping')
    for fontkey in ('display', 'body', 'mono'):
        font = fonts.get(fontkey)
        if not isinstance(font, str) or len(font) > 150 or not SAFE_FONT_RE.fullmatch(font):
            raise BuildError(f'Invalid safe font list in style.yaml: {fontkey}')
    width = style.get('layout', {}).get('max_width', 1240)
    if not isinstance(width, int) or not (720 <= width <= 2000):
        raise BuildError('layout.max_width must be an integer between 720 and 2000')
    replacements = {
        '__CANVAS__': colors['canvas'], '__SURFACE__': colors['surface'], '__INK__': colors['ink'],
        '__MUTED__': colors['muted'], '__BORDER__': colors['border'], '__ACCENT__': colors['accent'],
        '__INVERTED__': colors['inverted'], '__INVERTED_TEXT__': colors['inverted_text'],
        '__FOCUS__': colors['focus'], '__DISPLAY_FONT__': fonts['display'],
        '__BODY_FONT__': fonts['body'], '__MONO_FONT__': fonts['mono'], '__MAX_WIDTH__': str(width),
    }
    output = CSS_TEMPLATE
    for k,v in replacements.items():
        output = output.replace(k,v)
    return output


def section_anchor(source_id: str) -> str:
    slug, occur = source_id.rsplit(':', 1)
    return slug if occur == '1' else f'{slug}--{occur}'


def _validate_links_and_assets(soup: BeautifulSoup, root: Path, anchors: set[str]) -> set[Path]:
    assets: set[Path] = set()
    for tag in soup.find_all(['a', 'img']):
        attr = 'href' if tag.name == 'a' else 'src'
        ref = tag.get(attr)
        if not ref:
            if tag.name == 'img':
                raise BuildError('Markdown image has no URL')
            continue
        if any(ord(c) < 32 for c in ref) or '\\' in ref:
            raise BuildError(f'Unsafe URL in Markdown: {ref!r}')
        parts = urlsplit(ref)
        if parts.scheme in {'http', 'https', 'mailto'} and tag.name == 'a':
            if parts.scheme in {'http','https'} and not parts.netloc:
                raise BuildError(f'Invalid external URL: {ref}')
            continue
        if parts.scheme or parts.netloc:
            raise BuildError(f'Unsupported URL scheme or external image: {ref}')
        if tag.name == 'a' and ref.startswith('#'):
            if unquote(ref[1:]) not in anchors:
                raise BuildError(f'Broken heading anchor in content.md: {ref}')
            continue
        decoded_path = unquote(parts.path)
        # Only local files under assets are published. Fragment-only links are handled above.
        path = PurePosixPath(decoded_path)
        if path.is_absolute() or '..' in path.parts or not decoded_path.startswith('assets/'):
            raise BuildError(f'Local reference must be under assets/: {ref}')
        candidate = (root / decoded_path).resolve()
        assets_root = (root / 'assets').resolve()
        if not candidate.is_relative_to(assets_root) or not candidate.is_file() or candidate.is_symlink():
            raise BuildError(f'Asset does not exist or escapes assets/: {ref}')
        if tag.name == 'img' and candidate.suffix.casefold() not in ALLOWED_IMAGE_EXT:
            raise BuildError(f'Unsupported image format for safe publishing: {ref}')
        if tag.name == 'img' and not str(tag.get('alt', '')).strip():
            raise BuildError(f'Every image needs meaningful alt text: {ref}')
        # Disallow HTML/JS via local linked files as well.
        if candidate.suffix.casefold() in {'.html', '.htm', '.js', '.mjs', '.svg', '.css'}:
            raise BuildError(f'Potentially executable file cannot be linked through assets/: {ref}')
        assets.add(candidate)
    return assets


def _soup(markdown_html: str) -> BeautifulSoup:
    return BeautifulSoup(markdown_html, 'html.parser')


def _markdown_html(tokens: list, engine) -> str:
    return engine.renderer.render(tokens, engine.options, {})


def _make_feature_grid(soup: BeautifulSoup) -> None:
    listing = soup.find('ul')
    if not listing:
        return
    entries = listing.find_all('li', recursive=False)
    grid = soup.new_tag('div', attrs={'class':'cards'})
    for i, li in enumerate(entries, start=1):
        card = soup.new_tag('article', attrs={'class': 'card'})
        num = soup.new_tag('span', attrs={'class':'num'})
        num.string = f'{i:02d} /'
        card.append(num)
        copy = soup.new_tag('div', attrs={'class':'card-copy'})
        for child in list(li.contents):
            copy.append(child.extract() if isinstance(child, Tag) else child.extract())
        card.append(copy)
        grid.append(card)
    listing.replace_with(grid)


def _make_project_grid(soup: BeautifulSoup) -> None:
    headings = soup.find_all('h3', recursive=False)
    if not headings:
        _make_feature_grid(soup)
        return
    grid = soup.new_tag('div', attrs={'class':'work-grid'})
    for i, heading in enumerate(headings, start=1):
        item = soup.new_tag('article', attrs={'class':'work-item'})
        num = soup.new_tag('span', attrs={'class':'num'})
        num.string = f'{i:02d}'
        item.append(num)
        content = soup.new_tag('div', attrs={'class':'work-copy'})
        # Capture sibling content until next H3 heading, preserving all Markdown blocks.
        node = heading
        while node is not None and (node is heading or not (isinstance(node, Tag) and node.name == 'h3')):
            next_node = node.next_sibling
            content.append(node.extract())
            node = next_node
        item.append(content)
        grid.append(item)
    # grid follows the introduction, which stayed in the soup.
    soup.append(grid)


def _wrap_tables(soup: BeautifulSoup) -> None:
    for table in soup.find_all('table'):
        wrapper = soup.new_tag('div', attrs={'class':'table-scroll', 'role':'region', 'tabindex':'0', 'aria-label':'Scrollable data table'})
        table.wrap(wrapper)


def _render_hero(section, source: Source, engine, variant: str) -> str:
    soup = _soup(_markdown_html(section.body_tokens(), engine))
    first_para = soup.find('p', recursive=False)
    headline = source.title
    if first_para:
        # Promote a standalone opening sentence to the display headline while retaining the text verbatim.
        candidate = first_para.get_text(' ', strip=True)
        if 15 <= len(candidate) <= 130 and not first_para.find(['a', 'img', 'code', 'strong', 'em']):
            headline = candidate
            first_para.extract()
    headline_html = esc(headline)
    body = str(soup)
    return f'''<section class="hero variant-{esc(variant)}" id="top" aria-labelledby="page-title"><div class="wrap">
      <div class="hero-top"><span class="hero-kicker micro">{esc(source.title)}</span><span class="micro">Bold Editorial</span></div>
      <div class="hero-grid"><div><h1 id="page-title">{headline_html}</h1><div class="hero-copy">{body}</div></div>
      <div class="art" role="img" aria-label="Abstract geometric editorial illustration"><span class="art-lines" aria-hidden="true"></span><span class="art-circle" aria-hidden="true"></span><span class="art-note">Bold Editorial</span></div></div>
      </div></section>'''


def _render_section(section, entry: dict, engine, index: int) -> str:
    component = entry['component']
    soup = _soup(_markdown_html(section.body_tokens(), engine))
    _wrap_tables(soup)
    if component == 'feature_grid':
        _make_feature_grid(soup)
    elif component == 'project_showcase':
        _make_project_grid(soup)
    heading = esc(section.heading)
    anchor = esc(section_anchor(section.source_id))
    classnames = ['content-section', f'section-{component}', f"variant-{entry['variant']}"]
    if component == 'project_showcase':
        classnames.append('work-band')
    elif component == 'editorial_intro':
        classnames.append('editorial-intro')
    elif component == 'call_to_action':
        classnames.append('cta-band')
        if entry['variant'] == 'dark_band':
            classnames.append('dark')
    # Don't invent content: heading and body are always sourced exclusively from Markdown.
    return f'''<section class="{' '.join(classnames)}" id="{anchor}" aria-labelledby="heading-{anchor}">
      <div class="wrap"><div class="section-head"><div><span class="micro section-no">{index:02d} /</span>
      <h2 id="heading-{anchor}">{heading}</h2></div></div><div class="prose">{str(soup)}</div></div>
    </section>'''


def render_page(source: Source, plan: dict, style: dict, root: Path, output: Path) -> None:
    css = css_for(style)
    lang = style.get('site', {}).get('language', 'en')
    if not isinstance(lang, str) or not LANG_RE.fullmatch(lang):
        raise BuildError('style.yaml site.language must be a valid BCP 47-style language tag, e.g. en or ja')
    engine = markdown_engine()
    slug_ids = {section_anchor(s.source_id) for s in source.sections}
    nav_sections = source.sections[1:5]
    nav = ''.join(f'<a href="#{esc(section_anchor(s.source_id))}">{esc(s.heading)}</a>' for s in nav_sections)
    page_chunks = []
    for i, (section, entry) in enumerate(zip(source.sections, plan['sections'])):
        if i == 0:
            page_chunks.append(_render_hero(section, source, engine, entry['variant']))
        else:
            page_chunks.append(_render_section(section, entry, engine, i))

    # Description taken only from user content, not from LLM-generated claims.
    paras = [t.content for t in source.sections[0].body_tokens() if t.type == 'inline' and t.content.strip()]
    description = re.sub(r'\s+', ' ', paras[0] if paras else source.title)
    description = re.sub(r'\[([^]]+)\]\([^)]+\)', r'\1', description)
    description = description[:160]
    html_doc = f'''<!doctype html>
<html lang="{esc(lang)}"><head>
  <meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="{esc(description)}"><meta name="theme-color" content="{esc(style['colors']['canvas'])}">
  <meta property="og:type" content="website"><meta property="og:title" content="{esc(source.title)}">
  <meta property="og:description" content="{esc(description)}">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src 'self'; style-src 'self'; font-src 'self'; base-uri 'none'; form-action 'none'; object-src 'none'; script-src 'none'">
  <title>{esc(source.title)}</title><link rel="stylesheet" href="./style.css">
</head><body>
  <a class="skip" href="#main">Skip to content</a>
  <header class="wrap nav"><a class="brand" href="#top" aria-label="{esc(source.title)}, home"><span class="brandmark" aria-hidden="true">{esc(source.title[0].upper())}</span><span>{esc(source.title)}</span></a>
    <nav class="navlinks" aria-label="Main navigation">{nav}</nav></header>
  <main id="main">{''.join(page_chunks)}</main>
  <footer class="wrap page-footer"><span>{esc(source.title)}</span><span>Built from Markdown · Bold Editorial</span></footer>
</body></html>'''
    parsed = BeautifulSoup(html_doc, 'html.parser')
    copied_assets = _validate_links_and_assets(parsed, root, slug_ids | {'top','main'})
    # Additional structural checks, including accidental unsafe markup in the final document.
    if parsed.find(['script', 'iframe', 'object', 'embed', 'form']):
        raise BuildError('Unsafe active HTML detected')
    if len(parsed.find_all('h1')) != 1:
        raise BuildError('Generated page must contain exactly one H1')
    for tag in parsed.find_all(True):
        for attr in tag.attrs:
            if attr.casefold().startswith('on'):
                raise BuildError('Unsafe inline event handler detected')
    output.mkdir(parents=True, exist_ok=True)
    # To avoid stale asset files, remove and recreate the published assets folder.
    asset_output = output / 'assets'
    if asset_output.exists():
        shutil.rmtree(asset_output)
    for asset in copied_assets:
        rel = asset.relative_to((root / 'assets').resolve())
        destination = asset_output / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(asset, destination)
    (output / 'index.html').write_text(html_doc, encoding='utf-8')
    (output / 'style.css').write_text(css, encoding='utf-8')
    (output / '.nojekyll').write_text('', encoding='utf-8')


def validate_output(path: Path) -> dict:
    page = path / 'index.html'
    stylesheet = path / 'style.css'
    if not page.is_file() or not stylesheet.is_file():
        raise BuildError('Expected dist/index.html and dist/style.css')
    parsed = BeautifulSoup(page.read_text(encoding='utf-8'), 'html.parser')
    if len(parsed.find_all('h1')) != 1 or not parsed.find('main') or not parsed.find('nav'):
        raise BuildError('Generated output missing semantic structure')
    if parsed.find(['script', 'iframe', 'object', 'embed', 'form']):
        raise BuildError('Generated output includes forbidden executable elements')
    anchors = {tag['id'] for tag in parsed.find_all(id=True)}
    for link in parsed.find_all('a', href=True):
        href = link['href']
        if href.startswith('#') and unquote(href[1:]) not in anchors:
            raise BuildError(f'Generated page has broken anchor: {href}')
    for tag in parsed.find_all(True):
        for attr in tag.attrs:
            if attr.lower().startswith('on'):
                raise BuildError('Generated output has an inline event handler')
    return {'title': parsed.title.get_text() if parsed.title else '', 'h1': parsed.h1.get_text(strip=True), 'sections': len(parsed.select('main > section')), 'bytes': page.stat().st_size}
