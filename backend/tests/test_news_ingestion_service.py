from app.services.news_ingestion_service import NewsIngestionService


def test_normalize_article_uses_extracted_text_and_placeholder_image(monkeypatch):
    service = NewsIngestionService(
        api_key="test",
        extract_full_text=True,
        placeholder_image_url="https://example.com/placeholder.jpg",
    )

    monkeypatch.setattr(service, "_extract_article_text", lambda _: "Fully extracted article body text")

    row = service._normalize_article(
        {
            "title": "Test title",
            "url": "https://example.com/article",
            "description": "Snippet text",
            "content": "",
            "urlToImage": "",
            "publishedAt": "2026-04-16T08:20:00Z",
            "source": {"name": "Test Source"},
        }
    )

    assert row is not None
    assert row["text"] == "Fully extracted article body text"
    assert row["image_path"] == "https://example.com/placeholder.jpg"


def test_normalize_article_falls_back_to_snippet_when_extraction_missing(monkeypatch):
    service = NewsIngestionService(api_key="test", extract_full_text=True)
    monkeypatch.setattr(service, "_extract_article_text", lambda _: None)

    row = service._normalize_article(
        {
            "title": "Test title",
            "url": "https://example.com/article",
            "description": "Snippet text",
            "content": "",
            "publishedAt": "2026-04-16T08:20:00Z",
            "source": {"name": "Test Source"},
        }
    )

    assert row is not None
    assert row["text"] == "Snippet text"


def test_strip_html_removes_markup():
    service = NewsIngestionService(api_key="test")
    html = "<html><body><h1>Title</h1><p>Body text</p><script>ignore()</script></body></html>"

    text = service._strip_html(html)

    assert "Title" in text
    assert "Body text" in text
    assert "ignore()" not in text
