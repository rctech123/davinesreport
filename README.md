# Chat With Your Reports

A local chat agent that answers natural-language questions using your SQL Server
database and your Excel reports, powered by Claude.

## How it works

You type a question ("What were total sales by region last quarter?"). Claude looks
at your database schema and your Excel report's structure, decides whether it needs
to query SQL Server, read the Excel data, or both, and then answers in plain language.

## Prep checklist

1. **Install Python 3.10+** if you don't have it.
2. **Install the SQL Server ODBC driver** (Driver 17 or 18) — required for the database
   connection to work at all:
   - Windows: usually already present, or download from Microsoft's site.
   - Mac: `brew install msodbcsql18`
   - Linux: see Microsoft's ODBC driver install docs for your distro.
3. **Get a read-only SQL Server login.** Ask your DBA for a login limited to `SELECT`
   on the relevant database/tables. The app also blocks any non-SELECT query in code,
   but a read-only login is the real safety net.
4. **Get an Anthropic API key** from https://console.anthropic.com/settings/keys.
5. **Have your Excel report file ready** (.xlsx) — you'll upload it in the app itself,
   no prep needed beyond having it on hand.

## Setup

```bash
cd data-chat-agent
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# edit .env and fill in your real ANTHROPIC_API_KEY and SQL_* values
```

## Run

```bash
streamlit run app.py
```

This opens a browser tab with the chat interface. Upload your Excel report in the
sidebar, and if your `.env` SQL settings are correct you'll see "Connected to SQL Server."
Then just start asking questions.

## Notes on safety & scope

- Every SQL query the agent generates is checked in code (`db.py`) to ensure it's a
  single, read-only `SELECT` statement before it's ever run — anything else is rejected.
- You can restrict which tables the agent even knows about via `SQL_ALLOWED_TABLES`
  in `.env` (comma-separated table names). Leave blank to expose everything your login
  can see.
- Query results are capped at 500 rows per query to keep responses fast and affordable.
- This app runs entirely on your machine — the only external calls are to your SQL
  Server and to the Anthropic API (for the chat reasoning itself).

## Extending this later

- **Multiple Excel files at once**: extend the sidebar uploader to accept multiple files.
- **Scheduled/auto-generated reports**: this scaffold is built for interactive Q&A;
  ping me if you want it turned into a scheduled report generator instead.
- **Deploying for a team**: Streamlit apps can be hosted (e.g. Streamlit Community Cloud,
  or an internal server) so others can use it via URL instead of running it locally —
  just be extra careful about who gets access to a tool with database credentials.
