# Freelance AI MVP Skeleton

Production-oriented MVP skeleton for a multi-platform freelance order aggregator with Telegram approvals.

## Features

- Plugin-ready platform integration architecture
- Freelancehunt placeholder scraper based on public pages (`httpx` + `BeautifulSoup`)
- Unified internal order model + SQLAlchemy SQLite persistence
- De-duplication by `(platform, external_id)`
- Rule-based analyzer and project scoring placeholders
- Telegram inline approval workflow (Approve/Reject)
- APScheduler polling job every N minutes

## Project structure

```text
freelance_ai/
  app/
    main.py
    config.py
    database.py
  core/
    models.py
    platform_registry.py
    analyzer.py
    scorer.py
    proposal_generator.py
  platforms/
    base.py
    freelancehunt/
      scraper.py
      parser.py
      __init__.py
    __init__.py
  bot/
    telegram_bot.py
    handlers.py
  services/
    order_service.py
    scheduler.py
  requirements.txt
  README.md
  .env.example
```

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r freelance_ai/requirements.txt
```

3. Copy env file and configure values:

```bash
cp freelance_ai/.env.example .env
```

4. Run:

```bash
python -m freelance_ai.app.main
```

## Configuration

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API token |
| `TELEGRAM_CHAT_ID` | Target chat/user/channel ID |
| `ENABLED_PLATFORMS` | Comma-separated platform names (`freelancehunt`) |
| `POLL_INTERVAL_MINUTES` | Fetch interval in minutes (default: 10) |
| `HOURLY_RATE_EUR` | Rate for price estimation (default: 15) |
| `DEFAULT_LANGUAGE` | Proposal language: `en` or `ua` |
| `DATABASE_URL` | SQLAlchemy URL (default: `sqlite:///./freelance_ai.db`) |

## Adding a new platform plugin

1. Create a folder under `freelance_ai/platforms/<platform_name>/`.
2. Implement a class inheriting `BasePlatform`:
   - `platform_name`
   - `async fetch_orders() -> list[dict]`
   - `parse(raw: dict) -> OrderIn`
3. Export it in `platforms/<platform_name>/__init__.py` and optionally `platforms/__init__.py`.
4. Register it in `core/platform_registry.py`.
5. Enable it via `ENABLED_PLATFORMS`.

## Notes

- The Freelancehunt scraper is intentionally fault-tolerant and returns an empty list on failures.
- No secrets are hardcoded.
- The project is ready for swapping analyzer logic with LLM-based analysis later.
