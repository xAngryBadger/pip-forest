import pandas as pd

def analyze_formosa():
    path = "exame.xlsx"
    df = pd.read_excel(path, sheet_name="MICROPLANEJAMENTO_ABRIL_JUNHO")
    
    # Mapeamento manual conforme check_cols
    col_faz = 'NOME FAZENDA'
    col_atv = 'ATIVIDADES'
    col_area = 'ÁREA TRABALHADA ESTIMADA (HECTARE)'
    
    # Filtrar Formosa
    formosa = df[df[col_faz].str.contains("FORMOSA", na=False, case=False)].copy()
    
    if formosa.empty:
        print("Fazenda FORMOSA nao encontrada.")
        return

    # Agrupar por atividade
    summary = formosa.groupby(col_atv)[col_area].sum().reset_index()
    summary.columns = ['atividade', 'area_ha']
    summary.to_csv("formosa_atividades.csv", index=False)
    
    print(f"Total de registros FORMOSA: {len(formosa)}")
    print(f"Area total FORMOSA: {formosa[col_area].sum():.2f} ha")
    print(summary.to_string())

if __name__ == "__main__":
    analyze_formosa()
