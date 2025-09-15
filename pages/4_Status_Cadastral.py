# pages/4_📋_Status_Cadastral.py
import streamlit as st
import plotly.express as px

st.set_page_config(layout="wide", page_title="Análise de Status Cadastral")

st.title("📋 Análise de Status Cadastral")
st.markdown("---")

if 'df_filtrado' not in st.session_state or st.session_state.df_filtrado.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
    st.stop()

df = st.session_state.df_filtrado

# --- Distribuição de Status ---
st.subheader("Distribuição de Empresas por Situação Cadastral")
status_counts = df['situacao_cadastral_label'].value_counts()
fig_pie = px.pie(status_counts, values=status_counts.values, names=status_counts.index, 
                 title="Proporção por Status")
st.plotly_chart(fig_pie, use_container_width=True)

# --- Evolução do Status ---
st.subheader("Evolução do Status Cadastral ao Longo do Tempo")
evolucao_status = df.groupby(['ano_situacao', 'situacao_cadastral_label']).size().reset_index(name='quantidade')

fig_area = px.area(evolucao_status, x='ano_situacao', y='quantidade', color='situacao_cadastral_label',
                   title="Quantidade de Empresas por Status a Cada Ano",
                   labels={'ano_situacao': 'Ano', 'quantidade': 'Número de Empresas'})
st.plotly_chart(fig_area, use_container_width=True)