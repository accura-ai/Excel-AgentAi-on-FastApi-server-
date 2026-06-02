import pandas as pd

xl = pd.ExcelFile('dane_zrodlowe.xlsx')
print(xl.sheet_names)