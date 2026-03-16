from datetime import date
from unittest.mock import MagicMock, patch

from app.providers.dados_de_mercado import DadosDeMercadoProvider, DividendRecord


SAMPLE_HTML = """
<html><body>
<table>
<thead><tr><th>Tipo</th><th>Valor</th><th>Data Com</th><th>Data Ex</th><th>Pagamento</th></tr></thead>
<tbody>
<tr><td>Dividendo</td><td>0,752895</td><td>22/10/2025</td><td>23/10/2025</td><td>28/11/2025</td></tr>
<tr><td>JCP</td><td>1,234567</td><td>15/06/2025</td><td>16/06/2025</td><td>—</td></tr>
</tbody>
</table>
</body></html>
"""


class TestDadosDeMercadoProvider:
    def test_scrape_dividends_parses_html_table(self):
        provider = DadosDeMercadoProvider()

        mock_resp = MagicMock()
        mock_resp.text = SAMPLE_HTML
        mock_resp.raise_for_status = MagicMock()

        with patch("app.providers.dados_de_mercado.httpx.get", return_value=mock_resp):
            results = provider.scrape_dividends("AGRO3.SA")

        assert len(results) == 2

        assert results[0].dividend_type == "Dividendo"
        assert results[0].value == 0.752895
        assert results[0].record_date == date(2025, 10, 22)
        assert results[0].ex_date == date(2025, 10, 23)
        assert results[0].payment_date == date(2025, 11, 28)

        assert results[1].dividend_type == "JCP"
        assert results[1].value == 1.234567
        assert results[1].payment_date is None

    def test_strips_sa_suffix_in_url(self):
        provider = DadosDeMercadoProvider()

        mock_resp = MagicMock()
        mock_resp.text = "<html><body><table><thead><tr><th>Tipo</th><th>Valor</th><th>Data Com</th><th>Data Ex</th><th>Pagamento</th></tr></thead><tbody></tbody></table></body></html>"
        mock_resp.raise_for_status = MagicMock()

        with patch("app.providers.dados_de_mercado.httpx.get", return_value=mock_resp) as mock_get:
            provider.scrape_dividends("PETR4.SA")

        call_url = mock_get.call_args[0][0]
        assert "petr4" in call_url.lower()
        assert ".SA" not in call_url
        assert "/dividendos" in call_url

    def test_handles_http_error(self):
        provider = DadosDeMercadoProvider()

        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = Exception("404 Not Found")

        with patch("app.providers.dados_de_mercado.httpx.get", return_value=mock_resp):
            results = provider.scrape_dividends("INVALID.SA")

        assert results == []

    def test_handles_empty_table(self):
        provider = DadosDeMercadoProvider()

        mock_resp = MagicMock()
        mock_resp.text = "<html><body><table><thead><tr><th>Tipo</th><th>Valor</th><th>Data Com</th><th>Data Ex</th><th>Pagamento</th></tr></thead><tbody></tbody></table></body></html>"
        mock_resp.raise_for_status = MagicMock()

        with patch("app.providers.dados_de_mercado.httpx.get", return_value=mock_resp):
            results = provider.scrape_dividends("AGRO3.SA")

        assert results == []


class TestDividendRecord:
    def test_dataclass_fields(self):
        record = DividendRecord(
            dividend_type="Dividendo",
            value=1.50,
            record_date=date(2025, 10, 22),
            ex_date=date(2025, 10, 23),
            payment_date=date(2025, 11, 28),
        )
        assert record.dividend_type == "Dividendo"
        assert record.value == 1.50
        assert record.payment_date == date(2025, 11, 28)

    def test_payment_date_optional(self):
        record = DividendRecord(
            dividend_type="JCP",
            value=0.75,
            record_date=date(2025, 6, 15),
            ex_date=date(2025, 6, 16),
            payment_date=None,
        )
        assert record.payment_date is None
