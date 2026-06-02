import os
import pandas as pd
from typing import Any
from langchain_core.tools import tool

#TODO: Add notifications at the end of tools, so we can appeal to them 


# Transformation dictionary and functions

def _tak_nie(val: Any) -> Any:
    """Konwertuje 'tak'/'nie' na 1/0."""
    if pd.isna(val) or str(val).strip() == "":
        return ""
    v = str(val).strip().lower()
    if v == "tak":
        return 1
    if v == "nie":
        return 0
    return val

TRANSFORM = {
    "tak_nie": _tak_nie,
}

@tool
def transform_excel(spec: dict, file_path: str, output_path: str = "wynik.xlsx") -> str:

    """transform_excel(spec: dict, file_path: str, output_path: str = "wynik.xlsx")
      - This tool is used to transform excel file according to specification provided by user into a new file, spec are saved as work_sketch in your AgentState
      """

    if not os.path.exists(file_path):
        return f"BŁĄD: Nie znaleziono pliku źródłowego: {file_path}"

    header_row = spec.get("header_row", 0)
    df = pd.read_excel(file_path, sheet_name=0, header=header_row)
    df.columns = df.columns.str.strip()
    kolumny = df.columns.tolist()

    # Sortowanie
    sort_by = spec.get("sort_by")
    if sort_by:
        if sort_by in kolumny:
            df = df.sort_values(by=sort_by)
        else:
            return f"BŁĄD: Kolumna do sortowania '{sort_by}' nie istnieje. Dostępne: {kolumny}"

    # POPRAWKA: zawsze bierz sheets ze spec, niezależnie od create_sheets
    sheets_list = spec.get("sheets", [])

    if not sheets_list:
        return "BŁĄD: Brak definicji arkuszy w spec['sheets']"

    try:
        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
            for sheet_def in sheets_list:  # ✅ inna nazwa zmiennej niż lista
                sheet_name = sheet_def.get("sheet_name", "Sheet1")
                start_row = sheet_def.get("start_row", 0)
                start_col = sheet_def.get("start_col", 0)
                columns = sheet_def.get("columns", [])

                if not columns:
                    return f"BŁĄD: Arkusz '{sheet_name}' nie ma zdefiniowanych kolumn"

                df_output = build_sheet(df, columns)

                df_output.to_excel(
                    excel_writer=writer,
                    sheet_name=sheet_name,
                    index=False,
                    startrow=start_row,
                    startcol=start_col,
                    header=True,
                )

        return f"Okay: Saved file as '{output_path}' with {len(sheets_list)} sheet/sheets"

    except Exception as e:
        return f"Error: You cant save this file: {e}"


def build_sheet(df: pd.DataFrame, columns: list[dict]) -> pd.DataFrame:
    """
    Tworzy DataFrame dla jednego arkusza na podstawie listy definicji kolumn.

    Każda definicja kolumny to dict z kluczami:
      target    - nazwa kolumny w pliku wyjściowym (wymagane)
      source    - nazwa kolumny w pliku źródłowym (opcjonalne)
      value     - wartość stała gdy brak source (opcjonalne)
      transform - nazwa transformacji ze słownika TRANSFORM (opcjonalne)
    """
    n = len(df)
    output_df = pd.DataFrame()

    for col_def in columns:
        target = col_def.get("target")
        if not target:
            continue

        source = col_def.get("source")
        value = col_def.get("value", "")
        transform_name = col_def.get("transform")

        series = get_column(df, source) if source else pd.Series([value] * n)

        if transform_name and transform_name in TRANSFORM:
            series = series.apply(TRANSFORM[transform_name])

        output_df[target] = series.values

    return output_df


def get_column(df: pd.DataFrame, col_name: str) -> pd.Series:
    """Zwraca kolumnę z df lub pusty Series gdy brak."""
    if col_name in df.columns:
        return df[col_name]
    return pd.Series([""] * len(df))

@tool
def list_source_columns(file_path: str, header_row: int = 0) -> list[str]:
    """list_source_columns(file_path: str)
      - This tool is used to list all columns from excel file,
        it can be useful when you want to transform excel file but you don't know what columns are in it, you can use this tool to check columns and then use transform_excel tool to transform file according to specification provided by user"""
    if not os.path.exists(file_path):
        return [f"BŁĄD: Brak pliku {file_path}"]
    try:
        if file_path.lower().endswith(".csv"):
            df = pd.read_csv(file_path, dtype=str, header=header_row, nrows=0)
        else:
            df = pd.read_excel(file_path, dtype=str, header=header_row, nrows=0)
        return df.columns.str.strip().tolist()
    except Exception as e:
        return [f"Error: {e}"]