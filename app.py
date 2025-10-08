import streamlit as st
import pandas as pd
from core.database import (
    carregar_dados_filtrados,
    carregar_opcoes_filtros,
    carregar_kpis,
    obter_metadados,
    carregar_mapeamento_municipios
)

# --- Configuração da Página Principal ---
st.set_page_config(
    layout="wide",
    page_title="Dashboard RFB - RS",
    page_icon="📊"
)

# --- Mapeamento de Situação Cadastral ---
MAPEAMENTO_SITUACAO = {
    1: 'Nula',
    2: 'Ativa',
    3: 'Suspensa',
    4: 'Inapta',
    8: 'Baixada'
}

MAPEAMENTO_SITUACAO_REVERSO = {v: k for k, v in MAPEAMENTO_SITUACAO.items()}

# --- Inicialização do Estado da Sessão ---

@st.cache_data(ttl=3600)
def carregar_opcoes_iniciais():
    """Carrega apenas as opções para os filtros (RS e Ativa)."""
    return carregar_opcoes_filtros()

def inicializar_estado():
    """Inicializa o estado da sessão."""
    if 'opcoes_filtros' not in st.session_state:
        with st.spinner("⚡ Carregando opções de filtros (RS - Ativas)..."):
            st.session_state.opcoes_filtros = carregar_opcoes_iniciais()
    
    if 'municipio_selecionado' not in st.session_state:
        st.session_state.municipio_selecionado = []
    
    if 'cnae_selecionado' not in st.session_state:
        st.session_state.cnae_selecionado = []
    
    if 'situacao_selecionada' not in st.session_state:
        st.session_state.situacao_selecionada = []
    
    if 'periodo_selecionado' not in st.session_state:
        opcoes = st.session_state.opcoes_filtros
        min_data = opcoes.get('min_data')
        max_data = opcoes.get('max_data')
        st.session_state.periodo_selecionado = (min_data, max_data) if min_data and max_data else (None, None)

# --- Função de Carregamento de Dados ---

def carregar_dados():
    """Carrega dados COM FILTROS aplicados no banco (RS e Ativa por padrão)."""
    
    # Municípios já vêm como nomes
    municipios = st.session_state.municipio_selecionado if st.session_state.municipio_selecionado else None
    
    # Situações
    situacoes = [MAPEAMENTO_SITUACAO_REVERSO[s] for s in st.session_state.situacao_selecionada] if st.session_state.situacao_selecionada else None
    
    # CNAEs
    cnaes = st.session_state.cnae_selecionado if st.session_state.cnae_selecionado else None
    
    # Período
    data_inicio = None
    data_fim = None
    if len(st.session_state.periodo_selecionado) == 2:
        data_inicio, data_fim = st.session_state.periodo_selecionado
    
    with st.spinner("⚡ Carregando dados filtrados do banco (RS - Ativas)..."):
        df = carregar_dados_filtrados(
            municipios=municipios,
            cnaes=cnaes,
            situacoes=situacoes,
            data_inicio=data_inicio,
            data_fim=data_fim,
            limit=2000000  # 2 milhões
        )
    
    if df.empty:
        return df
    
    # Processamento
    df['situacao_cadastral'] = pd.to_numeric(df['situacao_cadastral'], errors='coerce')
    df.dropna(subset=['data_situacao_cadastral', 'situacao_cadastral'], inplace=True)
    
    # CNAE
    if 'cnae' in df.columns:
        df['cnae'] = df['cnae'].astype(str).fillna('N/A')
    
    # Colunas derivadas
    df['data_situacao_cadastral'] = pd.to_datetime(df['data_situacao_cadastral'])
    df['ano_situacao'] = df['data_situacao_cadastral'].dt.year
    df['mes_ano_situacao'] = df['data_situacao_cadastral'].dt.to_period('M')
    df['situacao_cadastral_label'] = df['situacao_cadastral'].map(MAPEAMENTO_SITUACAO).fillna('Outra')
    
    return df

# === INICIALIZAÇÃO ===
inicializar_estado()
opcoes = st.session_state.opcoes_filtros

# --- Barra Lateral de Filtros ---
st.sidebar.header("🔍 Filtros Globais")
st.sidebar.info("⚡ **Base:** RS - Empresas Ativas - Limite: 2M registros")

# Filtro por Município (nomes)
lista_municipios = sorted(opcoes.get('municipios', []))
st.session_state.municipio_selecionado = st.sidebar.multiselect(
    "Selecione o Município",
    options=lista_municipios,
    default=st.session_state.municipio_selecionado,
    help="Municípios do Rio Grande do Sul"
)

# Filtro por CNAE
lista_cnaes = sorted([str(c) for c in opcoes.get('cnaes', [])])
st.session_state.cnae_selecionado = st.sidebar.multiselect(
    "Selecione o CNAE",
    options=lista_cnaes,
    default=st.session_state.cnae_selecionado,
    help="Códigos CNAE disponíveis"
)

