from tools import transform_excel, list_source_columns

# Najpierw sprawdź jakie kolumny ma plik źródłowy
print("Kolumny w pliku źródłowym:")
print(list_source_columns("dane_zrodlowe.xlsx"))
print()

spec = {
    "header_row": 0,
    "sort_by": "Nazwisko",
    "sheets": [
        {
            "sheet_name": "Osoby",
            "start_row": 0,
            "start_col": 0,
            "columns": [
                {"target": "ID",              "source": "UNIVERSALID"},
                {"target": "Imię",            "source": "Imie"},
                {"target": "Nazwisko",        "source": "Nazwisko"},
                {"target": "Dział",           "source": "Dzial"},
                {"target": "Telefon",         "source": "Telefon"},
                {"target": "Email",           "source": "Email"},
                {"target": "Typ dokumentu",   "value":  "Dowód osobisty"},
                {"target": "Strój służbowy",  "source": "Stroj",    "transform": "tak_nie"},
                {"target": "Badanie lekarskie","source": "BadLek",  "transform": "tak_nie"},
            ]
        },
        {
            "sheet_name": "Uprawnienia",
            "start_row": 0,
            "start_col": 0,
            "columns": [
                {"target": "ID",              "source": "UNIVERSALID"},
                {"target": "Imię",            "source": "Imie"},
                {"target": "Uprawnienia ADR", "source": "UprADR",   "transform": "tak_nie"},
                {"target": "Wydany ID",       "source": "WydanyID", "transform": "tak_nie"},
            ]
        }
    ]
}

result = transform_excel(
    spec=spec,
    file_path="dane_zrodlowe.xlsx",
    output_path="Arkusz1.xlsx",
)

print(result)
