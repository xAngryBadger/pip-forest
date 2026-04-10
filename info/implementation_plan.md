# CLI Scheduling & Financial Dossier (V5.8) - Implementation Plan

## Goal Description
Evolve the SRF CLI into a professional management tool. Implement a "Financial Dossier" capable of cross-referencing budget (CT_313) with simulated labor consumption, featuring a **rich multi-sheet Excel export** and a **Global Swarm Mode** for final planting/irrigation.

## Proposed Changes

### [e:\cli_planilhas\atm_v5.py](file:///e:/cli_planilhas/atm_v5.py)

#### [MODIFY] Financial Data Layer
- **[modulo_importar_tarifas](file:///e:/cli_planilhas/atm_v5.py#425-484)**:
  - Re-add automated extraction for `CUSTO HORA (R$/h)` and `PREÇO R$ (Receita/ha)`.
  - Implement a `resolver_custo_hora` helper to handle fallbacks (median/config).
- **[calcular_cronograma_inteligente](file:///e:/cli_planilhas/atm_v5.py#680-1027)**:
  - Map `Revenue` (Area * Price/ha) for every task in the `demandas` dict.
  - Map `Labor Cost` (HH * Cost/h) per activity.

#### [MODIFY] Global Swarm Mode ("Ursinhos Carinhosos")
- **Activity Splitting**:
  - Automatically identify "Final Activities" (Plantio, Irrigação).
  - Block these activities from initial per-turma queues.
- **Phased Simulation**:
  - Phase 1: Normal queues run until the farm is 100% prepared.
  - Phase 2: Trigger "Mutirão Global". All available executors merge into a single swarm to finish the "Final Activities" together.

#### [MODIFY] Professional Excel Export (The "Dossier")
- **Multi-Sheet Engine**:
  - Use `pd.ExcelWriter` with `openpyxl`.
  - **Sheet 1: `RESUMO FINANCEIRO`**: Executive dashboard with Revenue, Direct Labor Cost, Idleness Cost (Gap analysis), and Profit Margin.
  - **Sheet 2: `CRONOGRAMA DETALHADO`**: Day-by-day actions with columns for `Talhão`, `Atividade`, `Turma`, `HH` and `Custo Alocado`.
  - **Sheet 3: `CUSTO POR ATIVIDADE`**: Aggregated pivot showing which activities (Roçada, Adubação, etc.) are most profitable vs most expensive.
- **Styling & UX**:
  - Inject **AutoFilters** on the headers.
  - Format currency columns as `R$ #,##0.00`.

## Verification Plan
### Automated Tests
- `python -m py_compile atm_v5.py`
### Manual Verification
- Verify the Excel file contains all 3 tabs with valid math.
- Ensure Swarm phase triggers only after Phase 1 is done.
- Check if filters are working in the exported Excel.
