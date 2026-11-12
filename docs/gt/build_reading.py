"""Render the protocol into a self-contained local reading page.

Dependency: Python-Markdown. The Markdown file remains the canonical source.
"""
from pathlib import Path
import html
import markdown

ROOT = Path(__file__).resolve().parent
source = (ROOT / "evaluation_protocol.md").read_text(encoding="utf-8")
md = markdown.Markdown(extensions=["tables", "fenced_code", "toc", "sane_lists"], extension_configs={"toc": {"toc_depth": "2-2"}})
content = md.convert(source)
title = "Coding-based Data Video Benchmark：Ground Truth 与评测方案"
page = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{color-scheme:light;--ink:#202d38;--muted:#607080;--accent:#245f78;--border:#dde4e9;--surface:#f4f7f9}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#fff;color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;font-size:16px;line-height:1.85}a{color:var(--accent);text-underline-offset:3px}
.shell{max-width:1480px;margin:auto;display:grid;grid-template-columns:270px minmax(0,1fr);gap:54px;padding:40px 48px 80px}.sidebar{position:sticky;top:28px;align-self:start;max-height:calc(100vh - 56px);overflow:auto;font-size:13px;line-height:1.65;padding-right:18px}.eyebrow{font-size:12px;letter-spacing:1.2px;color:var(--muted);margin:0 0 20px}.sidebar h2{font-size:14px;font-weight:600;margin:0 0 15px}.toc ul{list-style:none;padding:0;margin:0}.toc li{margin:0 0 10px}.toc a{color:#526370;text-decoration:none}.toc a:hover{color:var(--accent)}main{min-width:0;max-width:1030px}
h1{font-size:32px;line-height:1.42;letter-spacing:-.5px;margin:0 0 22px;font-weight:650}h2{font-size:25px;line-height:1.5;margin:58px 0 22px;padding-top:8px;border-top:1px solid var(--border);scroll-margin-top:24px}h3{font-size:19px;line-height:1.6;margin:30px 0 12px;scroll-margin-top:24px}p{margin:13px 0}li{margin:6px 0}strong{font-weight:650}blockquote{margin:22px 0;padding:14px 20px;background:#edf5f8;border-left:3px solid #669bb2}blockquote p{margin:0}
table{width:100%;border-collapse:collapse;font-size:14px;line-height:1.7;margin:22px 0;table-layout:auto}th,td{border:1px solid var(--border);padding:11px 13px;text-align:left;vertical-align:top;overflow-wrap:anywhere}th{background:var(--surface);font-weight:600}td:first-child{min-width:96px}code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.88em;background:var(--surface);padding:2px 5px;border-radius:3px;overflow-wrap:anywhere}pre{background:var(--surface);border:1px solid var(--border);padding:18px 20px;overflow:auto;border-radius:7px;line-height:1.7}pre code{padding:0;background:none;white-space:pre;overflow-wrap:normal}.note{font-size:12px;color:var(--muted);border-top:1px solid var(--border);margin-top:30px;padding-top:14px}.header-note{color:var(--muted);font-size:13px;margin:0 0 24px}.footer{margin-top:54px;padding-top:20px;border-top:1px solid var(--border);font-size:13px;color:var(--muted)}
@media(max-width:1000px){.shell{display:block;padding:28px 22px 60px}.sidebar{position:static;max-height:none;margin-bottom:36px;padding:20px;background:var(--surface)}.sidebar .toc ul{columns:2;column-gap:24px}.toc li{break-inside:avoid}h1{font-size:27px}h2{font-size:23px}table{display:block;overflow-x:auto;white-space:normal}th,td{min-width:120px}main{max-width:none}}
@media(max-width:560px){.sidebar .toc ul{columns:1}body{font-size:15px}.shell{padding:22px 16px 48px}h1{font-size:25px}h2{font-size:21px}}
@media print{.shell{display:block;padding:0}.sidebar,.header-note{display:none}main{max-width:none}body{font-size:10pt}h1{font-size:22pt}h2{font-size:16pt;break-after:avoid;margin-top:25px}h3{font-size:12pt;break-after:avoid}table{font-size:9pt}pre{white-space:pre-wrap}a{color:inherit;text-decoration:none}}
</style>
</head>
<body>
<div class="shell">
<aside class="sidebar" aria-label="文档目录"><p class="eyebrow">RESEARCH PROTOCOL · 2026.09</p><h2>方案目录</h2>__TOC__<p class="note">设计稿 1.0<br>构造示例，不含实验结果<br>原始 metric 文件未修改</p></aside>
<main><p class="header-note">从公开任务到可核验 ground truth，再到代码执行与视听证据</p>__CONTENT__<p class="footer">此页面由 evaluation_protocol.md 生成。示例 JSON 与校验脚本随方案交付；运行时 harness 和视频裁判尚未实现。</p></main>
</div>
</body>
</html>
""".replace("__TITLE__", html.escape(title)).replace("__TOC__", md.toc).replace("__CONTENT__", content)
(ROOT / "evaluation_protocol.html").write_text(page, encoding="utf-8")
print("Rendered evaluation_protocol.html from canonical Markdown")
