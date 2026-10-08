"""サイト名と文言とナビと表示設定（観葉植物トレンドサイト用）."""

SITE_NAME_EN = "LEAF FLASH"
SITE_NAME_JA = "観葉植物トレンド速報"
TAGLINE = "INDOOR GREEN / FRESH DROP"
HERO_STAMP = "NEW LEAF"
FOOTER_TEXT = "国内と海外の観葉植物とその周辺の植物の情報を自動収集しています"

# (href, label) のタプル。base.htmlのナビで使う
NAV_ITEMS = [
    ("index.html", "トップ"),
    ("feed.html", "新着情報"),
    ("trends/index.html", "トレンド分析"),
    ("varieties.html", "品種"),
    ("search.html", "検索"),
]

VARIETIES_PAGE_TITLE = "品種一覧"
VARIETIES_NOTE = "よく取り上げる主要な品種だけを対象にした簡易的な分類です。すべての記事は新着情報でご覧いただけます。"

USER_AGENT = "Mozilla/5.0 (compatible; LeafFlashSiteBot/1.0)"

# トップページの新着グリッドで、国内メディアを優先的に確保する比率（ファッション側と同じ仕組み）
JAPANESE_SOURCES = {"LOVEGREEN", "Gardenstory"}
TOP_GRID_JAPANESE_RATIO = 2 / 3
