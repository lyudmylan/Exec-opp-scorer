from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = "gpt-5-mini"
ROLE_OPTIONS = [
    "Co-Founder & CTO",
    "CTO",
    "VP R&D",
    "VP Engineering",
    "Head of R&D",
    "Head of Engineering",
]
STAGE_OPTIONS = [
    "",
    "pre-seed",
    "seed",
    "series a",
    "series b",
    "series c",
    "series d",
    "growth",
    "public",
]


def enrich_from_url(company_url: str, company_name: str = "") -> dict[str, Any]:
    """Fetch a company URL and use OpenAI to extract scoring-relevant fields."""
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return {"error": "OPENAI_API_KEY environment variable is not set."}

    page_content = _fetch_url(company_url)
    prompt = _build_prompt(company_url, company_name, page_content)

    try:
        response = _call_openai(prompt, api_key)
        return _parse_response(_extract_completion_text(response))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return {"error": f"OpenAI API error: {exc}"}


def _fetch_url(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible)"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8", errors="ignore")[:6000]
    except (urllib.error.URLError, OSError):
        return ""


def _call_openai(prompt: str, api_key: str) -> dict[str, Any]:
    body = json.dumps(
        {
            "model": OPENAI_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Extract structured company signals for executive-opportunity triage. "
                        "Return only data that fits the schema. Use empty strings, empty arrays, "
                        "or null when the signal is unknown."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "company_enrichment",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "company_stage": {
                                "type": "string",
                                "enum": STAGE_OPTIONS,
                            },
                            "team_size": {
                                "type": ["integer", "null"],
                            },
                            "current_engineering_leadership": {
                                "type": "array",
                                "items": {
                                    "type": "string",
                                    "enum": ROLE_OPTIONS,
                                },
                            },
                            "source_urls_text": {
                                "type": "string",
                            },
                            "research_notes": {
                                "type": "string",
                            },
                        },
                        "required": [
                            "company_stage",
                            "team_size",
                            "current_engineering_leadership",
                            "source_urls_text",
                            "research_notes",
                        ],
                    },
                },
            },
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        OPENAI_API_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if "error" in payload:
        message = payload["error"].get("message", "Unknown error")
        raise ValueError(message)
    return payload


def _extract_completion_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        raise ValueError("No choices returned from OpenAI.")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if item.get("type") in {"text", "output_text"} and item.get("text"):
                text_parts.append(item["text"])
        if text_parts:
            return "\n".join(text_parts)
    raise ValueError("OpenAI response did not include text content.")


def _build_prompt(url: str, name: str, content: str) -> str:
    content_block = (
        f"\nPage content (truncated):\n{content}"
        if content
        else "\n(Page content unavailable — infer conservatively from the URL and company name only.)"
    )
    return f"""You are helping a senior VP R&D candidate evaluate a company as a potential career move.

Company: {name or "(unknown)"}
URL: {url}{content_block}

Extract the following fields. Use the exact allowed title values and keep the funding stage lowercase.
If a field is unknown, return an empty string, empty array, or null.
- company_stage: one of {", ".join(option or '""' for option in STAGE_OPTIONS)}
- team_size: integer or null
- current_engineering_leadership: zero or more titles from {", ".join(ROLE_OPTIONS)}
- source_urls_text: relevant public URLs on separate lines, or an empty string if none are evident
- research_notes: a concise 2-3 sentence summary of the leadership situation from a VP R&D candidate's perspective
"""


def _parse_response(text: str) -> dict[str, Any]:
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        return {"error": f"Could not parse AI response: {exc}", "raw": text}
