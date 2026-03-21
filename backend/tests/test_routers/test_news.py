from unittest.mock import patch, MagicMock


@patch("app.routers.news.get_market_data_service")
def test_get_market_news(mock_get_mds, client):
    mock_finnhub = MagicMock()
    mock_finnhub.get_market_news.return_value = [
        {
            "id": 1,
            "category": "technology",
            "headline": "Test headline",
            "summary": "Test summary",
            "url": "https://example.com",
            "source": "Reuters",
            "datetime": 1700000000,
            "image": "",
        }
    ]
    mock_md = MagicMock()
    mock_md._finnhub = mock_finnhub
    mock_get_mds.return_value = mock_md

    resp = client.get("/api/news")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["news"]) == 1
    assert data["news"][0]["headline"] == "Test headline"
    assert data["news"][0]["category"] == "technology"


@patch("app.routers.news.get_market_data_service")
def test_get_market_news_error_returns_empty(mock_get_mds, client):
    mock_finnhub = MagicMock()
    mock_finnhub.get_market_news.side_effect = Exception("API error")
    mock_md = MagicMock()
    mock_md._finnhub = mock_finnhub
    mock_get_mds.return_value = mock_md

    resp = client.get("/api/news")
    assert resp.status_code == 200
    data = resp.json()
    assert data["news"] == []
