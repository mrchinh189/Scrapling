from app.models import SourceConfig
from app.scraper.runner import extract_price

HTML = """
<html><body>
  <div class="product">
    <span class="name">Thép xây dựng</span>
    <span class="price-value">15.800 VND</span>
  </div>
</body></html>
"""


def test_extract_price_from_html():
    src = SourceConfig(
        code="STEEL", name="Thép", unit="VND/kg",
        url="https://example.com/thep", price_selector=".price-value",
    )
    rec = extract_price(HTML, src)
    assert rec is not None
    assert rec.material_code == "STEEL"
    assert rec.price == 15800.0
    assert rec.unit == "VND/kg"
    assert rec.source == "example.com"


def test_extract_price_missing_selector_returns_none():
    src = SourceConfig(
        code="X", name="X", url="https://example.com",
        price_selector=".not-found",
    )
    assert extract_price(HTML, src) is None
