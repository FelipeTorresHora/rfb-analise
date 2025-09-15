# pages/6_🤖_Buscador_Instagram.py
import streamlit as st
import pandas as pd
from threading import Thread
from core.search import buscar_em_lote # Importa a função do arquivo em core/

st.set_page_config(layout="wide", page_title="Buscador de Instagram")

# Inicializa as variáveis de estado da sessão para esta página
if 'scraping_in_progress' not in st.session_state:
    st.session_state.scraping_in_progress = False
if 'scraping_results' not in st.session_state:
    st.session_state.scraping_results = None
if 'scraping_thread' not in st.session_state:
    st.session_state.scraping_thread = None

def run_scraping_thread(df_para_buscar):
    """Função que será executada na thread para não bloquear a UI."""
    resultados = buscar_em_lote(df_para_buscar)
    st.session_state.scraping_results = pd.DataFrame(resultados)
    st.session_state.scraping_in_progress = False # Sinaliza o fim do processo

st.title("🤖 Buscador de Perfis do Instagram")
st.markdown("---")
st.markdown("""
Esta ferramenta utiliza as empresas selecionadas pelos **filtros globais da barra lateral** para realizar uma busca em lote por perfis do Instagram.
A busca é executada em segundo plano para não travar a aplicação.
""")

# Verifica se o dataframe filtrado do app principal existe
if 'df_filtrado' not in st.session_state or st.session_state.df_filtrado.empty:
    st.warning("Nenhum dado encontrado. Por favor, aplique filtros na barra lateral para selecionar as empresas desejadas.")
    st.stop()

df_selecionado = st.session_state.df_filtrado
st.info(f"**{len(df_selecionado):,}** empresas foram selecionadas com base nos filtros globais. Estas empresas serão usadas para a busca.")

st.subheader("1. Inicie a Busca em Background")
st.markdown("Ao clicar no botão, a busca será iniciada. Você pode continuar navegando no dashboard. Os resultados aparecerão abaixo quando a busca for concluída.")

col1, col2 = st.columns(2)
with col1:
    start_button_disabled = st.session_state.scraping_in_progress
    if st.button("🚀 Iniciar Busca dos Perfis", type="primary", disabled=start_button_disabled, use_container_width=True):
        st.session_state.scraping_in_progress = True
        st.session_state.scraping_results = None

        thread = Thread(target=run_scraping_thread, args=(df_selecionado.copy(),))
        st.session_state.scraping_thread = thread
        thread.start()
        st.rerun()

with col2:
    if st.button("🧹 Limpar Resultados", disabled=(not st.session_state.scraping_in_progress and st.session_state.scraping_results is None), use_container_width=True):
        st.session_state.scraping_in_progress = False
        st.session_state.scraping_results = None
        st.session_state.scraping_thread = None
        st.rerun()

st.markdown("---")
st.subheader("2. Acompanhe e Exporte os Resultados")

if st.session_state.scraping_in_progress:
    st.info("🔄 Busca em andamento... Por favor, aguarde. A interface permanecerá responsiva.")
    st.spinner("Processando...")

elif st.session_state.scraping_results is not None:
    df_resultados = st.session_state.scraping_results
    perfis_validados = len(df_resultados[df_resultados['status_validacao'] == 'Perfil Validado'])

    st.success(f"✅ Busca concluída! {perfis_validados} perfis foram encontrados e validados de um total de {len(df_resultados)} empresas processadas.")
    st.dataframe(df_resultados, use_container_width=True)

    csv = df_resultados.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Baixar Resultados em CSV",
        data=csv,
        file_name="resultados_instagram.csv",
        mime="text/csv",
    )
else:
    st.info("Aguardando o início da busca. Os resultados aparecerão aqui.")