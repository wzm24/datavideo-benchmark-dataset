"""Render the Chinese evaluation contract as a standalone HTML file."""

from pathlib import Path

import markdown


ROOT = Path(r"D:\dev\data_video_dataset_pipeline")
SOURCE = ROOT / "benchmark_draft" / "gt" / "evaluation_contract_v2_20261105.md"
TARGET = ROOT / "benchmark_draft" / "gt" / "evaluation_contract_v2_20261105.html"


def main() -> None:
    body = markdown.markdown(
        SOURCE.read_text(encoding="utf-8"),
        extensions=["tables", "fenced_code", "sane_lists"],
    )
    TARGET.write_text(
        """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DataVideo Benchmark 评测契约 v2</title>
<style>
body{font-family:"Microsoft YaHei","Noto Sans SC",Segoe UI,sans-serif;max-width:1200px;margin:32px auto;padding:0 28px;line-height:1.7;color:#20242b;background:#fff}
h1{font-size:30px;border-bottom:2px solid #263238;padding-bottom:12px}
h2{margin-top:34px;border-bottom:1px solid #d9dde5;padding-bottom:7px}
h3{margin-top:24px}
table{border-collapse:collapse;width:100%;margin:14px 0;font-size:14px}
th,td{border:1px solid #d9dde5;padding:8px 10px;text-align:left;vertical-align:top}
th{background:#f0f3f7}
code{background:#eef1f5;padding:2px 5px;border-radius:4px}
pre{background:#f5f7fa;border:1px solid #e1e5eb;padding:14px;overflow:auto;border-radius:8px}
blockquote{border-left:4px solid #59748a;margin-left:0;padding-left:16px;color:#4d5964;background:#f7f9fb}
</style></head><body>
"""
        + body
        + "\n</body></html>\n",
        encoding="utf-8",
    )
    print(TARGET)


if __name__ == "__main__":
    main()
