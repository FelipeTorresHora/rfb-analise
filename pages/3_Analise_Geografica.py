# pages/3_🌍_Analise_Geografica.py
import streamlit as st
import pandas as pd
import plotly.express as px
import json

st.set_page_config(layout="wide", page_title="Análise Geográfica")

st.title("🌍 Análise Geográfica (Rio Grande do Sul)")
st.markdown("---")

if 'df_filtrado' not in st.session_state or st.session_state.df_filtrado.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
    st.stop()

df = st.session_state.df_filtrado

# --- Carregar GeoJSON ---
try:
    with open('dados/municipios_rs.json', 'r', encoding='utf-8') as f:
        geojson_rs = json.load(f)
except FileNotFoundError:
    st.error("Arquivo 'municipios_rs.json' não encontrado. Faça o download e coloque na pasta do projeto.")
    st.stop()

# --- Mapa Interativo ---
st.subheader("Distribuição de Empresas por Município no RS")
empresas_por_municipio = df['municipio'].value_counts().reset_index()
empresas_por_municipio.columns = ['municipio', 'quantidade']

fig = px.choropleth_mapbox(
    empresas_por_municipio,
    geojson=geojson_rs,
    locations='municipio',
    featureidkey="properties.name", # Chave no GeoJSON que corresponde ao nome do município
    color='quantidade',
    color_continuous_scale="Viridis",
    mapbox_style="carto-positron",
    zoom=5.5,
    center={"lat": -30.0346, "lon": -51.2177},
    opacity=0.6,
    labels={'quantidade': 'Nº de Empresas'}
)
fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
st.plotly_chart(fig, use_container_width=True)

# --- Ranking de Municípios ---
st.subheader("Ranking de Municípios")
col1, col2 = st.columns([1, 2])

with col1:
    st.write("**Top 10 Municípios**")
    top_10_municipios = empresas_por_municipio.head(10)
    st.dataframe(top_10_municipios, hide_index=True)

with col2:
    st.write("**Gráfico do Top 10**")
    fig_bar = px.bar(top_10_municipios, x='municipio', y='quantidade', text_auto=True)
    st.plotly_chart(fig_bar, use_container_width=True)