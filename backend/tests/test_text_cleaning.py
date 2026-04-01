from app.utils.text import clean_article_text


def test_clean_article_text_removes_boilerplate():
    raw = "Breaking update. Subscribe now   for more.   "
    cleaned = clean_article_text(raw)
    assert "subscribe now" not in cleaned.lower()