# Filtro por Situação Cadastral
lista_situacoes_cod = opcoes.get('situacoes', [])
lista_situacoes = sorted([MAPEAMENTO_SITUACAO.get(int(s), 'Outra') for s in lista_situacoes_cod if int(s) in MAPEAMENTO_SITUACAO])
st.session_state.situacao_selecionada = st.sidebar.multiselect(
    "Selecione a Situação Cadastral",
    options=lista_situacoes,
    default=st.session_state.situacao_selecionada,
    help="Situações cadastrais disponíveis"
)

# Filtro por Período
min_data = opcoes.get('min_data')
max_data = opcoes.get('max_data')
if min_data and max_data:
    st.session_state.periodo_selecionado = st.sidebar.date_input(
        "Selecione o Período",
        value=(
            st.session_state.periodo_selecionado[0] if st.session_state.periodo_selecionado[0] else min_data,
            st.session_state.periodo_selecionado[1] if st.session_state.periodo_selecionado[1] else max_data
        ),
        min_value=min_data,
        max_value=max_data,
        help="Período de data de situação cadastral"
    )

# Botões
st.sidebar.markdown("---")
aplicar_filtros = st.sidebar.button("🔄 Aplicar Filtros", type="primary", use_container_width=True)

if st.sidebar.button("🗑️ Limpar Filtros", use_container_width=True):
    st.session_state.municipio_selecionado = []
    st.session_state.cnae_selecionado = []
    st.session_state.situacao_selecionada = []
    st.session_state.periodo_selecionado = (min_data, max_data)
    st.rerun()

# --- Carrega Dados Filtrados ---
if aplicar_filtros or 'df_filtrado' not in st.session_state:
    df_filtrado = carregar_dados()
    st.session_state.df_filtrado = df_filtrado
else:
    df_filtrado = st.session_state.df_filtrado

# --- Conteúdo Principal ---
st.title("📊 Dashboard de Empresas (RFB) - Rio Grande do Sul")
st.markdown("---")

st.success("⚡ **OTIMIZADO** - Base: UF=RS | Situação=Ativa | Limite=2M registros")

st.markdown("""
### 🎯 Como Usar
- **Barra lateral:** Selecione os filtros desejados
- **Aplicar Filtros:** Carrega os dados do PostgreSQL
- **Municípios:** Exibidos por nome (mapeamento via CSV)
- **Performance:** Queries otimizadas com índices e filtros no banco
---
""")

# KPIs
st.subheader("📈 Indicadores Chave (RS - Ativas)")
kpis = carregar_kpis()

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Total Empresas (RS)", f"{kpis.get('total_empresas', 0):,}")
with col2:
    st.metric("Empresas Ativas", f"{kpis.get('empresas_ativas', 0):,}")
with col3:
    st.metric("Empresas Baixadas", f"{kpis.get('empresas_baixadas', 0):,}")
with col4:
    st.metric("% Ativas", f"{kpis.get('percent_ativas', 0):.2f}%")

st.markdown("---")

# Dados Filtrados
st.subheader("🔍 Dados Filtrados")
if not df_filtrado.empty:
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Registros Após Filtros", f"{len(df_filtrado):,}")
    with col_b:
        if len(df_filtrado) >= 2000000:
            st.warning("⚠️ Limite de 2 milhões atingido. Refine os filtros.")
    
    # Exibir com nome do município
    colunas_exibir = ['cnpj_basico', 'municipio_nome', 'cnae', 'situacao_cadastral_label', 'data_situacao_cadastral']
    colunas_disponiveis = [c for c in colunas_exibir if c in df_filtrado.columns]
    
    st.dataframe(
        df_filtrado[colunas_disponiveis].head(100),
        use_container_width=True,
        height=400
    )
    
    # Export
    if st.button("📥 Exportar Dados (CSV)"):
        csv = df_filtrado.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name="dados_rfb_rs_filtrados.csv",
            mime="text/csv"
        )
else:
    st.info("👆 Selecione filtros e clique em 'Aplicar Filtros' para carregar dados.")

st.markdown("---")

# Informações Técnicas
with st.expander("ℹ️ Informações Técnicas"):
    st.markdown("""
    ### Otimizações Implementadas
    
    #### ✅ Filtro Padrão Base
    - UF = 'RS' (Rio Grande do Sul)
    - Situação Cadastral = 2 (Ativa)
    - Limite máximo: 2.000.000 de registros
    
    #### ✅ Mapeamento de Municípios
    - CSV com 5.572 municípios (código → nome)
    - Cache de 24 horas
    - Conversão automática na interface
    
    #### ✅ Performance
    - Queries otimizadas com índices compostos
    - Filtros aplicados no PostgreSQL
    - JOIN no banco (não no pandas)
    - Connection pooling com SQLAlchemy
    
    ### Índices Recomendados
    ```
    CREATE INDEX idx_uf_situacao ON estabelecimentos(uf, situacao_cadastral);
    CREATE INDEX idx_uf_sit_data ON estabelecimentos(uf, situacao_cadastral, data_situacao_cadastral);
    CREATE INDEX idx_cnpj_cnae ON estabelecimento_cnaes(cnpj);
    ```
    """)
