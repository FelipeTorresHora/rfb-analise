# app.py
import streamlit as st
import pandas as pd
import glob

# --- Configuração da Página Principal ---
st.set_page_config(
    layout="wide",
    page_title="Dashboard RFB",
    page_icon="📊"
)

# --- Mapeamento de Situação Cadastral (para filtros amigáveis) ---
MAPEAMENTO_SITUACAO = {
    1: 'Nula',
    2: 'Ativa',
    3: 'Suspensa',
    4: 'Inapta',
    8: 'Baixada'
}

# --- Função de Carregamento de Dados (Cacheada) ---
@st.cache_data
def carregar_dados():
    """
    Função para carregar, concatenar, pré-processar e ENRIQUECER os dados.
    """
    # 1. Carregar e tratar a tabela de descrições de CNAE
    try:
        # O encoding 'utf-8-sig' remove o BOM (caractere invisível) do início do arquivo
        df_cnae = pd.read_csv('dados/codigos_cnae_2.csv', sep=';', dtype=str, encoding='utf-8-sig')
        df_cnae.columns = ['cnae', 'descricao']
        df_cnae.dropna(how='all', inplace=True)
        # O arquivo CNAE possui duplicatas, removemos mantendo a primeira ocorrência
        df_cnae.drop_duplicates(subset=['cnae'], keep='first', inplace=True)
        df_cnae['descricao'] = df_cnae['descricao'].str.strip()
    except FileNotFoundError:
        st.error("Arquivo 'codigos_cnae_2.csv' não encontrado. Por favor, adicione-o à pasta do projeto.")
        return pd.DataFrame() # Retorna um DataFrame vazio para evitar que o app quebre

    # 2. Carregar os dados principais da RFB
    arquivos_csv = glob.glob('dados/rfb_*.csv')
    if not arquivos_csv:
        st.error("Nenhum arquivo 'rfb_*.csv' encontrado.")
        return pd.DataFrame()
    
    lista_de_dfs = [pd.read_csv(f, sep=',', usecols=['cnpj_basico', 'situacao_cadastral', 'data_situacao_cadastral', 'cnae_fiscal_principal', 'municipio','razao_social'], dtype=str) for f in arquivos_csv]
    df = pd.concat(lista_de_dfs, ignore_index=True)
    
    # 3. Limpeza e conversão de tipos do DataFrame principal
    df['situacao_cadastral'] = pd.to_numeric(df['situacao_cadastral'], errors='coerce')
    df['data_situacao_cadastral'] = pd.to_datetime(df['data_situacao_cadastral'], format='%Y%m%d', errors='coerce')
    df.dropna(subset=['data_situacao_cadastral', 'situacao_cadastral'], inplace=True)
    df['municipio'] = df['municipio'].astype(str)
    df['cnae_fiscal_principal'] = df['cnae_fiscal_principal'].astype(str)

    # 4. ENRIQUECIMENTO: Juntar a descrição do CNAE ao DataFrame principal
    # Usamos um 'left' merge para manter todas as empresas, mesmo que um CNAE não seja encontrado
    df = pd.merge(df, df_cnae, left_on='cnae_fiscal_principal', right_on='cnae', how='left')
    df['descricao'].fillna('Descrição não informada', inplace=True) # Preenche CNAEs sem correspondência
    
    # 5. Criar colunas otimizadas para filtros e visualizações
    df['ano_situacao'] = df['data_situacao_cadastral'].dt.year
    df['mes_ano_situacao'] = df['data_situacao_cadastral'].dt.to_period('M')
    df['situacao_cadastral_label'] = df['situacao_cadastral'].map(MAPEAMENTO_SITUACAO).fillna('Outra')
    # **NOVA COLUNA PARA EXIBIÇÃO**
    df['cnae_descricao'] = df['cnae_fiscal_principal'] + ' - ' + df['descricao']
    
    return df

