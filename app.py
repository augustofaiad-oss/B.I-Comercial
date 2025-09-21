import streamlit as st
import pandas as pd
import plotly.express as px
from typing import Dict

st.set_page_config(page_title="Dashboard Quintal", layout="wide", initial_sidebar_state="expanded")

# =============================
# FUNÇÕES AUXILIARES
# =============================

def load_data(sheet_name: str, file_path: str = "Controle_De_Estoque.xlsx") -> pd.DataFrame:
    """
    Tenta carregar a planilha e detectar a linha de cabeçalho (procurando 'ESTOQUE').
    Retorna DataFrame limpo ou DataFrame vazio se não encontrar dados.
    """
    try:
        raw = pd.read_excel(file_path, sheet_name=sheet_name, header=None)
    except Exception as e:
        st.error(f"Erro ao abrir a planilha: {e}")
        return pd.DataFrame()

    # localizar linha de cabeçalho que contenha a palavra 'ESTOQUE'
    header_rows = raw[raw.apply(lambda r: r.astype(str).str.contains("ESTOQUE", case=False, na=False).any(), axis=1)].index.tolist()
    if header_rows:
        header_idx = header_rows[0]
        df = raw.copy()
        df.columns = df.iloc[header_idx]
        df = df[header_idx+1:].reset_index(drop=True)
    else:
        # tenta ler com a primeira linha como cabeçalho
        df = pd.read_excel(file_path, sheet_name=sheet_name)

    # remover linhas todas nulas e colunas totalmente nulas
    df = df.dropna(how="all").loc[:, df.notna().any(axis=0)]
    # padronizar nomes das colunas
    df.columns = [str(c).strip() for c in df.columns]

    return df

def extract_fields(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza as colunas essenciais: PRODUTO, ESTOQUE, SUGESTAO.
    Se não encontrar, cria colunas vazias para manter compatibilidade do dashboard.
    """
    df2 = df.copy()
    # identificar coluna de produto
    prod_candidates = [c for c in df2.columns if any(k in str(c).upper() for k in ["PROD", "ITEM", "CERVEJ", "NOME"])]
    estoque_candidates = [c for c in df2.columns if "ESTOQUE" in str(c).upper()]
    sugestao_candidates = [c for c in df2.columns if "SUGEST" in str(c).upper() or "SUGESTÃO" in str(c).upper()]

    if prod_candidates:
        df2["PRODUTO"] = df2[prod_candidates[0]].astype(str).str.strip()
    else:
        df2["PRODUTO"] = df2.index.astype(str)

    if estoque_candidates:
        df2["ESTOQUE"] = pd.to_numeric(df2[estoque_candidates[0]], errors="coerce")
    else:
        df2["ESTOQUE"] = pd.NA

    if sugestao_candidates:
        df2["SUGESTAO"] = pd.to_numeric(df2[sugestao_candidates[0]], errors="coerce")
    else:
        df2["SUGESTAO"] = pd.NA

    return df2

# =============================
# CARREGAR DADOS
# =============================
SHEETS = {
    "Bebidas": "BEBIDAS",
    "Itens Salão": "ITENS SALÃO",
    "Cozinha": "COZINHA",
    "Bar Drinks": "BAR DRINKS"
}

data: Dict[str, pd.DataFrame] = {}
for label, sheet in SHEETS.items():
    data[label] = load_data(sheet)

# =============================
# LAYOUT / SIDEBAR
# =============================
st.sidebar.title("📊 Dashboard Quintal")
st.sidebar.markdown("Modo dark, **design moderno**. Use o menu abaixo para navegar pelas categorias.")
selected = st.sidebar.radio("Selecione a aba", list(SHEETS.keys()))

df_raw = data[selected]

if df_raw.empty:
    st.warning("Nenhum dado encontrado para esta aba. Verifique se a aba existe na planilha e se contém a linha de cabeçalho com 'ESTOQUE'.")
    st.stop()

df = extract_fields(df_raw)

# =============================
# KPIs
# =============================
total_itens = int(df["PRODUTO"].nunique())
estoque_total = int(df["ESTOQUE"].sum(skipna=True)) if df["ESTOQUE"].notna().any() else 0
sugestao_total = int(df["SUGESTAO"].sum(skipna=True)) if df["SUGESTAO"].notna().any() else 0
itens_criticos = df[df["ESTOQUE"].fillna(0) <= df["SUGESTAO"].fillna(0)][["PRODUTO","ESTOQUE","SUGESTAO"]].head(10)

k1, k2, k3 = st.columns([1.5,1.5,1.5])
k1.metric("Total de Itens", total_itens)
k2.metric("Estoque Total", estoque_total)
k3.metric("Sugestão de Compra", sugestao_total)

st.markdown("---")

# =============================
# GRÁFICOS PRINCIPAIS
# =============================
st.subheader(f"📦 Visão Geral - {selected}")

# Estoque por produto (gráfico de barras)
if df["ESTOQUE"].notna().any():
    fig = px.bar(df.sort_values("ESTOQUE", ascending=False), x="PRODUTO", y="ESTOQUE",
                 title="Estoque por Produto", labels={"ESTOQUE":"Estoque", "PRODUTO":"Produto"})
    fig.update_layout(xaxis_tickangle=-45, template="plotly_dark", height=450)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Nenhuma coluna de estoque numérica encontrada nesta aba.")

# Sugestão de compra
if df["SUGESTAO"].notna().any():
    fig2 = px.bar(df.sort_values("SUGESTAO", ascending=False), x="PRODUTO", y="SUGESTAO",
                  title="Sugestão de Compra", labels={"SUGESTAO":"Sugestão"}, color="SUGESTAO")
    fig2.update_layout(xaxis_tickangle=-45, template="plotly_dark", height=380)
    st.plotly_chart(fig2, use_container_width=True)

# Itens críticos
st.subheader("⚠️ Itens Críticos (estoque <= sugestão)")
if not itens_criticos.empty:
    st.table(itens_criticos.fillna("-").rename(columns={"PRODUTO":"Produto","ESTOQUE":"Estoque","SUGESTAO":"Sugestão"}))
else:
    st.write("Nenhum item crítico encontrado.")

st.markdown("---")

# Mostrar dados brutos (expandable)
with st.expander("Mostrar dados brutos"):
    st.dataframe(df_raw.reset_index(drop=True))

st.caption("Dashboard gerado automaticamente. Para atualizar os dados em tempo real, coloque a planilha no Google Sheets ou OneDrive e adapte a função load_data para ler dessas fontes.")
