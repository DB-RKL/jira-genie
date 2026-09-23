# Diagram sources

Mermaid (`.mmd`) sources and rendered PNGs for the Jira Genie data model.

| File | Description |
|------|-------------|
| [jira_data_model_overview.mmd](jira_data_model_overview.mmd) / [.png](jira_data_model_overview.png) | Medallion layers: bronze → silver → gold → metrics → consumption |
| [jira_silver_er.mmd](jira_silver_er.mmd) / [.png](jira_silver_er.png) | Silver normalized Jira ERD |
| [jira_gold_star_schema.mmd](jira_gold_star_schema.mmd) / [.png](jira_gold_star_schema.png) | Gold facts, dimensions, and aggregates |

Regenerate PNGs after editing `.mmd` files:

```bash
./scripts/render_diagrams.sh
```

Full documentation: [../data-model.md](../data-model.md)
