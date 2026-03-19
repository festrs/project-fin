from unittest.mock import MagicMock

import pytest

from app.providers.dados_de_mercado import DadosDeMercadoProvider

# Simulates the main stock page with Indicadores + Resultados tables embedded
MAIN_PAGE_HTML = """
<html><body>
<h2>Indicadores</h2>
<table><thead><tr><th>Conta</th><th>2024</th><th>2023</th><th>2022</th><th>2021</th><th>2020</th></tr></thead>
<tbody>
<tr><td>P/L</td><td>30,39</td><td>26,36</td><td>21,00</td><td>18,00</td><td>15,00</td></tr>
<tr><td>LPA</td><td>5,00</td><td>4,50</td><td>4,00</td><td>3,50</td><td>3,00</td></tr>
<tr><td>EBITDA</td><td>80.000 mi</td><td>75.000 mi</td><td>70.000 mi</td><td>65.000 mi</td><td>60.000 mi</td></tr>
<tr><td>Dívida líquida</td><td>100.000 mi</td><td>120.000 mi</td><td>110.000 mi</td><td>90.000 mi</td><td>80.000 mi</td></tr>
</tbody></table>

<h2>Resultados</h2>
<table><thead><tr><th>Conta</th><th>2024</th><th>2023</th><th>2022</th><th>2021</th><th>2020</th></tr></thead>
<tbody>
<tr><td>Receita líquida</td><td>200.000 mi</td><td>190.000 mi</td><td>180.000 mi</td><td>170.000 mi</td><td>160.000 mi</td></tr>
<tr><td>Lucro líquido</td><td>50.000 mi</td><td>45.000 mi</td><td>40.000 mi</td><td>35.000 mi</td><td>30.000 mi</td></tr>
</tbody></table>
</body></html>
"""

MAIN_PAGE_NO_TABLES_HTML = """
<html><body><h1>Stock page</h1><p>No data available.</p></body></html>
"""


@pytest.fixture
def provider():
    return DadosDeMercadoProvider()


def _mock_get_for_html(html):
    def mock_get(url, *args, **kwargs):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.text = html
        return mock_resp
    return mock_get


