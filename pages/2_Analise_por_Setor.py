# pages/2_📊_Analise_por_Setor.py
import streamlit as st
import pandas as pd

st.set_page_config(layout="wide", page_title="Análise por Setor (CNAE)")

st.title("📊 Análise por Setor (CNAE)")
st.markdown("---")

if 'df_filtrado' not in st.session_state or st.session_state.df_filtrado.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
    st.stop()

df = st.session_state.df_filtrado

# --- Ranking de CNAEs ---
st.subheader("Top 15 CNAEs por Número de Empresas")
top_15_cnaes = df['cnae_fiscal_principal'].value_counts().nlargest(15)
top_15_cnaes.index = top_15_cnaes.index.astype(str) # Converte para string para gráfico de barras
st.bar_chart(top_15_cnaes)

# --- Evolução por Setor ---
st.subheader("Evolução de Aberturas para os Setores Filtrados")
if not st.session_state.cnae_selecionado:
    st.info("Selecione um ou mais CNAEs na barra lateral para ver a evolução específica do setor.")
else:
    evolucao_setor = df[df['cnae_fiscal_principal'].isin(st.session_state.cnae_selecionado)]
    evolucao_setor_chart = evolucao_setor.groupby('ano_situacao')['cnae_fiscal_principal'].value_counts().unstack(fill_value=0)
    st.line_chart(evolucao_setor_chart)