from theme.sources import FEED_SOURCES
from theme.keywords import EXCLUDE_KEYWORDS, INCLUDE_KEYWORDS
from theme.species import SPECIES_KEYWORDS
from theme import site


def test_feed_sources_has_search_and_filter_modes():
    modes = {s["mode"] for s in FEED_SOURCES}
    assert modes == {"search", "filter"}


def test_feed_sources_search_covers_5_terms_for_each_japanese_media():
    search_sources = [s for s in FEED_SOURCES if s["mode"] == "search"]
    lovegreen = [s for s in search_sources if s["name"] == "LOVEGREEN"]
    gardenstory = [s for s in search_sources if s["name"] == "Gardenstory"]
    assert len(lovegreen) == 5
    assert len(gardenstory) == 5


def test_feed_sources_search_urls_are_percent_encoded():
    # 検索語（日本語）はURLに埋め込む前にパーセントエンコードされている必要がある
    search_sources = [s for s in FEED_SOURCES if s["mode"] == "search"]
    for source in search_sources:
        assert "観葉植物" not in source["url"]
        assert "%" in source["url"]


def test_feed_sources_filter_sources_cover_english_media():
    filter_names = {s["name"] for s in FEED_SOURCES if s["mode"] == "filter"}
    assert filter_names == {"Gardening Know How", "Gardenista"}


def test_include_keywords_cover_major_houseplant_terms():
    assert "houseplant" in INCLUDE_KEYWORDS
    assert "monstera" in INCLUDE_KEYWORDS
    assert len(INCLUDE_KEYWORDS) >= 15


def test_exclude_keywords_is_a_non_empty_list_of_strings():
    assert len(EXCLUDE_KEYWORDS) > 0
    assert all(isinstance(k, str) for k in EXCLUDE_KEYWORDS)


def test_species_keywords_contains_common_houseplants():
    assert "モンステラ" in SPECIES_KEYWORDS
    assert "Monstera" in SPECIES_KEYWORDS["モンステラ"]
    assert "ポトス" in SPECIES_KEYWORDS


def test_site_has_required_constants():
    assert site.SITE_NAME_EN == "LEAF FLASH"
    assert site.SITE_NAME_JA == "観葉植物トレンド速報"
    assert len(site.NAV_ITEMS) == 5
    assert site.JAPANESE_SOURCES == {"LOVEGREEN", "Gardenstory"}
