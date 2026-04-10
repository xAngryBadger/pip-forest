import pandas as pd

def check_cols():
    path = "exame.xlsx"
    df = pd.read_excel(path, sheet_name="MICROPLANEJAMENTO_ABRIL_JUNHO")
    print(df.columns.tolist())

if __name__ == "__main__":
    check_cols()