# --- Inicialização do Estado da Sessão ---
def inicializar_estado():
    if 'df_completo' not in st.session_state:
        with st.spinner("Carregando e preparando os dados... Por favor, aguarde."):
            st.session_state.df_completo = carregar_dados()
            st.session_state.df_filtrado = st.session_state.df_completo.copy()
            st.session_state.municipio_selecionado = []
            st.session_state.cnae_selecionado = []
            st.session_state.situacao_selecionada = []
            if not st.session_state.df_completo.empty:
                min_data = st.session_state.df_completo['data_situacao_cadastral'].min().date()
                max_data = st.session_state.df_completo['data_situacao_cadastral'].max().date()
                st.session_state.periodo_selecionado = (min_data, max_data)
            else:
                st.session_state.periodo_selecionado = (None, None)

inicializar_estado()
df_completo = st.session_state.df_completo

if df_completo.empty:
    st.warning("Não foi possível carregar os dados. Verifique os arquivos CSV e a configuração.")
    st.stop()

# --- Barra Lateral de Filtros (Global para todas as páginas) ---
st.sidebar.header("Filtros Globais")

# Filtro por Município
lista_municipios = sorted(df_completo['municipio'].unique())
st.session_state.municipio_selecionado = st.sidebar.multiselect(
    "Selecione o Município",
    options=lista_municipios,
    default=st.session_state.get('municipio_selecionado', [])
)

# Filtro por CNAE
lista_cnaes = sorted(df_completo['cnae_descricao'].unique())
st.session_state.cnae_selecionado = st.sidebar.multiselect(
    "Selecione o CNAE Principal",
    options=lista_cnaes,
    default=st.session_state.get('cnae_selecionado', [])
)


# Filtro por Situação Cadastral
lista_situacoes = sorted(df_completo['situacao_cadastral_label'].unique())
st.session_state.situacao_selecionada = st.sidebar.multiselect(
    "Selecione a Situação Cadastral",
    options=lista_situacoes,
    default=st.session_state.get('situacao_selecionada', [])
)

# Filtro por Período
min_data = df_completo['data_situacao_cadastral'].min().date()
max_data = df_completo['data_situacao_cadastral'].max().date()
st.session_state.periodo_selecionado = st.sidebar.date_input(
    "Selecione o Período",
    value=(st.session_state.get('periodo_selecionado', (min_data, max_data))[0], 
           st.session_state.get('periodo_selecionado', (min_data, max_data))[1]),
    min_value=min_data,
    max_value=max_data,
)

# --- Lógica de Aplicação dos Filtros ---
df_filtrado = df_completo.copy()

if st.session_state.municipio_selecionado:
    df_filtrado = df_filtrado[df_filtrado['municipio'].isin(st.session_state.municipio_selecionado)]
if st.session_state.cnae_selecionado:
    # Extrai apenas o código CNAE da seleção para o filtro
    codigos_cnae_selecionados = [item.split(' - ')[0] for item in st.session_state.cnae_selecionado]
    df_filtrado = df_filtrado[df_filtrado['cnae_fiscal_principal'].isin(codigos_cnae_selecionados)]
if st.session_state.situacao_selecionada:
    df_filtrado = df_filtrado[df_filtrado['situacao_cadastral_label'].isin(st.session_state.situacao_selecionada)]
if len(st.session_state.periodo_selecionado) == 2:
    start_date, end_date = st.session_state.periodo_selecionado
    df_filtrado = df_filtrado[(df_filtrado['data_situacao_cadastral'].dt.date >= start_date) & (df_filtrado['data_situacao_cadastral'].dt.date <= end_date)]

st.session_state.df_filtrado = df_filtrado

# --- Conteúdo da Página Principal ---
st.title("Bem-vindo ao Dashboard de Análise de Empresas (RFB)")
st.markdown("---")
st.markdown("""
Esta é a página principal da sua aplicação de análise de dados.
- **Use a barra lateral à esquerda** para navegar entre as diferentes páginas de análise.
- Os filtros que você aplicar nesta barra lateral serão **mantidos em todas as páginas**, permitindo uma análise consistente.

### Resumo dos Dados Carregados
""")
st.metric("Total de Registros Carregados", f"{len(df_completo):,}")
st.metric("Total de Registros Após Filtros", f"{len(df_filtrado):,}")
st.dataframe(df_filtrado.head())