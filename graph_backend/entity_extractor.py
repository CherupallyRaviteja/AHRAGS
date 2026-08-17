from __future__ import annotations
import json
import logging
import re
from typing import Any, Dict, List, TypedDict
import requests
import config

logger = logging.getLogger(__name__)

ENTITY_TYPES = (
    "PERSON", "ORGANIZATION", "LOCATION", "TECHNOLOGY", "CONCEPT",
    "EVENT", "ACRONYM", "TOPIC",
)
GENERIC_ENTITY_NAMES = {
    "country",
    "countries",
    "organization",
    "organizations",
    "concept",
    "concepts",
    "location",
    "locations",
    "state",
    "states",
    "world",
    "people",
    "person",
    "industry",
    "industries",
    "company",
    "companies",
    "technology",
    "technologies",
    "event",
    "events",
    "topic",
    "topics",
}

class ExtractedEntity(TypedDict):
    name: str
    type: str


class ExtractedRelationship(TypedDict):
    source: str
    target: str
    relation: str


class ExtractionResult(TypedDict):
    entities: List[ExtractedEntity]
    relationships: List[ExtractedRelationship]


_EMPTY_RESULT: ExtractionResult = {"entities": [], "relationships": []}

_PROMPT_TEMPLATE = """You are an information extraction engine.

Extract ONLY information explicitly present in the TEXT.

Entity types: {entity_types}

Relationship rules:
- Use short, generic relationship names.
- Use uppercase relationship names.
- Maximum 3 words.
- Examples: USES, RELATED_TO, PART_OF, USED_FOR, LOCATED_IN, TEACHES, WORKS_AT.
- Do not create long descriptive relationship names.
- Do not invent entities or relationships.


Generic Entity Rules:
- DO NOT extract generic category words or labels as entities.
- Do NOT extract generic terms such as: {GENERIC_ENTITY_NAMES}.

Return ONLY valid JSON in exactly this format:

{{
  "entities": [{{"name": "...", "type": "..."}}],
  "relationships": [{{"source": "...", "target": "...", "relation": "..."}}]
}}

Examples-1:
TEXT: "Solar panels convert sunlight into electricity."
        VALID:
        {{
        "entities": [
            {{"name": "Solar panels", "type": "TECHNOLOGY"}},
            {{"name": "sunlight", "type": "CONCEPT"}},
            {{"name": "electricity", "type": "CONCEPT"}}
        ],
        "relationships": [
            {{"source": "Solar panels", "target": "electricity", "relation": "PRODUCES"}}
        ]
        }}
Examples-2:
TEXT: "India has strong potential for renewable energy."
    VALID:
    {{
    "entities": [
        {{"name": "India", "type": "LOCATION"}},
        {{"name": "renewable energy", "type": "CONCEPT"}}
    ],
    "relationships": []
    }}

If no entities or relationships are found, return {{"entities": [], "relationships": []}}.

TEXT:
{text}

JSON:
"""


def _build_prompt(text: str) -> str:
    return _PROMPT_TEMPLATE.format(entity_types=", ".join(ENTITY_TYPES), GENERIC_ENTITY_NAMES=", ".join(GENERIC_ENTITY_NAMES), text=text)


def _extract_json_block(raw: str) -> str:
    """Best-effort isolation of the JSON object from a chatty LLM response."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?", "", raw).strip()
    raw = re.sub(r"```$", "", raw).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end < start:
        return raw
    return raw[start : end + 1]


def _normalize_result(parsed: Dict[str, Any]) -> ExtractionResult:
    entities: List[ExtractedEntity] = []
    for item in parsed.get("entities", []) or []:
        name = str(item.get("name", "")).strip()
        etype = str(item.get("type", "CONCEPT")).strip().upper() or "CONCEPT"
        if name:
            entities.append({"name": name, "type": etype})

    relationships: List[ExtractedRelationship] = []
    for item in parsed.get("relationships", []) or []:
        source = str(item.get("source", "")).strip()
        target = str(item.get("target", "")).strip()
        relation = str(item.get("relation", "RELATED_TO")).strip().upper().replace(" ", "_") or "RELATED_TO"
        if source and target:
            relationships.append({"source": source, "target": target, "relation": relation})

    return {"entities": entities, "relationships": relationships}


def extract_entities_relationships(text: str) -> ExtractionResult:
    """
    Extract entities and relationships from a chunk of text using the
    configured Ollama model (config.ENTITY_EXTRACTION_MODEL).

    Fails soft: on any error (timeout, malformed JSON, connection refused)
    this returns an empty result instead of raising, so a single bad chunk
    or an offline LLM never breaks document ingestion
    (blueprint Section 4.14).
    """
    if not text or not text.strip():
        return dict(_EMPTY_RESULT)

    body = {
        "model": config.ENTITY_EXTRACTION_MODEL,
        "prompt": _build_prompt(text),
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }

    try:
        response = requests.post(
            f"{config.OLLAMA_URL}/api/generate",
            json=body,
            timeout=config.ENTITY_EXTRACTION_TIMEOUT,
        )
        response.raise_for_status()
        raw_text = response.json().get("response", "")
        json_block = _extract_json_block(raw_text)
        parsed = json.loads(json_block)
        result = _normalize_result(parsed)
        logger.debug(
            "Extracted %d entities, %d relationships",
            len(result["entities"]), len(result["relationships"]),
        )
        return result
    except json.JSONDecodeError as exc:
        logger.warning("Entity extraction returned non-JSON output: %s", exc)
        return dict(_EMPTY_RESULT)
    except requests.RequestException as exc:
        logger.warning("Entity extraction request to Ollama failed: %s", exc)
        return dict(_EMPTY_RESULT)
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error during entity extraction: %s", exc)
        return dict(_EMPTY_RESULT)


if __name__ == "__main__":
    sample = "FastAPI uses Pydantic for data validation and integrates with Uvicorn as its ASGI server."
    print(json.dumps(extract_entities_relationships(sample), indent=2))
