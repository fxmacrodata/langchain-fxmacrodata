"""Public FXMacroData HTTP requests. No third-party client."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

API_ORIGIN = "https://api.fxmacrodata.com"
MAX_BODY = 2_000_000

# method, OpenAPI path, query names. Path fields are the {placeholders}.
OPERATIONS: tuple[tuple[str, str, str], ...] = (
    ("GET", "/v1/announcements/changes", "currencies indicators since limit payload strict_cursor"),
    ("GET", "/v1/announcements/{currency}/latest", ""),
    ("GET", "/v1/announcements/{currency}/{indicator}", "start_date end_date series_mode limit offset page seasonality frequency annualization period_aggregation revisions basis base date_basis official_only fields as_of availability dataset_version value_mode"),
    ("GET", "/v1/calendar/{currency}", "indicator start_date end_date timezone"),
    ("GET", "/v1/calendar/{currency}/coverage", "start_date end_date as_of"),
    ("GET", "/v1/calendar/{currency}/events/{archive_event_id}/versions", "checkpoint cursor limit"),
    ("GET", "/v1/calendar/{currency}/snapshot", "as_of start_date end_date importance event_kind knowledge_mode checkpoint cursor limit"),
    ("GET", "/v1/commodities/latest", ""),
    ("GET", "/v1/commodities/{indicator}", "start_date end_date limit offset page"),
    ("GET", "/v1/cot/{currency}", "start_date end_date limit offset page report"),
    ("GET", "/v1/curves/{currency}", "curve_family metric view method date as_of availability max_staleness_days require_common_date"),
    ("GET", "/v1/data_catalogue/{currency}", "include_capabilities include_coverage include_analytics indicator"),
    ("GET", "/v1/factors/{currency}/{factor}", "start_date end_date include_components include_sources limit offset"),
    ("GET", "/v1/financial_prices/{currency}", "source start_date end_date measure instrument_id issuer limit offset"),
    ("GET", "/v1/forex/{base}/{quote}", "start_date end_date limit offset page indicators dataset_version"),
    ("GET", "/v1/fx/intraday-reference-rates/{base}/{quote}", "start_time end_time"),
    ("GET", "/v1/fx/reference-rates/{base}/{quote}", "date start_date end_date source timestamp_type native_only include_source_legs order limit offset page dataset_version"),
    ("GET", "/v1/fx/session-rates/{base}/{quote}", "session date start_date end_date order limit offset page dataset_version"),
    ("GET", "/v1/fx/source-universe", "currency source"),
    ("GET", "/v1/fx/sources", ""),
    ("GET", "/v1/health", ""),
    ("GET", "/v1/market_sessions", "at"),
    ("GET", "/v1/native", ""),
    ("GET", "/v1/native/{source}", "year measure holder_country_code ownership_basis maturity account_type region product limit offset order"),
    ("GET", "/v1/organisations", "q category limit"),
    ("GET", "/v1/organisations/{slug}", ""),
    ("GET", "/v1/ping", ""),
    ("GET", "/v1/positioning", ""),
    ("GET", "/v1/positioning/{instrument}", "report start_date end_date limit offset"),
    ("GET", "/v1/predictions/coverage", ""),
    ("GET", "/v1/predictions/coverage/{currency}", ""),
    ("GET", "/v1/predictions/{currency}", "prediction_source prediction_class statistic respondent_population start_date end_date variable target_period publication_precision before_id limit"),
    ("GET", "/v1/predictions/{currency}/{indicator}", "prediction_class prediction_type prediction_source official_limit pre_release_only seasonality frequency annualization period_aggregation basis start_date end_date limit offset page before_date as_of event_compatible_only"),
    ("GET", "/v1/press-releases/{currency}", "limit offset"),
    ("GET", "/v1/rate_differentials/{base}/{quote}", "measure rate_type curve_family start_tenor_years end_tenor_years start_date end_date limit offset as_of availability"),
    ("POST", "/v1/research/panel", ""),
    ("GET", "/v1/risk_sentiment", "start_date end_date limit offset"),
    ("GET", "/v1/risk_sentiment/changes", "after_sequence limit"),
    ("GET", "/v1/settlement/contracts", ""),
    ("GET", "/v1/settlement/contracts/{contract_id}", "period strike comparison currency"),
    ("GET", "/v1/settlement/keys", ""),
    ("GET", "/v1/settlement/{currency}/{indicator}", "period announcement_id strike comparison decimals"),
    ("GET", "/v1/stream/events", "currencies indicators payload live_only max_age_ms"),
)


class FXMacroDataError(RuntimeError):
    pass


def path_fields(template: str) -> tuple[str, ...]:
    fields = []
    start = 0
    while True:
        left = template.find("{", start)
        if left < 0:
            return tuple(fields)
        right = template.find("}", left)
        if right < 0:
            raise FXMacroDataError("broken path template")
        fields.append(template[left + 1 : right])
        start = right + 1


def build_url(template: str, query_names: str, values: dict[str, str], origin: str = API_ORIGIN) -> str:
    parsed = urllib.parse.urlsplit(origin)
    if parsed.scheme != "https" or parsed.netloc != "api.fxmacrodata.com" or parsed.path not in {"", "/"}:
        raise FXMacroDataError("requests stay on https://api.fxmacrodata.com")
    path = template
    for name in path_fields(template):
        value = values.get(name, "")
        if not value:
            raise FXMacroDataError(f"missing {name}")
        path = path.replace("{" + name + "}", urllib.parse.quote(value, safe=""))
    if "{" in path or "}" in path:
        raise FXMacroDataError("unfilled path")
    query = []
    for name in query_names.split():
        value = values.get(name, "")
        if value:
            query.append((name, value))
    return urllib.parse.urlunsplit(("https", "api.fxmacrodata.com", path, urllib.parse.urlencode(query), ""))


def _opener() -> urllib.request.OpenerDirector:
    class _NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
            raise FXMacroDataError("redirect refused")

    return urllib.request.build_opener(_NoRedirect)


def request(
    method: str,
    url: str,
    api_key: str | None = None,
    timeout: float = 30,
    extra_headers: dict[str, str] | None = None,
    json_body: dict | None = None,
) -> tuple[int, str]:
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != "https" or parsed.netloc != "api.fxmacrodata.com":
        raise FXMacroDataError("requests stay on https://api.fxmacrodata.com")
    if parsed.username or parsed.password or parsed.fragment:
        raise FXMacroDataError("invalid API URL")
    if any(name.lower() in {"api_key", "x-api-key", "authorization"}
           for name, _ in urllib.parse.parse_qsl(parsed.query)):
        raise FXMacroDataError("API key must not be placed in the URL")
    if method == "POST":
        if parsed.path != "/v1/research/panel" or parsed.query or json_body is None:
            raise FXMacroDataError("POST requires a research panel JSON body")
    elif method != "GET" or json_body is not None:
        raise FXMacroDataError("unsupported method or body")
    headers = {"Accept": "application/json", "User-Agent": "langchain-fxmacrodata/0.1"}
    for name, value in (extra_headers or {}).items():
        if name.lower() in {"x-api-key", "authorization", "host"}:
            raise FXMacroDataError("that header is reserved")
        if value:
            headers[name] = value
    if api_key:
        headers["X-API-Key"] = api_key
    data = None
    if json_body is not None:
        data = json.dumps(json_body, allow_nan=False).encode("utf-8")
        if len(data) > MAX_BODY:
            raise FXMacroDataError("request exceeds 2 MB")
        headers["Content-Type"] = "application/json"
    call = urllib.request.Request(url, headers=headers, data=data, method=method)
    try:
        with _opener().open(call, timeout=timeout) as response:
            status = getattr(response, "status", 200)
            body = response.read(MAX_BODY + 1)
    except urllib.error.HTTPError as exc:
        status = exc.code
        body = exc.read(MAX_BODY + 1)
    except FXMacroDataError:
        raise
    except urllib.error.URLError as exc:
        raise FXMacroDataError("request failed") from exc
    if len(body) > MAX_BODY:
        raise FXMacroDataError("response exceeds 2 MB")
    return status, body.decode("utf-8")


def call_operation(template: str, query_names: str, values: dict, transport=None, *, json_transport=None) -> str:
    if template == "/v1/research/panel":
        from langchain_fxmacrodata.schemas import ResearchPanelRequest

        payload = ResearchPanelRequest.model_validate(values).model_dump(mode="json", exclude_unset=True)
        url = build_url(template, "", {})
        key = os.environ.get("FXMACRODATA_API_KEY", "").strip() or None
        if json_transport is None:
            status, body = request("POST", url, key, json_body=payload)
        else:
            status, body = json_transport("POST", url, key, payload)
        return body if status == 200 else json.dumps({"status": status, "body": body}, ensure_ascii=False)
    url = build_url(template, query_names, values)
    key = os.environ.get("FXMACRODATA_API_KEY", "").strip() or None
    if "api_key=" in url:
        raise FXMacroDataError("API key must not be placed in the URL")
    extra = {}
    if template == "/v1/stream/events" and values.get("last_event_id"):
        extra["Last-Event-ID"] = values["last_event_id"]
    if transport is None:
        status, body = request("GET", url, key, extra_headers=extra)
    else:
        status, body = transport("GET", url, key)
    if status == 200:
        return body
    return json.dumps({"status": status, "body": body}, ensure_ascii=False)
