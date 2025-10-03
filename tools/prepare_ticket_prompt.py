"""
Preparation Phase Tool
Reads historical tickets from the ticketing API (using a list of
Amazon order numbers or ticket numbers) and produces:

- A JSONL dataset with compact conversation summaries per ticket
- Aggregate stats (languages, intents as detected heuristically)
- A prompt_suggestions.md draft (optionally AI-generated if keys present)

Usage examples:
  python -m tools.prepare_ticket_prompt --input ids.txt --outdir config/preparation
  python -m tools.prepare_ticket_prompt --ids 304-1234567-1234567,DE25006528

Input file format:
  - One ID per line
  - ID can be an Amazon order number (123-1234567-1234567)
    or a ticket number (e.g., DE25006528)
  - Lines starting with '#' are ignored
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import structlog

from config.settings import settings
from src.api.ticketing_client import TicketingAPIClient, TicketingAPIError
from src.ai.language_detector import LanguageDetector

logger = structlog.get_logger(__name__)


ORDER_RE = re.compile(r"^\d{3}-\d{7}-\d{7}$")
TICKET_RE = re.compile(r"^[A-Z]{2}\d{8}$")


def parse_ids(input_path: Optional[Path], ids_csv: Optional[str]) -> List[str]:
    ids: List[str] = []
    if input_path and input_path.exists():
        for line in input_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # allow CSV columns like order_number,ticket_number
            parts = [p.strip() for p in re.split(r"[,;]", line) if p.strip()]
            for p in parts:
                ids.append(p)
    if ids_csv:
        ids.extend([s.strip() for s in re.split(r"[,;]", ids_csv) if s.strip()])
    # Deduplicate keeping order
    seen = set()
    unique: List[str] = []
    for i in ids:
        if i not in seen:
            seen.add(i)
            unique.append(i)
    return unique


def detect_id_type(value: str) -> str:
    if ORDER_RE.match(value):
        return "order"
    if TICKET_RE.match(value):
        return "ticket"
    # fallback heuristic: digits with dashes -> order
    if re.match(r"^\d{3}-\d{7}-\d{7}$", value):
        return "order"
    return "ticket"


def compact_ticket_summary(ticket: Dict[str, Any], max_items: int = 10) -> str:
    """Create a compact, plain-text summary from ticketDetails.
    Falls back gracefully if fields are missing.
    """
    lines: List[str] = []
    details = ticket.get("ticketDetails") or []
    for d in details[-max_items:]:
        sender = d.get("receiverEmailAddress") or d.get("sender") or "System"
        comment = (d.get("comment") or "").strip()
        if not comment:
            continue
        comment = comment.replace("\r", " ").replace("\n", " ")
        lines.append(f"[{sender}] {comment[:400]}")
    return "\n".join(lines)


def build_prompt_from_stats(stats: Dict[str, Any], examples: List[Dict[str, Any]]) -> str:
    """Build a deterministic prompt draft without external AI.
    If you want an AI-written prompt, run with --use-ai and valid keys.
    """
    lines: List[str] = []
    lines.append("AI Support Agent – Operating Instructions (Draft)")
    lines.append("")
    lines.append("Scope: Amazon order support tickets. Respond in the customer's language.")
    lines.append("Always be concise, polite, and action-oriented.")
    lines.append("")
    lines.append("Observed patterns:")
    for k, v in (stats.get("intents", {}) or {}).items():
        lines.append(f"- {k}: {v} examples")
    if stats.get("languages"):
        lines.append("- Languages seen: " + ", ".join(f"{k}({v})" for k, v in stats["languages"].items()))
    lines.append("")
    lines.append("General policy:")
    lines.append("- Verify order number and map to ticket.")
    lines.append("- Summarize customer ask; check prior history in ticket.")
    lines.append("- If refund requested and evidence supports it: propose refund workflow.")
    lines.append("- If tracking requested: provide tracking info or contact supplier.")
    lines.append("- If return label required: send label or escalate.")
    lines.append("- Log every step as internal note in Phase 1.")
    lines.append("")
    lines.append("Representative examples (truncated):")
    for ex in examples[:5]:
        lines.append(f"- Ticket {ex.get('ticket_number','?')}: {ex.get('summary','')[:300]}")
    return "\n".join(lines)


def try_ai_prompt(examples: List[Dict[str, Any]]) -> Optional[str]:
    """Optionally use configured AI provider to draft a prompt."""
    try:
        from src.ai.ai_engine import AIEngine
        engine = AIEngine()
        joined = "\n\n".join(
            f"Ticket {e.get('ticket_number','?')}:\n{e.get('summary','')}" for e in examples[:20]
        )
        prompt = (
            "You are to write an operating prompt for an AI support agent. "
            "Summarize consistent policies and steps the human agents took across these tickets, "
            "and output a clear prompt with bullet rules and 3 short example responses.\n\n"
            + joined
        )
        text = engine.provider.generate_response(prompt, temperature=0.2)
        return text
    except Exception as e:
        logger.warning("AI prompt generation skipped", error=str(e))
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description="Preparation: analyze historical tickets")
    ap.add_argument("--input", type=str, help="File with IDs (one per line)")
    ap.add_argument("--ids", type=str, help="Comma-separated IDs", default="")
    ap.add_argument("--outdir", type=str, default="config/preparation")
    ap.add_argument("--max-details", type=int, default=10)
    ap.add_argument("--no-ai", action="store_true", help="Do not call AI to generate prompt")
    args = ap.parse_args()

    input_path = Path(args.input) if args.input else None
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    ids = parse_ids(input_path, args.ids)
    if not ids:
        logger.error("No IDs provided. Use --input or --ids.")
        raise SystemExit(2)

    client = TicketingAPIClient()
    langdet = LanguageDetector()

    dataset_path = outdir / "dataset.jsonl"
    stats_path = outdir / "stats.json"
    prompt_path = outdir / "prompt_suggestions.md"

    stats = {
        "total": 0,
        "languages": {},
        "intents": {},  # heuristic placeholder; not inferred without domain labels
        "by_type": {"order": 0, "ticket": 0},
    }
    examples: List[Dict[str, Any]] = []

    with dataset_path.open("w", encoding="utf-8") as fw:
        for raw_id in ids:
            id_type = detect_id_type(raw_id)
            stats["by_type"][id_type] += 1

            try:
                if id_type == "order":
                    tickets = client.get_ticket_by_amazon_order_number(raw_id)
                else:
                    tickets = client.get_ticket_by_ticket_number(raw_id)

                if not tickets:
                    logger.warning("No ticket found", id=raw_id, id_type=id_type)
                    continue

                # Use the first ticket returned
                ticket = tickets[0]
                summary = compact_ticket_summary(ticket, max_items=args.max_details)
                lang = langdet.detect_language(summary) if summary else "en-US"

                stats["total"] += 1
                stats["languages"][lang] = stats["languages"].get(lang, 0) + 1

                record = {
                    "input_id": raw_id,
                    "id_type": id_type,
                    "ticket_number": ticket.get("ticketNumber"),
                    "order_number": ticket.get("salesOrder", {}).get("orderNumber"),
                    "ticket_status_id": ticket.get("ticketStatusId"),
                    "owner_id": ticket.get("ownerId"),
                    "language": lang,
                    "summary": summary,
                }
                fw.write(json.dumps(record, ensure_ascii=False) + "\n")
                examples.append(record)

            except TicketingAPIError as e:
                logger.error("Ticketing API error for id", id=raw_id, error=str(e))
            except Exception as e:
                logger.error("Unexpected error for id", id=raw_id, error=str(e))

    stats_path.write_text(json.dumps(stats, indent=2))

    # Build prompt suggestions
    final_prompt: Optional[str] = None
    if not args.no_ai:
        final_prompt = try_ai_prompt(examples)
    if not final_prompt:
        final_prompt = build_prompt_from_stats(stats, examples)
    prompt_path.write_text(final_prompt)

    logger.info(
        "Preparation results written",
        dataset=str(dataset_path),
        stats=str(stats_path),
        prompt=str(prompt_path),
        count=stats["total"],
    )


if __name__ == "__main__":
    main()

