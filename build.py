#!/usr/bin/env python3
"""Generate a portable research homepage using only Python's standard library."""
import argparse
import functools
import html
import http.server
import json
import shutil
from pathlib import Path
from string import Template
from urllib.parse import quote, urlsplit

ROOT = Path(__file__).resolve().parent


def esc(value):
    return html.escape(str(value), quote=True)


def build():
    data = json.loads((ROOT / 'content.json').read_text(encoding='utf-8'))
    pdf_root = ROOT / 'assets' / 'papers'
    rows = {'working_papers': [], 'work_in_progress': []}
    linked_pdfs = []
    for number, paper in enumerate(data['papers'], 1):
        pdf = paper.get('pdf', '')
        pdf_url = paper.get('pdf_url', '').strip()
        if pdf and pdf_url:
            raise ValueError('pdf と pdf_url は片方だけ指定してください。')
        if pdf_url:
            parsed = urlsplit(pdf_url)
            if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError('pdf_url には有効なHTTPS共有URLを指定してください。')
            link = f'<a class="pdf-link" href="{esc(pdf_url)}" target="_blank" rel="noopener noreferrer">Read PDF ↗</a>'
        elif pdf:
            source = (pdf_root / pdf).resolve()
            if not source.is_relative_to(pdf_root.resolve()) or source.suffix.lower() != '.pdf':
                raise ValueError('pdf には assets/papers 内のPDFの相対パスを指定してください。')
            if not source.is_file():
                raise FileNotFoundError(f'PDFが見つかりません: {pdf}')
            linked_pdfs.append((source, pdf))
            link = f'<a class="pdf-link" href="papers/{quote(pdf, safe="/")}">Read PDF ↗</a>'
        else:
            link = '<span class="availability">PDF forthcoming</span>' if paper.get('group', 'working_papers') == 'working_papers' else ''
        meta = ' · '.join(str(paper[k]) for k in ('authors', 'status') if paper.get(k))
        if paper.get('updated'):
            meta += ' · Version: ' + str(paper['updated'])
        summary = ''
        if paper.get('summary'):
            label = 'Overview'
            summary = f'<details><summary>{label}</summary><p>{esc(paper["summary"])}</p></details>'
        rows[paper.get('group', 'working_papers')].append(f'''<article class="paper">
<h3>{esc(paper['title'])}</h3><div class="meta">{esc(meta)}</div>
<div class="topics">{esc(paper.get('topics', ''))}</div>{summary}{link}</article>''')

    context = {key: esc(data[key]) for key in ('name', 'role', 'affiliation', 'research_interests')}
    for group in rows:
        context[group] = '\n'.join(rows[group]) or '<p>Coming soon.</p>'
    context['robots'] = '<meta name="robots" content="noindex">' if data.get('noindex', True) else ''
    output = Template((ROOT / 'template.html').read_text(encoding='utf-8')).substitute(context)
    # Validate the complete input before touching existing output. Only referenced
    # PDFs are copied; files left in assets never become public accidentally.
    destination = ROOT / 'dist'
    destination.mkdir(exist_ok=True)
    if (destination / 'papers').exists():
        shutil.rmtree(destination / 'papers')
    for source, relative in linked_pdfs:
        target = destination / 'papers' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    (destination / 'index.html').write_text(output, encoding='utf-8')
    print(f'生成完了: {destination / "index.html"}')
    return destination


def main():
    parser = argparse.ArgumentParser(description='研究者用ホームページを生成します。')
    parser.add_argument('--serve', action='store_true', help='生成後にローカルプレビューを起動')
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    destination = build()
    if args.serve:
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(destination))
        with http.server.ThreadingHTTPServer(('127.0.0.1', args.port), handler) as server:
            print(f'プレビュー: http://127.0.0.1:{args.port}/ （終了: Ctrl+C）', flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass


if __name__ == '__main__':
    main()
