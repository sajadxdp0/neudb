# neuDB documentation

neuDB 0.5.0 is inspectable embedded Python storage for local tools, prototypes, and LLM-agent memory. The core has zero dependencies and requires Python 3.11 or newer.

| Resource | Location |
|----------|----------|
| Product README and installation | [`../README.md`](../README.md) |
| Product scope and interfaces | [`PRODUCT.md`](PRODUCT.md) |
| CLI reference | [`cli.md`](cli.md) |
| HTTP API reference | [`api.md`](api.md) |
| Architecture | [`architecture.md`](architecture.md) |
| Storage and durability | [`storage.md`](storage.md) |
| Recovery | [`recovery.md`](recovery.md) |
| Concurrency | [`concurrency.md`](concurrency.md) |
| Search and embeddings | [`search.md`](search.md) |
| Engineering decisions | [`decisions.md`](decisions.md) |
| Reproducible benchmark protocol | [`performance.md`](performance.md) |
| Brand assets | [`brand/`](brand/) |
| Archived launch demo | [`launch-video/`](launch-video/) |
| Coding-assistant demo | [`../demos/realworld_coding_assistant.py`](../demos/realworld_coding_assistant.py) |
| Website source | [`../website/`](../website/) |
| Changelog | [`../CHANGELOG.md`](../CHANGELOG.md) |
| Contributing | [`../CONTRIBUTING.md`](../CONTRIBUTING.md) |
| Security policy | [`../SECURITY.md`](../SECURITY.md) |

The library, CLI, API, and agent share the same table engine. They do not provide indexes, transactions, automatic backups, or multi-process locking.