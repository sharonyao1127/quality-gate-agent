# Knowledge Store Lite

Quality Gate Agent includes a lightweight local knowledge store for reusable risk patterns.

It is intentionally simple:

- YAML files under `knowledge/risk_patterns/`
- domain filters such as `payment`, `ads`, and `logistics`
- keyword/signal retrieval
- generated knowledge context for downstream analysis
- Markdown report output for review

## Why Not Vector DB First?

For a public portfolio project, the first goal is to show clear domain modeling and deterministic retrieval. A vector database can be added later when there is enough private historical data, incident notes, or customer-specific knowledge to justify semantic retrieval.

This design keeps the public repository safe:

- No confidential incident data.
- No customer-specific rules.
- No production credentials or connectors.
- Easy upgrade path to RAG.

## Run

```bash
python3 -m src.main \
  --input examples/prd/payment_callback_prd.md \
  --input-type prd \
  --business-domain payment
```

Generated files include:

- `outputs/knowledge_report.md`
- `outputs/gate_result.json` with `knowledge_retrieval`

## Pattern Shape

```yaml
patterns:
  - id: payment_async_callback_idempotency
    domain: payment
    name: Payment callback idempotency and final-state overwrite
    signals:
      - callback
      - provider
      - timeout
    risks:
      - Duplicated callbacks can update the same transaction multiple times.
    recommended_checks:
      - Verify duplicated callbacks are idempotent.
```
