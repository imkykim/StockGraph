"""
LLM extractor — production mode.
Requires ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable.
"""
from __future__ import annotations
import json
import os
import re
import sys

from schema.models import Chunk
from pipeline.extract.base import ExtractionResult, RawCompany, RawRelation
from prompts.extraction_prompt import SYSTEM_PROMPT, build_user_message


def _safe_json(text: str) -> dict:
    """Strip markdown code fences and parse JSON."""
    text = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text.strip(), flags=re.MULTILINE)
    return json.loads(text)


def _call_anthropic(messages: list[dict], api_key: str) -> str:
    import anthropic
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=messages,
    )
    return response.content[0].text


def _call_openai(messages: list[dict], api_key: str, base_url: str | None = None) -> str:
    from openai import OpenAI
    client = OpenAI(api_key=api_key, base_url=base_url)
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    model = "Qwen3-32B"
    extra = {"enable_thinking": False} if "Qwen3" in model else {}
    response = client.chat.completions.create(
        model=model,
        messages=full_messages,
        max_tokens=2048,
        response_format={"type": "json_object"},
        extra_body=extra,
    )
    return response.choices[0].message.content


def _extract_chunk(chunk: Chunk, caller) -> tuple[list[RawCompany], list[RawRelation]]:
    user_msg = build_user_message(chunk.chunk_id, chunk.week, chunk.text)
    messages = [{"role": "user", "content": user_msg}]
    try:
        raw_text = caller(messages)
        data = _safe_json(raw_text)
    except Exception as e:
        print(f"  [warn] chunk {chunk.chunk_id}: {e}", file=sys.stderr)
        return [], []

    raw_companies = data.get("companies", [])
    companies = [
        RawCompany(surface=c if isinstance(c, str) else c["surface"])
        for c in raw_companies
    ]
    relations = []
    for r in data.get("relations", []):
        try:
            relations.append(RawRelation(
                source_surface=r["source_surface"],
                target_surface=r["target_surface"],
                relation_type=r["relation_type"],
                what_flows=r.get("what_flows"),
                quantity=r.get("quantity"),
                unit=r.get("unit"),
                confidence=float(r.get("confidence", 1.0)),
                evidence=r.get("evidence", ""),
                source_chunk_ids=[chunk.chunk_id],
            ))
        except (KeyError, TypeError, ValueError) as e:
            print(f"  [warn] bad relation in {chunk.chunk_id}: {e}", file=sys.stderr)
    return companies, relations


class LLMExtractor:
    def __init__(self):
        api_key = os.environ.get("API_KEY")
        base_url = os.environ.get("BASE_URL")
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        openai_key = os.environ.get("OPENAI_API_KEY")

        if api_key and base_url:
            print(f"Using custom API: {base_url}", file=sys.stderr)
            self._caller = lambda msgs: _call_openai(msgs, api_key, base_url=base_url)
        elif anthropic_key:
            print("Using Anthropic API", file=sys.stderr)
            self._caller = lambda msgs: _call_anthropic(msgs, anthropic_key)
        elif openai_key:
            print("Using OpenAI API", file=sys.stderr)
            self._caller = lambda msgs: _call_openai(msgs, openai_key)
        else:
            print(
                "ERROR: No API key found.\n"
                "Set API_KEY + BASE_URL (or ANTHROPIC_API_KEY / OPENAI_API_KEY).\n"
                "For demo/testing, use --extractor seed instead.",
                file=sys.stderr,
            )
            sys.exit(1)

    def extract(self, chunks: list[Chunk]) -> ExtractionResult:
        all_companies: list[RawCompany] = []
        all_relations: list[RawRelation] = []

        for i, chunk in enumerate(chunks):
            print(f"  [{i+1}/{len(chunks)}] {chunk.chunk_id}", file=sys.stderr)
            companies, relations = _extract_chunk(chunk, self._caller)
            all_companies.extend(companies)
            all_relations.extend(relations)

        return ExtractionResult(companies=all_companies, relations=all_relations)
