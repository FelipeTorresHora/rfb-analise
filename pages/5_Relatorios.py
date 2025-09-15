# pages/5_📄_Relatorios.py
import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(layout="wide", page_title="Geração de Relatórios")

st.title("📄 Geração e Download de Relatórios")
st.markdown("---")

if 'df_filtrado' not in st.session_state or st.session_state.df_filtrado.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
    st.stop()

df_relatorio = st.session_state.df_filtrado

# --- Função para converter DataFrame para Excel em memória ---
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Relatorio')
    processed_data = output.getvalue()
    return processed_data

# --- Interface de Geração ---
st.subheader("Relatório Personalizado com Filtros Atuais")
st.markdown("Os seguintes filtros estão aplicados ao relatório:")

with st.expander("Ver Filtros Ativos", expanded=False):
    st.write(f"**Municípios:** {st.session_state.municipio_selecionado or 'Todos'}")
    st.write(f"**CNAEs:** {st.session_state.cnae_selecionado or 'Todos'}")
    st.write(f"**Situação Cadastral:** {st.session_state.situacao_selecionada or 'Todas'}")
    start, end = st.session_state.periodo_selecionado
    st.write(f"**Período:** {start.strftime('%d/%m/%Y')} a {end.strftime('%d/%m/%Y')}")

st.metric("Total de Linhas no Relatório", f"{len(df_relatorio):,}")

st.markdown("### Pré-visualização do Relatório")
st.dataframe(df_relatorio.head(10))

# --- Botão de Geração e Download ---
st.markdown("---")
st.subheader("Download do Relatório Completo")

# Gera o arquivo Excel em memória
excel_data = to_excel(df_relatorio)

# Cria o botão de download
st.download_button(
    label="📥 Baixar Relatório em Excel",
    data=excel_data,
    file_name="relatorio_empresas_filtrado.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)