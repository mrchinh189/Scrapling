from app.scraper.price_parser import parse_price


def test_vietnamese_thousand_separator():
    assert parse_price("1.850.000 VND") == 1850000.0
    assert parse_price("12.500 đ/kg") == 12500.0


def test_vietnamese_decimal_comma():
    assert parse_price("12.500,50") == 12500.5
    assert parse_price("99,90") == 99.9


def test_us_format():
    assert parse_price("12,500") == 12500.0
    assert parse_price("1,234.56") == 1234.56


def test_plain_and_decimal():
    assert parse_price("18500") == 18500.0
    assert parse_price("12.5") == 12.5


def test_with_regex_pattern():
    assert parse_price("Giá: 25.000đ (đã gồm VAT)", r"\d[\d.]*") == 25000.0


def test_no_number_returns_none():
    assert parse_price("Liên hệ") is None
    assert parse_price("") is None
    assert parse_price(None) is None
