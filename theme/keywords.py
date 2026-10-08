"""採用キーワードと除外キーワード（観葉植物トレンドサイト用）.

INCLUDE_KEYWORDSは、filterモードの取得元（Gardening Know HowとGardenista）で、
タイトルか概要にこのどれかを含む記事だけを通すために使う（英語媒体向け）。
EXCLUDE_KEYWORDSは、採用された記事のうち明らかに観葉植物と無関係なものを
弾くために使う（searchとfilterどちらのモードにも適用する）。

どちらも初期値であり、実データの検証で増減する（design doc 3.3節と3.4節）。
"""

INCLUDE_KEYWORDS = [
    "houseplant", "house plant", "indoor plant", "monstera", "pothos", "philodendron",
    "snake plant", "ZZ plant", "fiddle leaf", "rubber plant", "calathea", "ficus",
    "succulent", "cactus", "agave", "air plant", "staghorn fern", "peperomia",
    "dracaena", "string of pearls",
]

# 初期値。LOVEGREENとGardenstoryの検索フィードは庭づくりや雑草対策、クイズ記事等を
# 混入させることがあるため、実際に混入した語のみを狭く狙う（design doc 3.4節）。
EXCLUDE_KEYWORDS = [
    "雑草対策",
    "防草シート",
    "家庭菜園",
    "野菜の育て方",
    "アプリ無料配信",
    "3択クイズ",
]
