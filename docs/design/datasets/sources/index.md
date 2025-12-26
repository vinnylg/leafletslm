# Sources Design

<!-- TODO(!documentation): Document additional data sources
     Plan integration with other pharmaceutical databases (FDA, EMA).
     Document selection criteria for data sources.
     labels: documentation, data-sources -->

This section documents the design of data acquisition modules. Each source has its own scraping strategy, rate limiting considerations, and data validation rules.

## 🌐 Available Sources

| Source | Region | Data Type | Status |
|:-------|:-------|:----------|:-------|
| [ANVISA](anvisa/index.md) | Brazil | Drug leaflets, registrations | Active |

<!-- TODO(!documentation): Add FDA data source design
     US pharmaceutical database integration.
     labels: documentation, data-sources -->

<!-- TODO(!documentation): Add EMA data source design  
     European pharmaceutical database integration.
     labels: documentation, data-sources -->

## 🔧 Common Patterns

All source modules follow these design principles:

1. **Idempotent scraping** - Re-running produces same results
2. **Incremental updates** - Only fetch new/changed data
3. **Checkpoint persistence** - Resume from failure points
4. **Rate limiting** - Respect source server constraints

---

> **See also:** [API Reference - Sources](../../../reference/datasets/sources/index.md) for implementation details.
