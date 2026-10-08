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
#
# 以下4語はTask 8の実データ検証で追加（2026-10-08）。
# - "Meanwhile, on Remodelista"：GardenistaがIncludeで拾うが、姉妹サイトRemodelista
#   への誘導記事（タイトル・本文に観葉植物の解説は無い。概要文中の「Houseplants」が
#   他の屋内アイテム例と並んで一度出るだけでINCLUDE_KEYWORDSの"houseplant"に誤って
#   マッチしていた）
# - "プチプラ花コーデ"：Gardenstoryの連載名（ドライフラワー・造花クラフトが主題で、
#   鉢植えの観葉植物とは無関係。実データでVol.113とVol.137の2件を確認）
# - "ガーデンストーリーシリーズ"/"ガーデングッズ・プロジェクト"：Gardenstory自社の
#   屋外ガーデニング用品ブランドの新商品告知・投票企画（アプリ無料配信と同種の
#   自社プロモーション記事で、観葉植物の解説記事ではない）
EXCLUDE_KEYWORDS = [
    "雑草対策",
    "防草シート",
    "家庭菜園",
    "野菜の育て方",
    "アプリ無料配信",
    "3択クイズ",
    "Meanwhile, on Remodelista",
    "プチプラ花コーデ",
    "ガーデンストーリーシリーズ",
    "ガーデングッズ・プロジェクト",
]
