#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wiki 文档生成器 - 将 Markdown 文档转换为飞书/Lark Wiki 风格的静态 HTML 页面

用法:
    python wiki_gen.py 文档.md                    # 输出到 docs/index.html
    python wiki_gen.py 文档.md -o output/         # 输出到指定目录
    python wiki_gen.py 文档.md --title "自定义标题"  # 自定义标题

安装:
    pip install -e .
    wiki-gen 文档.md
"""

import sys
import os
import re
import html as html_module
import argparse


def inline_md_to_html(text):
    """处理行内 Markdown 标记"""
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank">\1</a>', text)
    text = re.sub(r'==(.+?)==', r'<mark>\1</mark>', text)
    return text


def parse_md(text):
    """将 Markdown 文本转为 HTML 片段列表"""
    blocks = []
    lines = text.split('\n')
    i = 0
    in_table = False
    table_rows = []
    in_code = False
    code_lines = []
    in_quote = False
    quote_lines = []
    list_buffer = []

    def flush_list():
        nonlocal list_buffer
        if list_buffer:
            blocks.append(('html', '<ul>' + ''.join(list_buffer) + '</ul>'))
            list_buffer = []

    def flush_table():
        nonlocal table_rows
        if table_rows:
            html_str = '<table>'
            for idx, row in enumerate(table_rows):
                tag = 'th' if idx == 0 else 'td'
                html_str += '<tr>' + ''.join(f'<{tag}>{c}</{tag}>' for c in row) + '</tr>'
            html_str += '</table>'
            blocks.append(('html', html_str))
            table_rows = []

    def flush_code():
        nonlocal code_lines
        if code_lines:
            code_text = html_module.escape('\n'.join(code_lines))
            blocks.append(('html', f'<pre><code>{code_text}</code></pre>'))
            code_lines = []

    def flush_quote():
        nonlocal quote_lines
        if quote_lines:
            blocks.append(('html', '<blockquote>' + '<br>'.join(quote_lines) + '</blockquote>'))
            quote_lines = []

    while i < len(lines):
        line = lines[i]

        if line.strip().startswith('```'):
            if in_code:
                flush_code()
                in_code = False
            else:
                flush_table()
                flush_quote()
                flush_list()
                in_code = True
                code_lines = []
            i += 1
            continue

        if in_code:
            code_lines.append(line)
            i += 1
            continue

        if '|' in line and line.strip().startswith('|'):
            flush_quote()
            flush_list()
            cells = [c.strip() for c in line.strip().split('|')[1:-1]]
            if all(re.match(r'^[-:]+$', c) for c in cells):
                i += 1
                continue
            if not in_table:
                in_table = True
                table_rows = []
            table_rows.append([inline_md_to_html(c) for c in cells])
            i += 1
            continue
        else:
            if in_table:
                flush_table()
                in_table = False

        if line.strip().startswith('>'):
            flush_table()
            flush_list()
            content = re.sub(r'^>\s?', '', line)
            quote_lines.append(f'<p>{inline_md_to_html(content)}</p>')
            in_quote = True
            i += 1
            continue
        else:
            if in_quote:
                if line.strip() == '':
                    quote_lines.append('')
                    i += 1
                    continue
                flush_quote()
                in_quote = False

        if re.match(r'^[-*_]{3,}\s*$', line.strip()):
            flush_table()
            flush_quote()
            flush_list()
            blocks.append(('html', '<hr>'))
            i += 1
            continue

        h_match = re.match(r'^(#{1,6})\s+(.*)', line)
        if h_match:
            flush_table()
            flush_quote()
            flush_list()
            level = len(h_match.group(1))
            heading_text = h_match.group(2).strip()
            heading_id = heading_text.replace(' ', '-')
            heading_id = re.sub(r'[^\w\-]', '', heading_id)
            if level == 2:
                blocks.append(('h2', heading_text))
                blocks.append(('html', f'<h2 id="{heading_id}">{inline_md_to_html(heading_text)}</h2>'))
            elif level == 3:
                blocks.append(('h3', heading_text))
                blocks.append(('html', f'<h3 id="{heading_id}">{inline_md_to_html(heading_text)}</h3>'))
            else:
                blocks.append(('html', f'<h{level}>{inline_md_to_html(heading_text)}</h{level}>'))
            i += 1
            continue

        li_match = re.match(r'^(\s*)[-*+]\s+(.*)', line)
        num_match = re.match(r'^(\s*)\d+\.\s+(.*)', line)
        if li_match or num_match:
            flush_table()
            flush_quote()
            content = (li_match or num_match).group(2)
            list_buffer.append(f'<li>{inline_md_to_html(content)}</li>')
            i += 1
            continue

        bold_match = re.match(r'^\*\*(.+)\*\*\s*$', line.strip())
        if bold_match:
            flush_table()
            flush_quote()
            blocks.append(('html', f'<p><strong>{inline_md_to_html(bold_match.group(1))}</strong></p>'))
            i += 1
            continue

        if line.strip() == '':
            flush_list()
            i += 1
            continue

        flush_list()
        blocks.append(('html', f'<p>{inline_md_to_html(line.strip())}</p>'))
        i += 1

    flush_table()
    flush_quote()
    flush_code()
    flush_list()
    return blocks


def build_nav(blocks):
    """从 blocks 中提取 H2/H3 标题构建导航"""
    h2_items = []
    current_h2 = None
    for t, content in blocks:
        if t == 'h2':
            current_h2 = {'title': content, 'children': []}
            h2_items.append(current_h2)
        elif t == 'h3' and current_h2:
            current_h2['children'].append(content)
    return h2_items


def build_html(text, title="文档"):
    blocks = parse_md(text)
    nav = build_nav(blocks)

    nav_html = ''
    for h2 in nav:
        h2_id = re.sub(r'[^\w\-]', '', h2['title'].replace(' ', '-'))
        nav_html += f'<li class="nav-h2"><a href="#{h2_id}">{html_module.escape(h2["title"])}</a>'
        if h2['children']:
            nav_html += '<ul>'
            for h3 in h2['children']:
                h3_id = re.sub(r'[^\w\-]', '', h3.replace(' ', '-'))
                nav_html += f'<li class="nav-h3"><a href="#{h3_id}">{html_module.escape(h3)}</a></li>'
            nav_html += '</ul>'
        nav_html += '</li>'

    content_html = '\n'.join(item[1] for item in blocks if item[0] != 'h2' and item[0] != 'h3')

    css = '''
* { margin: 0; padding: 0; box-sizing: border-box; }
:root { --banner-start: #1a1a2e; --banner-end: #16213e; --banner-accent: #0f3460; --sidebar-bg: #f7f8fa; --sidebar-hover: #e8ecf1; --sidebar-active: #e0e7ff; --sidebar-active-border: #4f6ef7; --text-primary: #1d2129; --text-secondary: #4e5969; --text-muted: #86909c; --border: #e5e6eb; --bg-white: #ffffff; --accent: #4f6ef7; --code-bg: #f2f3f5; --blockquote-border: #4f6ef7; --blockquote-bg: #f7f8fa; --table-stripe: #f7f8fa; --table-border: #e5e6eb; --table-header-bg: #f2f3f5; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; color: var(--text-primary); background: var(--bg-white); line-height: 1.8; }
.banner { background: linear-gradient(135deg, var(--banner-start), var(--banner-end), var(--banner-accent)); padding: 60px 40px 50px; text-align: center; position: relative; overflow: hidden; }
.banner::before { content: ''; position: absolute; top: -50%; left: -50%; width: 200%; height: 200%; background: radial-gradient(ellipse at 30% 50%, rgba(79,110,247,0.15) 0%, transparent 60%), radial-gradient(ellipse at 70% 50%, rgba(79,110,247,0.1) 0%, transparent 60%); }
.banner h1 { font-size: 36px; font-weight: 700; color: #ffffff; position: relative; z-index: 1; letter-spacing: 1px; }
.banner p { font-size: 16px; color: rgba(255,255,255,0.7); margin-top: 12px; position: relative; z-index: 1; }
.page-wrapper { display: flex; max-width: 1280px; margin: 0 auto; min-height: calc(100vh - 220px); }
.sidebar { width: 260px; min-width: 260px; background: var(--sidebar-bg); border-right: 1px solid var(--border); padding: 24px 0; position: sticky; top: 0; height: 100vh; overflow-y: auto; }
.sidebar-title { font-size: 14px; font-weight: 600; color: var(--text-secondary); padding: 0 20px 16px; text-transform: uppercase; letter-spacing: 1px; }
.sidebar ul { list-style: none; }
.sidebar .nav-h2 > a { display: block; padding: 8px 20px; font-size: 14px; color: var(--text-primary); text-decoration: none; font-weight: 500; border-left: 3px solid transparent; transition: all 0.15s; }
.sidebar .nav-h2 > a:hover { background: var(--sidebar-hover); color: var(--accent); }
.sidebar .nav-h2 > a.active { background: var(--sidebar-active); color: var(--accent); border-left-color: var(--sidebar-active-border); font-weight: 600; }
.sidebar .nav-h3 > a { display: block; padding: 5px 20px 5px 36px; font-size: 13px; color: var(--text-secondary); text-decoration: none; }
.sidebar .nav-h3 > a:hover { color: var(--accent); }
.main-content { flex: 1; padding: 40px 48px 80px; max-width: 860px; overflow-x: hidden; }
.main-content h2 { font-size: 26px; font-weight: 700; margin: 48px 0 16px; padding-bottom: 8px; border-bottom: 2px solid var(--border); }
.main-content h3 { font-size: 20px; font-weight: 600; margin: 32px 0 12px; }
.main-content p { margin: 12px 0; font-size: 15px; }
.main-content a { color: var(--accent); text-decoration: none; }
.main-content a:hover { text-decoration: underline; }
.main-content table { width: 100%; border-collapse: collapse; margin: 16px 0; font-size: 14px; border-radius: 8px; overflow: hidden; border: 1px solid var(--table-border); }
.main-content th { background: var(--table-header-bg); font-weight: 600; text-align: left; padding: 10px 14px; border-bottom: 2px solid var(--table-border); }
.main-content td { padding: 10px 14px; border-bottom: 1px solid var(--table-border); }
.main-content tr:nth-child(even) td { background: var(--table-stripe); }
.main-content blockquote { margin: 16px 0; padding: 12px 20px; background: var(--blockquote-bg); border-left: 4px solid var(--blockquote-border); border-radius: 0 6px 6px 0; font-size: 14px; color: var(--text-secondary); }
.main-content code { background: var(--code-bg); padding: 2px 6px; border-radius: 4px; font-size: 13px; font-family: "SF Mono", "Monaco", "Menlo", "Consolas", monospace; color: #e64539; }
.main-content pre { background: #1e1e2e; color: #cdd6f4; padding: 20px; border-radius: 8px; overflow-x: auto; margin: 16px 0; font-size: 13px; line-height: 1.6; }
.main-content pre code { background: none; padding: 0; color: inherit; }
.main-content ul, .main-content ol { margin: 12px 0; padding-left: 24px; }
.main-content li { margin: 6px 0; font-size: 15px; }
.main-content hr { border: none; border-top: 1px solid var(--border); margin: 32px 0; }
.back-to-top { position: fixed; bottom: 40px; right: 40px; width: 44px; height: 44px; background: var(--accent); color: white; border: none; border-radius: 50%; cursor: pointer; font-size: 20px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 14px rgba(79,110,247,0.35); opacity: 0; transform: translateY(20px); pointer-events: none; z-index: 100; transition: all 0.2s; }
.back-to-top.visible { opacity: 1; transform: translateY(0); pointer-events: auto; }
.footer { text-align: center; padding: 24px; color: var(--text-muted); font-size: 13px; border-top: 1px solid var(--border); }
@media (max-width: 768px) { .sidebar { display: none; } .main-content { padding: 24px 20px 60px; max-width: 100%; } .banner { padding: 40px 20px; } .banner h1 { font-size: 24px; } }
'''

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html_module.escape(title)}</title>
<style>
{css}
</style>
</head>
<body>
<header class="banner"><h1>{html_module.escape(title)}</h1><p>Generated by wiki-doc-generator</p></header>
<div class="page-wrapper">
<aside class="sidebar"><div class="sidebar-title">目录导航</div><ul>{nav_html}</ul></aside>
<main class="main-content">{content_html}</main>
</div>
<footer class="footer">Generated by <a href="https://github.com" target="_blank">wiki-doc-generator</a></footer>
<button class="back-to-top" onclick="window.scrollTo({{top:0,behavior:'smooth'}})">↑</button>
<script>
const navLinks=document.querySelectorAll('.sidebar a');
const headings=document.querySelectorAll('.main-content h2');
const btt=document.querySelector('.back-to-top');
function u(){{let c='';headings.forEach(h=>{{if(window.scrollY>=h.offsetTop-100)c=h.id}});navLinks.forEach(a=>a.classList.toggle('active',a.getAttribute('href')==='#'+c));btt.classList.toggle('visible',window.scrollY>400)}}
u();window.addEventListener('scroll',u);
</script>
</body>
</html>'''


def main():
    parser = argparse.ArgumentParser(
        description='将 Markdown 文档转换为飞书/Lark Wiki 风格的静态 HTML 页面',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例:
  wiki-gen README.md
  wiki-gen 文档.md -o ./public/
  wiki-gen 文档.md --title "自定义标题"
        '''
    )
    parser.add_argument('input', help='Markdown 文件路径')
    parser.add_argument('-o', '--output', default='docs/', help='输出目录（默认 docs/）')
    parser.add_argument('-t', '--title', help='页面标题（默认使用文件名）')
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f'错误: 文件不存在 - {args.input}')
        sys.exit(1)

    title = args.title or os.path.splitext(os.path.basename(args.input))[0]

    print(f'读取: {args.input}')
    with open(args.input, 'r', encoding='utf-8') as f:
        text = f.read()

    print(f'生成 Wiki 页面: "{title}"')
    result = build_html(text, title)

    os.makedirs(args.output, exist_ok=True)
    output_path = os.path.join(args.output, 'index.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result)

    size_kb = os.path.getsize(output_path) / 1024
    print(f'完成! 输出: {output_path} ({size_kb:.1f} KB)')
    print(f'用浏览器打开 file:///{output_path.replace(os.sep, "/")} 查看效果')


if __name__ == '__main__':
    main()
