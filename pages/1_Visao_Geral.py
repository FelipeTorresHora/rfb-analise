# pages/1_🏠_Visao_Geral.py
import streamlit as st
import plotly.express as px

st.set_page_config(layout="wide", page_title="Visão Geral")

st.title("🏠 Visão Geral")
st.markdown("---")

# Verifica se o dataframe filtrado existe no estado da sessão
if 'df_filtrado' not in st.session_state or st.session_state.df_filtrado.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados. Por favor, ajuste os filtros na página principal.")
    st.stop()

df = st.session_state.df_filtrado

# --- KPIs Principais ---
st.subheader("Indicadores Chave")
total_empresas = len(df)
empresas_ativas = len(df[df['situacao_cadastral_label'] == 'Ativa'])
percent_ativas = (empresas_ativas / total_empresas * 100) if total_empresas > 0 else 0

col1, col2, col3 = st.columns(3)
col1.metric("Total de Empresas", f"{total_empresas:,}")
col2.metric("Empresas Ativas", f"{empresas_ativas:,}")
col3.metric("% de Empresas Ativas", f"{percent_ativas:.2f}%")

st.markdown("---")

# --- Evolução Temporal ---
st.subheader("Evolução de Empresas por Ano")
empresas_por_ano = df['ano_situacao'].value_counts().sort_index()
st.line_chart(empresas_por_ano)

# --- Aberturas vs. Baixas ---
st.subheader("Aberturas (Ativas) vs. Baixas por Mês/Ano")
df_evolucao = df.groupby('mes_ano_situacao')['situacao_cadastral_label'].value_counts().unstack(fill_value=0)

# Garante que as colunas Ativa e Baixada existam
if 'Ativa' not in df_evolucao: df_evolucao['Ativa'] = 0
if 'Baixada' not in df_evolucao: df_evolucao['Baixada'] = 0

df_evolucao.index = df_evolucao.index.to_timestamp()

fig = px.line(df_evolucao, y=['Ativa', 'Baixada'], title="Evolução Mensal de Empresas Ativas vs. Baixadas",
              labels={'value': 'Quantidade', 'mes_ano_situacao': 'Data'})
st.plotly_chart(fig, use_container_width=True)