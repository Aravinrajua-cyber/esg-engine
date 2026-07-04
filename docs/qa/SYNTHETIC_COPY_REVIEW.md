# Synthetic Copy And Unsupported-Claims Review

## Scope

Reviewed visible frontend copy, report-generation copy, demo script, and support docs for synthetic-data labelling and unsupported investment claims.

## Findings

- The frontend source includes the exact persistent banner string `SYNTHETIC DEMONSTRATION DATA`.
- The frontend footer includes `Research demonstration - not investment advice.`.
- The report builder repeatedly labels current figures and statistics as synthetic demonstration outputs.
- The demo script explicitly says the prototype does not identify real winners, predict returns, or constitute investment advice.
- Placeholder copy remains in frontend risks/footer and report citations; this is labelled as placeholder prose for Claude to replace.

## Claims To Avoid Until Live Validation Exists

- Do not claim real issuer rankings are valid.
- Do not claim the synthetic backtest proves alpha.
- Do not use buy, sell, hold, outperform, underperform, or target-price language.
- Do not imply Yahoo coverage failures mean companies are delisted.
- Do not present synthetic scores as live ESG scores.

## Open Copy Item

If live mode is introduced, the frontend should show a visible live-mode tag with retrieval date and should keep a separate not-investment-advice disclaimer.
