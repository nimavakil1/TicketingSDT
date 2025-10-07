Preparation Phase - Historical Ticket Analysis

Goal
- Analyze existing tickets (by Amazon order number or ticket number) and generate:
  - A compact JSONL dataset for review
  - Aggregate stats (languages, counts)
  - A draft prompt with observed rules/templates

Inputs
- A text file with one ID per line, e.g.:
  304-3755348-6901123
  DE25006528
  302-4871157-8281966

Run
1) Ensure .env has valid ticketing API credentials.
2) From project root:
   python -m tools.prepare_ticket_prompt --input ids.txt --outdir config/preparation

Outputs
- config/preparation/dataset.jsonl – one JSON object per ticket with a compact conversation summary
- config/preparation/stats.json – aggregate counts
- config/preparation/prompt_suggestions.md – a draft operating prompt (AI-generated if keys present, otherwise heuristic)

Options
- --ids "id1,id2,..." – provide CSV instead of a file
- --no-ai – skip AI summarization and use a deterministic draft
- --max-details N – number of ticket history items to include per ticket (default 10)

Notes
- This phase does NOT read emails. It only uses the ticketing API.
- Gmail processing is unaffected.

