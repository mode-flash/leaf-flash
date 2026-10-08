# 観葉植物トレンドサイト（LEAF FLASH）

観葉植物とその周辺の植物（多肉植物と塊根植物とエアプランツなど）のニュースとトレンド分析を、園芸メディアのRSSから自動収集して公開する静的サイト。

## セットアップ

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

## 手動実行

```bash
python -m scripts.fetch_feeds
python -m scripts.build_site
```

## テスト

```bash
pytest
```

## 運用メモ

- GitHub Actionsが1日3回（1時と9時と17時 UTC）走り、`main`ブランチに直接コミットしてpushする。
  ローカルで変更をpushする前には、必ず`git pull`してから作業すること。
- `docs/`はビルドの生成物。手で編集しないこと（`build_site.py`を実行するたびに上書きされる）。
- サイト固有の設定（取得元とキーワードと品種辞書と文言と配色）は`theme/`と`static/theme.css`に集約している。差し替えるときはそこだけを直す。
