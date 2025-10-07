"""
Build an agent prompt and few-shot examples from the preparation dataset.

Usage:
  python -m tools.build_prompt_from_dataset --dataset config/preparation/dataset.jsonl --outdir config/prompt
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Dict, Any


def load_records(path: Path) -> List[Dict[str, Any]]:
    items = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except Exception:
                pass
    return items


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", required=True)
    ap.add_argument("--outdir", default="config/prompt")
    ap.add_argument("--max-examples", type=int, default=12)
    args = ap.parse_args()

    dataset = Path(args.dataset)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    records = load_records(dataset)
    few_shots = []
    for r in records[: args.max_examples]:
        ai = r.get("ai") or {}
        few_shots.append({
            "ticket_number": r.get("ticket_number"),
            "issue_type": ai.get("issue_type"),
            "facts": ai.get("key_facts"),
            "actions": ai.get("actions_taken"),
            "customer_template": ai.get("customer_template"),
            "supplier_template": ai.get("supplier_template"),
        })

    (outdir / "few_shots.json").write_text(json.dumps(few_shots, indent=2, ensure_ascii=False), encoding="utf-8")

    # Draft agent prompt that references examples
    lines = []
    lines.append("AI Support Agent – Operating Prompt")
    lines.append("")
    lines.append("Follow company rules in config/policies/rules.md.")
    lines.append("Always: identify language, be concise, action-oriented, log internal notes.")
    lines.append("")
    lines.append("Representative examples:")
    for ex in few_shots:
        facts = ex.get('facts') or []
        if isinstance(facts, list):
            facts_str = ", ".join(facts)
        else:
            facts_str = str(facts)
        lines.append(f"- Ticket {ex.get('ticket_number')}: {ex.get('issue_type')} – facts: {facts_str}")
    (outdir / "agent_prompt.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {outdir/'few_shots.json'} and {outdir/'agent_prompt.md'}")


if __name__ == "__main__":
    main()
