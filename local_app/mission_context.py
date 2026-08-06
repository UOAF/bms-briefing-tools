from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .providers import ProviderRouter
from .skill_context import load_skill_prompt


def extract_json_object(text: str) -> dict[str, Any]:
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    raw = fenced.group(1) if fenced else text
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end < start:
        raise ValueError("No JSON object found in model response")
    return json.loads(raw[start : end + 1])


def parse_package_ids(text: str) -> list[int]:
    ids = []
    for item in re.split(r"[\s,;]+", text.strip()):
        if item.isdigit():
            ids.append(int(item))
    return ids


def fallback_context(form: dict[str, Any], planner_text: str) -> dict[str, Any]:
    package_ids = parse_package_ids(str(form.get("package_ids", "")))
    packages = [{"package_id": package_id} for package_id in package_ids]
    return {
        "source": "Local app planner intake",
        "event": str(form.get("event_number", "")).strip(),
        "operation_name": str(form.get("operation_name", "")).strip(),
        "campaign_prefix": str(form.get("prefix", "")).strip(),
        "deck_structure": "Treat listed player packages as one integrated player operation unless the planner says otherwise.",
        "packages": packages,
        "planner_notes_internal": planner_text.strip(),
    }


def build_context_with_llm(router: ProviderRouter, form: dict[str, Any], planner_text: str, provider: str = "auto") -> tuple[dict[str, Any], str]:
    if provider == "offline-template":
        return fallback_context(form, planner_text), "offline-template"
    system = (
        "You convert Falcon BMS mission-planner chat into the mission-context JSON schema used by "
        "the existing UOAF BMS briefing pipeline. Return JSON only. Preserve uncertainty as notes. "
        "Do not invent frequencies, TACAN, targets, or prior-mission facts.\n\n"
        "Relevant skill/workflow policy:\n"
        f"{load_skill_prompt()[:18000]}"
    )
    user = {
        "form_fields": form,
        "planner_text": planner_text,
        "schema_hint": {
            "source": "Local app planner intake",
            "event": "string",
            "operation_name": "string",
            "campaign_prefix": "string",
            "deck_structure": "string",
            "named_points": [{"label": "TIG", "name": "Tiger", "meaning": "what it means tactically"}],
            "packages": [
                {
                    "package_id": 1234,
                    "briefing_read": "planner interpretation",
                    "strike_contracts": [],
                    "sad_contracts": [],
                    "cap_contracts": [],
                    "target_opportunities": [],
                    "fallback_logic": "",
                }
            ],
            "commander_intent": "string",
            "comm_plan": {},
            "deconfliction": [],
            "map_mark_overrides": [],
            "map_flow_groups": [],
        },
    }
    try:
        result = router.chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user, indent=2)},
            ],
            requested=provider,
            temperature=0.1,
        )
        context = extract_json_object(result.text)
        if "packages" not in context or not isinstance(context.get("packages"), list):
            raise ValueError("Model response did not include mission-context packages")
        return context, result.provider
    except Exception:
        return fallback_context(form, planner_text), "offline-template"


def save_context(path: Path, context: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(context, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
