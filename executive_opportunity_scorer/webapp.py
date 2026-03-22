from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from urllib.parse import urlparse

from .engine import score_company, score_to_dict
from .models import CompanyInput
from . import storage
from . import enricher

PACKAGE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PACKAGE_ROOT.parent
WEB_ROOT = PACKAGE_ROOT / "web"
UI_SPEC_PATH = PROJECT_ROOT / "data" / "ui_spec" / "company_form.json"
DEMO_SAMPLE_PATH = PROJECT_ROOT / "data" / "samples" / "series_b_growth.json"


class WebAppError(Exception):
    """Raised when a web request payload is invalid."""


def load_ui_spec() -> dict[str, Any]:
    return json.loads(UI_SPEC_PATH.read_text())


def build_template_from_spec(spec: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {"evidence": {}}
    for section in spec.get("sections", []):
        for field in section.get("fields", []):
            payload[field["id"]] = _default_value(field)
            evidence_key = field.get("evidence_key")
            if evidence_key:
                payload["evidence"][evidence_key] = []
    return payload


def coerce_submission(spec: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    normalized = build_template_from_spec(spec)
    evidence_payload = payload.get("evidence", {})
    evidence_fields = spec.get("evidence_entry", {}).get("fields", [])

    for section in spec.get("sections", []):
        for field in section.get("fields", []):
            field_id = field["id"]
            raw_value = payload.get(field_id, _default_value(field))
            normalized[field_id] = _coerce_value(field, raw_value)

            if field.get("required") and normalized[field_id] in (None, ""):
                raise WebAppError(f"Field `{field_id}` is required.")

            evidence_key = field.get("evidence_key")
            if evidence_key:
                normalized["evidence"][evidence_key] = _normalize_evidence_items(
                    evidence_payload.get(evidence_key, []),
                    evidence_fields,
                    evidence_key,
                )

    if "current_engineering_leadership" in normalized:
        normalized["existing_exec_layer"] = _derive_exec_layer(
            normalized["current_engineering_leadership"]
        )

    return normalized


def _default_value(field: dict[str, Any]) -> Any:
    if field.get("id") == "snapshot_date":
        return datetime.now().isoformat(timespec="seconds")
    return field.get("default")


def _coerce_value(field: dict[str, Any], raw_value: Any) -> Any:
    field_type = field.get("type")

    if raw_value == "":
        return None if field_type in {"number", "select", "date"} else ""

    if raw_value is None:
        return None

    if field_type == "number":
        if isinstance(raw_value, (int, float)):
            return raw_value
        text = str(raw_value).strip()
        if text == "":
            return None
        return float(text) if "." in text else int(text)

    if field_type == "boolean":
        if isinstance(raw_value, bool):
            return raw_value
        lowered = str(raw_value).strip().lower()
        if lowered in {"true", "1", "yes"}:
            return True
        if lowered in {"false", "0", "no"}:
            return False
        return None

    if field_type == "multiselect":
        if raw_value is None:
            return []
        if isinstance(raw_value, list):
            return [str(value) for value in raw_value]
        text = str(raw_value).strip()
        if not text:
            return []
        return [item.strip() for item in text.split(",") if item.strip()]

    return raw_value


def _derive_exec_layer(roles: Any) -> str | None:
    if not roles:
        return "none"
    selected = {str(role).strip() for role in roles if str(role).strip()}
    if not selected:
        return "none"
    has_founder_cto = "Co-Founder & CTO" in selected
    has_cto = "CTO" in selected
    has_vp_or_head = bool(selected & {"VP R&D", "VP Engineering", "Head of R&D", "Head of Engineering"})
    if has_cto:
        return "strong"
    if has_founder_cto and has_vp_or_head:
        return "strong"
    if has_founder_cto or has_vp_or_head:
        return "partial"
    return "none"


def _normalize_evidence_items(items: list[dict[str, Any]], field_defs: list[dict[str, Any]], evidence_key: str) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    required_fields = {field["id"] for field in field_defs if field.get("required")}
    for item in items:
        if not any(str(value).strip() for value in item.values() if value is not None):
            continue
        missing_required = [
            field_id
            for field_id in required_fields
            if not str(item.get(field_id, "")).strip()
        ]
        if missing_required:
            raise WebAppError(
                f"Evidence for `{evidence_key}` is missing required fields: {', '.join(sorted(missing_required))}."
            )
        normalized.append(
            {
                "source_type": item.get("source_type", "").strip(),
                "label": item.get("label", "").strip(),
                "url": item.get("url", "").strip(),
                "observed_at": item.get("observed_at") or "",
                "published_at": item.get("published_at") or None,
                "note": item.get("note", "").strip(),
            }
        )
    return normalized


class ScorerRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path in {"/", "/index.html"}:
            self._serve_file("index.html", "text/html; charset=utf-8")
            return
        if path == "/app.js":
            self._serve_file("app.js", "application/javascript; charset=utf-8")
            return
        if path == "/styles.css":
            self._serve_file("styles.css", "text/css; charset=utf-8")
            return
        if path == "/api/ui-spec":
            self._send_json(HTTPStatus.OK, load_ui_spec())
            return
        if path == "/api/template":
            spec = load_ui_spec()
            self._send_json(HTTPStatus.OK, build_template_from_spec(spec))
            return
        if path == "/api/demo":
            self._send_json(HTTPStatus.OK, json.loads(DEMO_SAMPLE_PATH.read_text()))
            return
        if path == "/api/pipeline":
            self._send_json(HTTPStatus.OK, {"entries": storage.list_pipeline()})
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8")
            payload = json.loads(body or "{}")
        except json.JSONDecodeError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Request body must be valid JSON."})
            return

        req_path = urlparse(self.path).path
        if req_path == "/api/score":
            self._handle_score(payload)
            return
        if req_path == "/api/pipeline":
            self._handle_pipeline_save(payload)
            return
        if req_path == "/api/enrich":
            self._handle_enrich(payload)
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def do_DELETE(self) -> None:  # noqa: N802
        del_path = urlparse(self.path).path
        if del_path.startswith("/api/pipeline/"):
            id_str = del_path[len("/api/pipeline/"):]
            try:
                entry_id = int(id_str)
            except ValueError:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid pipeline entry id."})
                return
            deleted = storage.delete_entry(entry_id)
            if deleted:
                self._send_json(HTTPStatus.OK, {"deleted": entry_id})
            else:
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "Entry not found."})
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def _handle_score(self, payload: dict[str, Any]) -> None:
        try:
            spec = load_ui_spec()
            normalized = coerce_submission(spec, payload)
            result = score_company(CompanyInput.from_dict(normalized))
            self._send_json(
                HTTPStatus.OK,
                {
                    "input": normalized,
                    "result": score_to_dict(result),
                },
            )
        except WebAppError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except ValueError as exc:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})

    def _handle_pipeline_save(self, payload: dict[str, Any]) -> None:
        result = payload.get("result")
        input_data = payload.get("input")
        if not result or not result.get("company_name"):
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Missing result or company_name."})
            return
        entry_id = storage.save_result(result, input_data)
        self._send_json(HTTPStatus.OK, {"id": entry_id, "saved": True})

    def _handle_enrich(self, payload: dict[str, Any]) -> None:
        company_url = payload.get("company_url", "").strip()
        company_name = payload.get("company_name", "").strip()
        if not company_url:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "company_url is required."})
            return
        parsed = urlparse(company_url)
        if parsed.scheme not in {"http", "https"}:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "company_url must use http or https."})
            return
        result = enricher.enrich_from_url(company_url, company_name)
        if "error" in result:
            self._send_json(HTTPStatus.BAD_REQUEST, result)
        else:
            self._send_json(HTTPStatus.OK, result)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def _serve_file(self, filename: str, content_type: str) -> None:
        path = WEB_ROOT / filename
        if not path.exists():
            self._send_json(HTTPStatus.NOT_FOUND, {"error": f"Missing asset: {filename}"})
            return
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    storage.init_db()
    server = ThreadingHTTPServer((host, port), ScorerRequestHandler)
    print(f"Executive Opportunity Scorer running at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
