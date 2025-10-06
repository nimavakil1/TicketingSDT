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
from src.ai.ai_engine import AIEngine

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


def normalize(raw: str) -> str:
    s = (raw or "").strip().upper()
    # collapse whitespace
    s = re.sub(r"\s+", " ", s)
    return s


AMAZON_ANY_RE = re.compile(r"\b\d{3}-\d{7}-\d{7}\b")
TICKET_ANY_RE = re.compile(r"\b(?:DE|FR|BE|LU|NL|AT|IT)\d{8}\b")
PO_ANY_RE = re.compile(r"\b(?:[DFBLNAI])4\d{2}\d{6}\b")
SO_ANY_RE = re.compile(r"\b(?:[DFBLNAI])3\d{2}-\d{6}\b")


def extract_candidates(raw: str) -> Dict[str, List[str]]:
    s = normalize(raw)
    candidates = {"amazon": [], "ticket": [], "purchase": [], "sales": []}

    # Amazon base
    m = AMAZON_ANY_RE.search(s)
    if m:
        base = m.group(0)
        variants = [base, f"{base}_X", f"{base}-X"]
        # Also if original included a variant form, keep it — variants already cover both
        candidates["amazon"] = list(dict.fromkeys(variants))

    # Ticket
    candidates["ticket"] = list(dict.fromkeys(TICKET_ANY_RE.findall(s)))

    # Purchase order
    candidates["purchase"] = list(dict.fromkeys(PO_ANY_RE.findall(s)))

    # Sales order
    candidates["sales"] = list(dict.fromkeys(SO_ANY_RE.findall(s)))

    return candidates


def parse_ticket_number(ticket_number: str) -> tuple:
    """Return (yy:int, seq:int) for ticket numbers like DE25xxxxxx; fallback (-1,-1)."""
    if not ticket_number:
        return (-1, -1)
    m = re.match(r"^(DE|FR|BE|LU|NL|AT|IT)(\d{2})(\d{6})$", ticket_number)
    if not m:
        return (-1, -1)
    try:
        yy = int(m.group(2))
        seq = int(m.group(3))
        return (yy, seq)
    except Exception:
        return (-1, -1)


def choose_latest_ticket(tickets: List[Dict[str, Any]]) -> tuple[Optional[Dict[str, Any]], List[str]]:
    """From a list of ticket dicts, choose the latest by ticket_number semantics.
    Returns (chosen_ticket, related_ticket_numbers)."""
    if not tickets:
        return None, []
    by_num: Dict[str, Dict[str, Any]] = {}
    for t in tickets:
        tn = t.get("ticketNumber")
        if tn:
            by_num[tn] = t
    uniq = list(by_num.values())
    if not uniq:
        return tickets[0], []
    uniq.sort(key=lambda t: parse_ticket_number(t.get("ticketNumber")), reverse=True)
    chosen = uniq[0]
    related = [t.get("ticketNumber") for t in uniq[1:] if t.get("ticketNumber")]
    return chosen, related


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


def _parse_ai_json(text: str) -> Dict[str, Any]:
    if not text:
        return {}
    # Strip code fences and extract JSON object
    lines = [ln for ln in text.splitlines() if not ln.strip().startswith("```")]
    body = "\n".join(lines)
    i, j = body.find("{"), body.rfind("}")
    if i != -1 and j != -1 and j > i:
        try:
            return json.loads(body[i:j+1])
        except Exception:
            return {}
    return {}


