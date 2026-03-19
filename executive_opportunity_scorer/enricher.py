from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


def enrich_from_url(company_url: str, company_name: str = "") -> dict[str, Any]:
    """Fetch a company URL and use Claude to extract scoring-relevant fields.

    Returns a partial payload dict compatible with CompanyInput field names,
    or a dict with an ``error`` key if enrichment is unavailable.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {"error": "ANTHROPIC_API_KEY environment variable is not set."}

    try:
        import anthropic  # optional dependency
    except ImportError:
        return {"error": "anthropic package is not installed. Run: pip install anthropic"}

    page_content = _fetch_url(company_url)
    prompt = _build_prompt(company_url, company_name, page_content)

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return _parse_response(message.content[0].text.strip())


def _fetch_url(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible)"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode("utf-8", errors="ignore")[:6000]
    except (urllib.error.URLError, OSError):
        return ""


def _build_prompt(url: str, name: str, content: str) -> str:
    content_block = f"\nPage content (truncated):\n{content}" if content else "\n(Page content unavailable — infer from URL and company name if possible.)"
    return f"""You are helping a senior VP R&D candidate evaluate a company as a potential career move.

Company: {name or "(unknown)"}
URL: {url}{content_block}

Extract the following fields. Return ONLY valid JSON with no markdown or explanation:
{{
  "company_stage": "<one of: pre-seed, seed, series a, series b, series c, series d, growth, public — or empty string if unknown>",
  "team_size": <integer or null>,
  "current_engineering_leadership": ["<zero or more titles from exactly: Co-Founder & CTO, CTO, VP R&D, VP Engineering, Head of R&D, Head of Engineering>"],
  "source_urls_text": "<relevant Crunchbase / LinkedIn / news URLs on separate lines, or empty string>",
  "notes": "<2-3 sentence summary of the engineering leadership situation from a VP R&D candidate's perspective>"
}}"""


def _parse_response(text: str) -> dict[str, Any]:
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        return {"error": f"Could not parse AI response: {exc}", "raw": text}
