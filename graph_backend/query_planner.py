from __future__ import annotations
import logging
import re
import requests
import config

logger = logging.getLogger(__name__)

_DEFAULT_QUERY_TYPE = "fact_lookup"

_PROMPT_TEMPLATE = """Classify the QUESTION below into exactly one of these categories:
{types}

Definitions:
- fact_lookup: asks for a single fact or definition.
- relationship_lookup: asks how two or more things are connected/related.
- multi_hop: requires following a chain of connections across multiple entities.
- comparison: asks to compare two or more things.
- summary: asks for an overview or summary of a topic/document.
- recommendation: asks for a suggestion or recommendation.

Reply with ONLY the category name, nothing else.

QUESTION:
{query}

CATEGORY:
"""

def _build_prompt(query: str) -> str:
    return _PROMPT_TEMPLATE.format(types=", ".join(config.QUERY_TYPES), query=query)


def _extract_type(raw: str) -> str:
    raw = raw.strip().lower()
    for qtype in config.QUERY_TYPES:
        if qtype in raw:
            return qtype
    # Fallback: try to match the first alphabetic token against known types.
    match = re.search(r"[a-z_]+", raw)
    if match and match.group(0) in config.QUERY_TYPES:
        return match.group(0)
    return _DEFAULT_QUERY_TYPE


def classify_query(query: str) -> str:
    """
    Classify a query into one of config.QUERY_TYPES.

    Fails soft to "fact_lookup" (the safest default — routes to the
    existing, proven vector+keyword path) on any error, so the graph
    routing layer never blocks a response if the LLM call fails.
    """
    if not query or not query.strip():
        return _DEFAULT_QUERY_TYPE

    body = {
        "model": config.MODEL,
        "prompt": _build_prompt(query),
        "stream": False,
        "options": {"temperature": 0},
    }

    try:
        response = requests.post(f"{config.OLLAMA_URL}/api/generate", json=body, timeout=30)
        response.raise_for_status()
        raw = response.json().get("response", "")
        qtype = _extract_type(raw)
        logger.debug("Query '%s' classified as '%s'", query, qtype)
        return qtype
    except requests.RequestException as exc:
        logger.warning("Query classification request failed, defaulting to '%s': %s", _DEFAULT_QUERY_TYPE, exc)
        return _DEFAULT_QUERY_TYPE
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error during query classification: %s", exc)
        return _DEFAULT_QUERY_TYPE


def should_use_graph(query_type: str) -> bool:
    """True if this query type should be routed through the graph retriever
    in addition to the existing vector+keyword retriever (blueprint 4.4)."""
    return query_type in config.GRAPH_ROUTED_QUERY_TYPES


if __name__ == "__main__":
    while True:
        q = input("Query: ")
        qtype = classify_query(q)
        print(f"Type: {qtype} | Graph routed: {should_use_graph(qtype)}")