def main() -> None:
    ap = argparse.ArgumentParser(description="Preparation: analyze historical tickets")
    ap.add_argument("--input", type=str, help="File with IDs (one per line)")
    ap.add_argument("--ids", type=str, help="Comma-separated IDs", default="")
    ap.add_argument("--outdir", type=str, default="config/preparation")
    ap.add_argument("--max-details", type=int, default=10)
    ap.add_argument("--no-ai", action="store_true", help="Do not call AI to generate prompt or per-ticket JSON")
    ap.add_argument("--limit", type=int, default=0, help="Process only first N IDs (0 = all)")
    ap.add_argument("--model", type=str, default="", help="Override AI model during preparation")
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
    engine = None if args.no_ai else AIEngine()
    if engine and args.model:
        try:
            engine.provider.model = args.model  # type: ignore[attr-defined]
        except Exception:
            pass

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
        processed = 0
        for raw_id in ids:
            if args.limit and processed >= args.limit:
                break

            try:
                cands = extract_candidates(raw_id)
                resolved_type = "unknown"
                gathered: List[Dict[str, Any]] = []

                # Amazon first: try base and suffix variants (_X and -X)
                amazon = cands.get("amazon") or []
                if amazon:
                    resolved_type = "order"
                    tried = []
                    for aid in amazon:
                        tried.append(aid)
                        tk = client.get_ticket_by_amazon_order_number(aid)
                        if tk:
                            gathered.extend(tk)
                    if not gathered:
                        logger.warning("amazon_not_found", id=raw_id, tried=tried)

                # Ticket fallback
                if not gathered and (cands.get("ticket") or []):
                    resolved_type = "ticket"
                    for tn in cands["ticket"]:
                        tk = client.get_ticket_by_ticket_number(tn)
                        if tk:
                            gathered.extend(tk)
                    if gathered:
                        logger.info("fallback_ticket_match", id=raw_id, count=len(gathered))

                # Purchase order fallback
                if not gathered and (cands.get("purchase") or []):
                    resolved_type = "purchase_order"
                    for po in cands["purchase"]:
                        tk = client.get_ticket_by_purchase_order_number(po)
                        if tk:
                            gathered.extend(tk)
                    if gathered:
                        logger.info("fallback_purchase_match", id=raw_id, count=len(gathered))

                if not gathered:
                    logger.warning("No ticket found", id=raw_id, id_type=resolved_type)
                    continue

                # Choose latest, keep related
                ticket, related = choose_latest_ticket(gathered)
                if not ticket:
                    logger.warning("No ticket chosen after gather", id=raw_id)
                    continue

                summary = compact_ticket_summary(ticket, max_items=args.max_details)
                lang = langdet.detect_language(summary) if summary else "en-US"

                stats["total"] += 1
                stats["languages"][lang] = stats["languages"].get(lang, 0) + 1

                # Build AI JSON via provider (best effort)
                ai_json: Dict[str, Any] = {}
                if engine is not None:
                    try:
                        supplier_name = (
                            (ticket.get("salesOrder") or {}).get("purchaseOrders", [{}])[0].get("supplierName", "")
                            if (ticket.get("salesOrder") or {}).get("purchaseOrders") else ""
                        )
                        prompt = (
                            "You are the seller's support agent at Distri-Smart. You never write as the customer.\n"
                            "Return STRICT JSON only (no code fences), with keys: \n"
                            "  issue_type, customer_intent, key_facts, actions_taken, outcome, missing_info, recommended_rule, customer_template, supplier_template, language.\n\n"
                            f"Ticket number: {ticket.get('ticketNumber')}\n"
                            f"Detected customer language: {lang}\n"
                            f"Supplier (internal context only): {supplier_name or 'unknown'}\n\n"
                            "Conversation (latest, compact):\n"
                            f"{summary}\n\n"
                            "Guidelines:\n"
                            "- customer_template: This is OUR message to the customer in the detected language. Use a polite, concise style (German: formal 'Sie'). 2–5 sentences.\n"
                            "  Do NOT pretend to be the customer. Do NOT ask the customer for a proof of delivery.\n"
                            "  If proof of delivery is relevant, say: 'wir haben unsere Logistikabteilung um einen Abliefernachweis gebeten und würden Sie informieren, sobald wir mehr erfahren.'.\n"
                            "  NEVER mention any supplier name to the customer. Mentioning the carrier (e.g., DHL/UPS) is allowed if known.\n"
                            "  Ask the customer only for items listed in missing_info (if any).\n"
                            "- supplier_template: Our message to the supplier in the supplier language; 2–4 sentences; include the concrete ask (e.g., PoD, RMA, reship) and order/ticket number if available.\n"
                            "- key_facts: an array of short strings; actions_taken: short strings describing what already happened.\n"
                            "- language: use the detected customer language code.\n"
                        )
                        text = engine.provider.generate_response(prompt, temperature=0.2) or ""
                        ai_json = _parse_ai_json(text)
                        if not isinstance(ai_json, dict):
                            ai_json = {}
                        if "language" not in ai_json:
                            ai_json["language"] = lang
                        logger.info("AI summary generated", ok=bool(ai_json))
                    except Exception as e:
                        logger.warning("AI summary failed; continuing", error=str(e))

                record = {
                    "input_id": raw_id,
                    "id_type": resolved_type,
                    "ticket_number": ticket.get("ticketNumber"),
                    "order_number": (ticket.get("salesOrder", {}) or {}).get("orderNumber"),
                    "ticket_status_id": ticket.get("ticketStatusId"),
                    "owner_id": ticket.get("OwnerId") or ticket.get("ownerId"),
                    "language": lang,
                    "summary": summary,
                    "ai": ai_json,
                }
                if related:
                    record["related_tickets"] = related

                fw.write(json.dumps(record, ensure_ascii=False) + "\n")
                examples.append(record)
                processed += 1

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
