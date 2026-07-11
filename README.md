## Usage

Run the checker with `uv`:

```
uv run manuscript-checker
```

The script creates `manuscript_checker.sqlite3` in the project root if it does
not already exist.

Configuration is via environment variables:

- `MANUSCRIPT_ID`: manuscript UUID to check.
- `MANUSCRIPT_CHECKER_DB`: optional SQLite database path.
- `NTFY_TOPIC_PREFIX`: optional ntfy.sh topic prefix. Defaults to
  `paper-info-updates`, producing `paper-info-updates-$MANUSCRIPT_ID`.
- `LOG_LEVEL`: logging level. Defaults to `INFO`.

Example cron entry:

```
*/10 * * * * cd /path/to/manuscript-checker-cf && uv run manuscript-checker >> manuscript-checker.log 2>&1
```
