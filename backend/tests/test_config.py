import os
from unittest.mock import patch


def test_settings_has_finnhub_api_key():
    with patch.dict(os.environ, {"FINNHUB_API_KEY": "test-key", "BRAPI_API_KEY": "test-key2"}):
        from importlib import reload
        import app.config
        reload(app.config)
        assert app.config.settings.finnhub_api_key == "test-key"


def test_settings_has_brapi_api_key():
    with patch.dict(os.environ, {"FINNHUB_API_KEY": "test-key", "BRAPI_API_KEY": "test-key2"}):
        from importlib import reload
        import app.config
        reload(app.config)
        assert app.config.settings.brapi_api_key == "test-key2"
