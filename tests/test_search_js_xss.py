"""static/search.jsのrenderCardが、属性値コンテキストから脱出できる文字列
（image_url中の`"`等）を与えられても安全であることを確認する回帰テスト。

JS側のテストランナーは本プロジェクトに無いため、Node（外部npm依存なし、
node:fs・node:assert等の標準モジュールのみ使用）で実行できる最小テストを
tests/js/search_render_test.mjs に用意し、ここからサブプロセスとして呼び出す。
Nodeがインストールされていない環境ではスキップする。
"""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TEST_SCRIPT = REPO_ROOT / "tests" / "js" / "search_render_test.mjs"

pytestmark = pytest.mark.skipif(
    shutil.which("node") is None,
    reason="Node.jsが見つからないため、search.jsのXSS回帰テストをスキップします",
)


def test_search_js_render_card_does_not_allow_attribute_breakout():
    result = subprocess.run(
        ["node", str(TEST_SCRIPT)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        "search.jsのrenderCard XSS回帰テストが失敗しました\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    assert "OK" in result.stdout
