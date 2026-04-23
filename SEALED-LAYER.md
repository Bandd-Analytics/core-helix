---
aliases: [Sealed Layer, Helix Sealed]
tags: [charter, helix, confidentiality]
---

# Helix Sealed Layer

> [!warning] Top-secret content. Read before contributing.
> Nothing in `helix/sealed/` is tracked by git, synced to Supabase, or visible to cloud LLMs. This is by design.

## What goes in `sealed/`

Only the narrow layer that constitutes actual IP:

- Validated profitable parameter sets (entry z-score thresholds, ADX cutoffs, correlation ceilings that *work*)
- Pair-specific tuned values that outperform defaults
- Live PnL data from funded accounts
- Proven edge thresholds and their walk-forward validation
- Backtest reports from validated strategies with real numbers

## What does NOT go in `sealed/`

Everything else is in the **open** layer (fully AI-collaborative):

- Architecture, infrastructure (ZMQ bridge, risk framework, logging, backtest harness)
- Generic strategy descriptions, pre-validation experiments
- Indicator code, statistical helpers, data pipelines
- Testing frameworks, CI configuration
- Exploratory research, shelved ideas, failed attempts

## Why this split exists

The IP is not the architecture — infrastructure like ZMQ bridges, correlation matrices, and Kelly sizing are commoditized. The IP is **which specific parameter combinations on which instruments actually work**. Protect that narrow layer; everything else is fair game for AI collaboration.

## Enforcement

Four layers of protection, all automatic:

1. **Git**: `sealed/*` is gitignored in `helix/.gitignore` except `.gitkeep`. Sealed content cannot be committed.
2. **Vault → Supabase sync**: [[Worklog-Sync]] `vault_rag.py` skips any path containing `/sealed/` when embedding.
3. **Worklog commit messages**: Any commit message containing the marker `[SEALED]` is redacted to `[SEALED commit — message redacted]` in the worklog pipeline.
4. **Vault gitignore**: If you author a sealed note in the Obsidian vault, put it under a folder named `sealed/` — vault gitignore excludes these from the private GitHub backup.

## AI tier rule

When working with Helix in any form:

- **API only**: Claude Code, OpenRouter API (zero-retention tiers)
- **Never**: consumer claude.ai web chat, chatgpt.com, Gemini web, any free tier with undeclared training policy

See [[CHARTER#5. Confidentiality Rules]] for the full rule.

## Creating sealed content

```bash
# From helix/ root
mkdir -p sealed/parameters sealed/pnl sealed/validated
# Write your sealed .md, .csv, .json files inside these folders
# They will NOT be tracked by git (see .gitignore)
```

If you need to reference a sealed fact from an open note, reference it by name only — never paste the value:

- ✅ `See sealed/parameters/usdjpy-swing.md for tuned Z threshold`
- ❌ `Tuned Z threshold for USDJPY swing: 2.3`

## Related

- [[CHARTER]] — master confidentiality rules
- [[helix/V2/docs/shelved_features|Shelved features]] — open-layer, documents what was tried and rejected
- [[Worklog-Sync]] — tooling that enforces sealed exclusion
