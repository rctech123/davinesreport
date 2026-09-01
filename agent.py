"""
The agent brain: given a natural-language question, a SQL schema summary, and
an Excel data summary, Claude decides whether to query SQL Server, look at the
Excel data, or both — then writes the final answer in plain language.

Uses Claude's tool-use (function-calling) feature.
"""

import json
import anthropic

MODEL = "claude-sonnet-4-6"

TOOLS = [
    {
        "name": "query_sql_server",
        "description": (
            "Run a read-only SELECT query against the SQL Server database to answer "
            "the user's question. Only use tables/columns from the provided schema."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "A single read-only SELECT statement."}
            },
            "required": ["sql"],
        },
    },
    {
        "name": "get_excel_sheet",
        "description": (
            "Retrieve the full contents of a named sheet from the uploaded Excel report "
            "so you can inspect and reason over it directly."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sheet_name": {"type": "string"}
            },
            "required": ["sheet_name"],
        },
    },
]


def build_system_prompt(sql_schema_summary: str, excel_summary: str) -> str:
    return f"""You are a data analyst assistant. You help the user answer questions using
two data sources:

1. A SQL Server database with this schema:
{sql_schema_summary}

2. Excel report data with this structure:
{excel_summary}

When you need data, use the provided tools rather than guessing values.
Prefer SQL for large/precise aggregations; use the Excel tool for anything specific
to the uploaded report. If a question needs both sources, use both tools before answering.
Always explain your answer in plain, concise language — don't just dump a table unless asked.
If you're not confident a question is answerable from these sources, say so plainly.
"""


def ask_agent(client: anthropic.Anthropic, question: str, sql_schema_summary: str,
              excel_summary: str, run_sql_fn, get_sheet_fn, history=None):
    """
    run_sql_fn(sql) -> pandas.DataFrame
    get_sheet_fn(sheet_name) -> pandas.DataFrame
    history: list of prior {"role": ..., "content": ...} turns (optional)
    Returns (answer_text, updated_history)
    """
    messages = list(history) if history else []
    messages.append({"role": "user", "content": question})

    system_prompt = build_system_prompt(sql_schema_summary, excel_summary)

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=2000,
            system=system_prompt,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            final_text = "".join(
                block.text for block in response.content if block.type == "text"
            )
            messages.append({"role": "assistant", "content": response.content})
            return final_text, messages

        # Handle tool calls
        messages.append({"role": "assistant", "content": response.content})
        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            try:
                if block.name == "query_sql_server":
                    df = run_sql_fn(block.input["sql"])
                    result_str = df.to_string(index=False) if not df.empty else "(no rows returned)"
                elif block.name == "get_excel_sheet":
                    df = get_sheet_fn(block.input["sheet_name"])
                    result_str = df.to_string(index=False)
                else:
                    result_str = f"Unknown tool: {block.name}"
            except Exception as e:
                result_str = f"Error: {e}"

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result_str[:8000],  # keep responses bounded
            })

        messages.append({"role": "user", "content": tool_results})
