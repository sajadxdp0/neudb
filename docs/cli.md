# neuDB CLI

The `neudb` command exposes the same JSON table engine as the Python library. Install from a GitHub checkout first; see the [README installation guide](../README.md#install-from-source).

## Global options

```text
neudb [--db DIR] [--json] [--version] COMMAND …
```

| Option | Behavior |
|--------|----------|
| `--db DIR` | Database directory. Defaults to `NEUDB_DB`, then `neudb_data`. |
| `--json` | Emit one JSON document instead of human-readable output or JSON Lines. |
| `--version` | Print the neuDB version and exit. |

Global options must appear before `table` or `row`. `python -m neudb` is equivalent to `neudb`.

List commands emit JSON Lines by default and a JSON array with `--json`. Other commands emit their documented object or status value. Records are strict JSON objects with immutable string IDs.

## Table commands

### Create a table

```bash
neudb --db ./neudb_data table create notes
```

Table names contain 1–128 ASCII letters, numbers, or underscores. Creation is silent at the library level and returns a boolean; the CLI reports whether the table was created or already existed.

### List tables

```bash
neudb --db ./neudb_data --json table list
```

### Drop a table

```bash
neudb --db ./neudb_data table drop notes --yes
```

`--yes` is required. Dropping a table deletes its JSON file; there is no recycle bin or backup.

## Row commands

All row commands take a table name immediately after the action.

### Insert

```bash
neudb --db ./neudb_data --json row insert notes \
  --data '{"title":"Python setup","done":false}'
```

`--data` must be a JSON object. If `id` is omitted, neuDB generates one. Supplying an existing ID replaces that record.

### List with pagination

```bash
neudb --db ./neudb_data row list notes --limit 10 --offset 0
neudb --db ./neudb_data --json row list notes --limit 10 --offset 0
```

`--limit` must be positive. `--offset` must be non-negative. Pagination slices the in-memory result after the full table is loaded; it does not make the underlying read partial.

### Get one record

```bash
neudb --db ./neudb_data --json row get notes --id note-1
```

A missing record is an error.

### Find by field equality

```bash
neudb --db ./neudb_data --json row find notes \
  --where done=false --limit 10 --offset 0
```

`--where` uses `field=value`. Both sides are trimmed, and the value is passed as a string. Equality is typed, so `done=false` matches the string `"false"`, not the boolean `false`; use the Python library for typed non-string filters. Missing fields never match.

### Update

```bash
neudb --db ./neudb_data --json row update notes \
  --id note-1 --data '{"done":true}'
```

Updates merge fields into an existing record. The `id` field cannot be changed. The command fails if the record does not exist.

### Delete

```bash
neudb --db ./neudb_data --json row delete notes --id note-1
```

The command fails if the record does not exist.

### Vector search

```bash
neudb --db ./neudb_data --json row search notes \
  --field embedding \
  --vector '[0.12, 0.84, -0.31]' \
  --top-k 5
```

`--vector` must be a JSON array of finite numbers. neuDB scans the table and returns records ordered by cosine similarity. Records with missing, invalid, or differently sized vectors are skipped. No similarity scores or vector index are provided.

### Text search

```bash
neudb --db ./neudb_data --json row search-text notes \
  --field title --query python --top-k 5
```

Text search is a case-insensitive substring scan, not ranked full-text search. The field value is converted to text for matching. An empty query returns no records.

## Complete example

```bash
neudb --db ./neudb_data table create notes
neudb --db ./neudb_data --json row insert notes \
  --data '{"title":"Local memory","embedding":[0.12,0.84,-0.31]}'
neudb --db ./neudb_data row list notes
neudb --db ./neudb_data row search-text notes --field title --query local
neudb --db ./neudb_data row search notes \
  --field embedding --vector '[0.1,0.8,-0.3]'
neudb --db ./neudb_data table list
```

Run only one writer process against a database directory. The CLI has no multi-process lock, transactions, indexes, or automatic backups. See [concurrency](../docs/concurrency.md) and [storage](../docs/storage.md).
