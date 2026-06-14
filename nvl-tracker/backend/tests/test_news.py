from app.collect.news import parse_google_news_rss

RSS = """<?xml version="1.0"?>
<rss version="2.0"><channel>
  <item>
    <title>PP price falls in Asia</title>
    <link>https://news.example/pp-asia</link>
    <pubDate>Wed, 10 Jun 2026 08:00:00 GMT</pubDate>
    <description>&lt;p&gt;Polypropylene CFR SEA declines on weak demand.&lt;/p&gt;</description>
    <source url="https://polymerupdate.com">Polymerupdate</source>
  </item>
  <item>
    <title>TiO2 prices rise</title>
    <link>https://news.example/tio2</link>
    <pubDate>Tue, 09 Jun 2026 10:00:00 GMT</pubDate>
    <description>Sulfate route TiO2 climbs.</description>
  </item>
</channel></rss>"""


def test_parse_rss_basic():
    items = parse_google_news_rss(RSS, category="resin")
    assert len(items) == 2
    a = items[0]
    assert a["title"] == "PP price falls in Asia"
    assert a["url"] == "https://news.example/pp-asia"
    assert a["published_at"] == "2026-06-10"
    assert a["category"] == "resin"
    # HTML trong description bị loại bỏ
    assert "<p>" not in a["summary"]


def test_parse_rss_invalid_returns_empty():
    assert parse_google_news_rss("không-phải-xml") == []
