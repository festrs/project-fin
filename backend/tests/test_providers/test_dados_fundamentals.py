from unittest.mock import MagicMock, patch

import pytest

from app.providers.dados_de_mercado import DadosDeMercadoProvider


BALANCE_HTML = """
<html><body>
<table><thead><tr><th>Item</th><th>2025</th><th>2024</th><th>2023</th><th>2022</th><th>2021</th></tr></thead>
<tbody>
<tr><td>Dívida Líquida</td><td>100.000</td><td>120.000</td><td>110.000</td><td>90.000</td><td>80.000</td></tr>
</tbody></table>
</body></html>
"""

RESULTADO_HTML = """
<html><body>
<table><thead><tr><th>Item</th><th>2025</th><th>2024</th><th>2023</th><th>2022</th><th>2021</th></tr></thead>
<tbody>
<tr><td>LPA</td><td>5,00</td><td>4,50</td><td>4,00</td><td>3,50</td><td>3,00</td></tr>
<tr><td>Lucro Líquido</td><td>50.000</td><td>45.000</td><td>40.000</td><td>35.000</td><td>30.000</td></tr>
<tr><td>EBITDA</td><td>80.000</td><td>75.000</td><td>70.000</td><td>65.000</td><td>60.000</td></tr>
</tbody></table>
</body></html>
"""


@pytest.fixture
def provider():
    return DadosDeMercadoProvider()


class TestScrapeFinancialTable:
    def test_returns_years_and_rows(self, provider, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.text = RESULTADO_HTML
        mock_resp.raise_for_status = MagicMock()

        monkeypatch.setattr("app.providers.dados_de_mercado.httpx.get", lambda *a, **kw: mock_resp)

        result = provider._scrape_financial_table("https://example.com/acoes/petr4/resultado")

        assert result["years"] == [2025, 2024, 2023, 2022, 2021]
        assert "LPA" in result
        assert "Lucro Líquido" in result
        assert "EBITDA" in result

    def test_parses_lpa_values(self, provider, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.text = RESULTADO_HTML
        mock_resp.raise_for_status = MagicMock()

        monkeypatch.setattr("app.providers.dados_de_mercado.httpx.get", lambda *a, **kw: mock_resp)

        result = provider._scrape_financial_table("https://example.com/acoes/petr4/resultado")

        assert result["LPA"][2025] == pytest.approx(5.0)
        assert result["LPA"][2021] == pytest.approx(3.0)

    def test_parses_large_numbers(self, provider, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.text = BALANCE_HTML
        mock_resp.raise_for_status = MagicMock()

        monkeypatch.setattr("app.providers.dados_de_mercado.httpx.get", lambda *a, **kw: mock_resp)

        result = provider._scrape_financial_table("https://example.com/acoes/petr4/balanco")

        assert result["Dívida Líquida"][2025] == pytest.approx(100000.0)
        assert result["Dívida Líquida"][2021] == pytest.approx(80000.0)

    def test_returns_empty_dict_on_http_error(self, provider, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("404 Not Found")

        monkeypatch.setattr("app.providers.dados_de_mercado.httpx.get", lambda *a, **kw: mock_resp)

        result = provider._scrape_financial_table("https://example.com/acoes/invalid/balanco")

        assert result == {}


class TestScrapeFundamentals:
    def test_returns_fundamentals_shape(self, provider, monkeypatch):
        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            if call_count == 0:
                mock_resp.text = BALANCE_HTML
            else:
                mock_resp.text = RESULTADO_HTML
            call_count += 1
            return mock_resp

        monkeypatch.setattr("app.providers.dados_de_mercado.httpx.get", mock_get)

        result = provider.scrape_fundamentals("PETR4.SA")

        assert "ipo_years" in result
        assert "eps_history" in result
        assert "net_income_history" in result
        assert "debt_history" in result
        assert "current_net_debt_ebitda" in result
        assert "raw_data" in result

    def test_eps_history_has_5_items(self, provider, monkeypatch):
        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            if call_count == 0:
                mock_resp.text = BALANCE_HTML
            else:
                mock_resp.text = RESULTADO_HTML
            call_count += 1
            return mock_resp

        monkeypatch.setattr("app.providers.dados_de_mercado.httpx.get", mock_get)

        result = provider.scrape_fundamentals("PETR4.SA")

        assert len(result["eps_history"]) == 5

    def test_net_income_history_has_5_items(self, provider, monkeypatch):
        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            if call_count == 0:
                mock_resp.text = BALANCE_HTML
            else:
                mock_resp.text = RESULTADO_HTML
            call_count += 1
            return mock_resp

        monkeypatch.setattr("app.providers.dados_de_mercado.httpx.get", mock_get)

        result = provider.scrape_fundamentals("PETR4.SA")

        assert len(result["net_income_history"]) == 5

    def test_debt_history_has_5_items(self, provider, monkeypatch):
        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            if call_count == 0:
                mock_resp.text = BALANCE_HTML
            else:
                mock_resp.text = RESULTADO_HTML
            call_count += 1
            return mock_resp

        monkeypatch.setattr("app.providers.dados_de_mercado.httpx.get", mock_get)

        result = provider.scrape_fundamentals("PETR4.SA")

        assert len(result["debt_history"]) == 5

    def test_current_net_debt_ebitda_is_not_none(self, provider, monkeypatch):
        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            if call_count == 0:
                mock_resp.text = BALANCE_HTML
            else:
                mock_resp.text = RESULTADO_HTML
            call_count += 1
            return mock_resp

        monkeypatch.setattr("app.providers.dados_de_mercado.httpx.get", mock_get)

        result = provider.scrape_fundamentals("PETR4.SA")

        assert result["current_net_debt_ebitda"] is not None

    def test_eps_history_values_are_correct(self, provider, monkeypatch):
        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            if call_count == 0:
                mock_resp.text = BALANCE_HTML
            else:
                mock_resp.text = RESULTADO_HTML
            call_count += 1
            return mock_resp

        monkeypatch.setattr("app.providers.dados_de_mercado.httpx.get", mock_get)

        result = provider.scrape_fundamentals("PETR4.SA")

        # eps_history should be a flat list of floats (most recent first)
        assert result["eps_history"][0] == pytest.approx(5.0)
        assert result["eps_history"][-1] == pytest.approx(3.0)

    def test_strips_sa_suffix_in_url(self, provider, monkeypatch):
        urls_called = []

        def mock_get(url, *args, **kwargs):
            urls_called.append(url)
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            if "balanco" in url:
                mock_resp.text = BALANCE_HTML
            else:
                mock_resp.text = RESULTADO_HTML
            return mock_resp

        monkeypatch.setattr("app.providers.dados_de_mercado.httpx.get", mock_get)

        provider.scrape_fundamentals("PETR4.SA")

        for url in urls_called:
            assert ".SA" not in url
            assert "petr4" in url.lower()

    def test_returns_empty_shape_on_error(self, provider, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("503 Service Unavailable")

        monkeypatch.setattr("app.providers.dados_de_mercado.httpx.get", lambda *a, **kw: mock_resp)

        result = provider.scrape_fundamentals("PETR4.SA")

        assert "eps_history" in result
        assert result["eps_history"] == []
        assert result["net_income_history"] == []
        assert result["debt_history"] == []