class TestScrapeFundamentals:
    def test_returns_fundamentals_shape(self, provider, monkeypatch):
        monkeypatch.setattr("app.providers.dados_de_mercado.httpx.get", _mock_get_for_html(MAIN_PAGE_HTML))

        result = provider.scrape_fundamentals("PETR4.SA")

        assert "ipo_years" in result
        assert "eps_history" in result
        assert "net_income_history" in result
        assert "debt_history" in result
        assert "current_net_debt_ebitda" in result
        assert "raw_data" in result

    def test_eps_history_has_5_items(self, provider, monkeypatch):
        monkeypatch.setattr("app.providers.dados_de_mercado.httpx.get", _mock_get_for_html(MAIN_PAGE_HTML))

        result = provider.scrape_fundamentals("PETR4.SA")

        assert len(result["eps_history"]) == 5

    def test_eps_history_values_are_correct(self, provider, monkeypatch):
        monkeypatch.setattr("app.providers.dados_de_mercado.httpx.get", _mock_get_for_html(MAIN_PAGE_HTML))

        result = provider.scrape_fundamentals("PETR4.SA")

        assert result["eps_history"][0] == pytest.approx(5.0)
        assert result["eps_history"][-1] == pytest.approx(3.0)

    def test_net_income_history_has_5_items(self, provider, monkeypatch):
        monkeypatch.setattr("app.providers.dados_de_mercado.httpx.get", _mock_get_for_html(MAIN_PAGE_HTML))

        result = provider.scrape_fundamentals("PETR4.SA")

        assert len(result["net_income_history"]) == 5

    def test_debt_history_has_5_items(self, provider, monkeypatch):
        monkeypatch.setattr("app.providers.dados_de_mercado.httpx.get", _mock_get_for_html(MAIN_PAGE_HTML))

        result = provider.scrape_fundamentals("PETR4.SA")

        assert len(result["debt_history"]) == 5

    def test_debt_history_is_ratio(self, provider, monkeypatch):
        monkeypatch.setattr("app.providers.dados_de_mercado.httpx.get", _mock_get_for_html(MAIN_PAGE_HTML))

        result = provider.scrape_fundamentals("PETR4.SA")

        # 100000 / 80000 = 1.25
        assert result["debt_history"][0] == pytest.approx(1.25)

    def test_current_net_debt_ebitda_is_not_none(self, provider, monkeypatch):
        monkeypatch.setattr("app.providers.dados_de_mercado.httpx.get", _mock_get_for_html(MAIN_PAGE_HTML))

        result = provider.scrape_fundamentals("PETR4.SA")

        assert result["current_net_debt_ebitda"] is not None
        assert result["current_net_debt_ebitda"] == pytest.approx(1.25)

    def test_ipo_years_from_data_span(self, provider, monkeypatch):
        monkeypatch.setattr("app.providers.dados_de_mercado.httpx.get", _mock_get_for_html(MAIN_PAGE_HTML))

        result = provider.scrape_fundamentals("PETR4.SA")

        assert result["ipo_years"] == 5

    def test_strips_sa_suffix_in_url(self, provider, monkeypatch):
        urls_called = []

        def mock_get(url, *args, **kwargs):
            urls_called.append(url)
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.text = MAIN_PAGE_HTML
            return mock_resp

        monkeypatch.setattr("app.providers.dados_de_mercado.httpx.get", mock_get)

        provider.scrape_fundamentals("PETR4.SA")

        assert len(urls_called) == 1
        assert ".SA" not in urls_called[0]
        assert "petr4" in urls_called[0].lower()

    def test_fetches_main_page_not_subpages(self, provider, monkeypatch):
        urls_called = []

        def mock_get(url, *args, **kwargs):
            urls_called.append(url)
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_resp.text = MAIN_PAGE_HTML
            return mock_resp

        monkeypatch.setattr("app.providers.dados_de_mercado.httpx.get", mock_get)

        provider.scrape_fundamentals("WEGE3.SA")

        assert len(urls_called) == 1
        assert urls_called[0].endswith("/acoes/wege3")

    def test_returns_empty_shape_on_error(self, provider, monkeypatch):
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("503 Service Unavailable")

        monkeypatch.setattr("app.providers.dados_de_mercado.httpx.get", lambda *a, **kw: mock_resp)

        result = provider.scrape_fundamentals("PETR4.SA")

        assert result["eps_history"] == []
        assert result["net_income_history"] == []
        assert result["debt_history"] == []

    def test_returns_empty_shape_when_no_tables(self, provider, monkeypatch):
        monkeypatch.setattr("app.providers.dados_de_mercado.httpx.get", _mock_get_for_html(MAIN_PAGE_NO_TABLES_HTML))

        result = provider.scrape_fundamentals("PETR4.SA")

        assert result["eps_history"] == []
        assert result["ipo_years"] is None

    def test_raw_data_has_entries(self, provider, monkeypatch):
        monkeypatch.setattr("app.providers.dados_de_mercado.httpx.get", _mock_get_for_html(MAIN_PAGE_HTML))

        result = provider.scrape_fundamentals("PETR4.SA")

        assert len(result["raw_data"]) == 5
        assert result["raw_data"][0]["year"] == 2024
        assert result["raw_data"][0]["eps"] == pytest.approx(5.0)


class TestParseValue:
    def test_simple_number(self):
        from app.providers.dados_de_mercado import _parse_value
        assert _parse_value("1,52") == pytest.approx(1.52)

    def test_millions_suffix(self):
        from app.providers.dados_de_mercado import _parse_value
        assert _parse_value("9.000 mi") == pytest.approx(9_000_000_000)

    def test_billions_suffix(self):
        from app.providers.dados_de_mercado import _parse_value
        assert _parse_value("6,78 B") == pytest.approx(6_780_000_000)

    def test_M_suffix(self):
        from app.providers.dados_de_mercado import _parse_value
        assert _parse_value("148,94 M") == pytest.approx(148_940_000)

    def test_negative_with_suffix(self):
        from app.providers.dados_de_mercado import _parse_value
        assert _parse_value("-2.690 mi") == pytest.approx(-2_690_000_000)

    def test_percentage(self):
        from app.providers.dados_de_mercado import _parse_value
        assert _parse_value("33,53%") == pytest.approx(0.3353)

    def test_dash_raises(self):
        from app.providers.dados_de_mercado import _parse_value
        with pytest.raises(ValueError):
            _parse_value("--")

    def test_star_prefix(self):
        from app.providers.dados_de_mercado import _parse_value
        assert _parse_value("* 1,52") == pytest.approx(1.52)
