"""
Loads one or more Excel report files into pandas DataFrames and produces
a text summary (columns + dtypes + sample rows) the AI can reason over.
"""

import pandas as pd


def load_excel(file) -> dict[str, pd.DataFrame]:
    """Loads all sheets from an uploaded Excel file. Returns {sheet_name: DataFrame}."""
    sheets = pd.read_excel(file, sheet_name=None)
    return sheets


def summarize_sheets(sheets: dict[str, pd.DataFrame]) -> str:
    lines = []
    for name, df in sheets.items():
        col_desc = ", ".join(f"{c} ({df[c].dtype})" for c in df.columns)
        lines.append(f"Sheet '{name}' — {len(df)} rows. Columns: {col_desc}")
        lines.append(f"Sample rows:\n{df.head(3).to_string(index=False)}")
    return "\n\n".join(lines)


def query_sheet(sheets: dict[str, pd.DataFrame], sheet_name: str, pandas_expr: str):
    """
    Runs a restricted pandas query against a loaded sheet.
    pandas_expr is expected to be a `.query()`-style filter string, e.g. "Region == 'West'".
    For anything more complex the AI is instructed to just request the full sheet and reason over it directly.
    """
    df = sheets[sheet_name]
    if not pandas_expr:
        return df
    return df.query(pandas_expr)
