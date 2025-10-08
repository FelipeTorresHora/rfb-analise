import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.pool import QueuePool
from typing import Optional, List, Tuple, Dict
from datetime import date, datetime

# ==================== CONNECTION POOLING ====================

@st.cache_resource
def get_engine():
    """
    Cria e retorna um engine SQLAlchemy com connection pooling.
    
    Returns:
        sqlalchemy.engine.Engine: Engine com pool de conexões
    """
    try:
        connection_string = (
            f"postgresql://{st.secrets['postgres']['user']}:"
            f"{st.secrets['postgres']['password']}@"
            f"{st.secrets['postgres']['host']}:"
            f"{st.secrets['postgres']['port']}/"
            f"{st.secrets['postgres']['dbname']}"
        )
        
        engine = create_engine(
            connection_string,
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
            echo=False
        )
        
        return engine
    except Exception as e:
        st.error(f"❌ Erro ao criar engine de conexão: {e}")
        raise

# ==================== MAPEAMENTO DE MUNICÍPIOS ====================

@st.cache_data(ttl=86400)  # Cache por 24 horas
def carregar_mapeamento_municipios() -> Dict[str, Dict[str, str]]:
    """
    Carrega o CSV de municípios e retorna dicionários para mapeamento.
    
    Returns:
        dict: {'codigo_para_nome': {}, 'nome_para_codigo': {}}
    """
    try:
        df = pd.read_csv('dados/municipios.csv', sep=';', header=None, 
                        names=['codigo', 'nome'], dtype={'codigo': str})
        
        # Remove zeros à esquerda dos códigos para compatibilidade
        df['codigo'] = df['codigo'].str.lstrip('0')
        
        # Dicionário codigo -> nome
        codigo_para_nome = dict(zip(df['codigo'], df['nome']))
        
        # Dicionário nome -> codigo
        nome_para_codigo = dict(zip(df['nome'], df['codigo']))
        
        return {
            'codigo_para_nome': codigo_para_nome,
            'nome_para_codigo': nome_para_codigo
        }
    except Exception as e:
        st.error(f"Erro ao carregar mapeamento de municípios: {e}")
        return {'codigo_para_nome': {}, 'nome_para_codigo': {}}

# ==================== FUNÇÕES AUXILIARES DE DATA ====================

def converter_yyyymmdd_para_date(yyyymmdd_str: str) -> Optional[date]:
    """
    Converte string no formato YYYYMMDD para objeto date.
    """
    try:
        if not yyyymmdd_str or yyyymmdd_str == '0':
            return None
        return datetime.strptime(str(yyyymmdd_str), '%Y%m%d').date()
    except:
        return None

def date_para_yyyymmdd(data: date) -> str:
    """
    Converte objeto date para string YYYYMMDD.
    """
    return data.strftime('%Y%m%d')

# ==================== SOLUÇÃO 1 & 2: QUERIES FILTRADAS COM JOIN ====================

def carregar_dados_filtrados(
    municipios: Optional[List[str]] = None,
    cnaes: Optional[List[str]] = None,
    situacoes: Optional[List[int]] = None,
    data_inicio: Optional[date] = None,
    data_fim: Optional[date] = None,
    limit: int = 2000000  # Aumentado para 2 milhões
) -> pd.DataFrame:
    """
    ⚡ OTIMIZADO: Carrega dados COM FILTROS aplicados no banco de dados.
    FILTRO PADRÃO: UF = 'RS' e situacao_cadastral = 2 (Ativa)
    
    Args:
        municipios: Lista de NOMES de municípios para filtrar
        cnaes: Lista de códigos CNAE para filtrar
        situacoes: Lista de códigos de situação cadastral
        data_inicio: Data inicial do período
        data_fim: Data final do período
        limit: Número máximo de registros (padrão: 2 milhões)
    
    Returns:
        pd.DataFrame: DataFrame com dados filtrados
    """
    try:
        engine = get_engine()
        mapeamento = carregar_mapeamento_municipios()
        nome_para_codigo = mapeamento['nome_para_codigo']
        codigo_para_nome = mapeamento['codigo_para_nome']
        
        # Query base com filtro FIXO para RS e Ativa
        query = """
        SELECT e.cnpj AS cnpj_basico,
               e.situacao_cadastral,
               e.data_situacao_cadastral,
               e.municipio,
               e.uf,
               ec.cnae
        FROM public.estabelecimentos e
        LEFT JOIN public.estabelecimento_cnaes ec
          ON e.cnpj = ec.cnpj
        WHERE e.uf = 'RS'
          AND e.situacao_cadastral = 2
          AND e.data_situacao_cadastral IS NOT NULL
          AND e.data_situacao_cadastral != '0'
        """
        
        params = {}
        
        # Converter nomes de municípios para códigos
        if municipios and len(municipios) > 0:
            codigos_municipios = []
            for nome in municipios:
                codigo = nome_para_codigo.get(nome)
                if codigo:
                    codigos_municipios.append(int(codigo))
            
            if codigos_municipios:
                query += " AND e.municipio = ANY(:municipios)"
                params['municipios'] = codigos_municipios
        
        # Filtro de CNAEs
        if cnaes and len(cnaes) > 0:
            query += " AND ec.cnae = ANY(:cnaes)"
            params['cnaes'] = cnaes
        
        # Filtro adicional de situações (caso queira filtrar além da Ativa)
        if situacoes and len(situacoes) > 0:
            query += " AND e.situacao_cadastral = ANY(:situacoes)"
            params['situacoes'] = situacoes
        
        # Filtro de data
        if data_inicio and data_fim:
            data_inicio_yyyymmdd = date_para_yyyymmdd(data_inicio)
            data_fim_yyyymmdd = date_para_yyyymmdd(data_fim)
            query += " AND e.data_situacao_cadastral::text BETWEEN :data_inicio AND :data_fim"
            params['data_inicio'] = data_inicio_yyyymmdd
            params['data_fim'] = data_fim_yyyymmdd
        
        query += " LIMIT :limit"
        params['limit'] = limit
        
        df = pd.read_sql_query(text(query), engine, params=params)
        
        # Pós-processamento
        if not df.empty and 'data_situacao_cadastral' in df.columns:
            df['data_situacao_cadastral'] = df['data_situacao_cadastral'].apply(
                lambda x: converter_yyyymmdd_para_date(str(x))
            )
            df = df[df['data_situacao_cadastral'].notna()]
            
            # Adicionar nome do município
            df['municipio_nome'] = df['municipio'].astype(str).str.lstrip('0').map(codigo_para_nome)
            df['municipio_nome'] = df['municipio_nome'].fillna('Município ' + df['municipio'].astype(str))
        
        return df
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar dados filtrados: {e}")
        import traceback
        st.code(traceback.format_exc())
        return pd.DataFrame()

def carregar_opcoes_filtros() -> dict:
    """
    ⚡ OTIMIZADO: Carrega apenas as opções únicas para os filtros.
    FILTRADO PARA: UF = 'RS' e situacao_cadastral = 2
    
    Returns:
        dict: Dicionário com listas de opções (municípios por nome)
    """
    try:
        engine = get_engine()
        mapeamento = carregar_mapeamento_municipios()
        codigo_para_nome = mapeamento['codigo_para_nome']
        
        # Filtro base para RS e Ativa
        filtro_base = "WHERE uf = 'RS' AND situacao_cadastral = 2"
        
        # Query de municípios com filtro
        query_municipios = f"""
        SELECT DISTINCT municipio
        FROM public.estabelecimentos
        {filtro_base}
        AND municipio IS NOT NULL
        ORDER BY municipio
        LIMIT 1000
        """
        
        # Query de CNAEs com JOIN para pegar apenas de empresas RS ativas
        query_cnaes = f"""
        SELECT DISTINCT ec.cnae
        FROM public.estabelecimento_cnaes ec
        INNER JOIN public.estabelecimentos e ON ec.cnpj = e.cnpj
        {filtro_base}
        AND ec.cnae IS NOT NULL
        ORDER BY ec.cnae
        LIMIT 1000
        """
        
        # Situações (mesmo com filtro, retorna as disponíveis)
        query_situacoes = f"""
        SELECT DISTINCT situacao_cadastral
        FROM public.estabelecimentos
        {filtro_base}
        ORDER BY situacao_cadastral
        """
        
        # Query de datas
        query_datas = f"""
        SELECT
          MIN(data_situacao_cadastral::text) AS min_data,
          MAX(data_situacao_cadastral::text) AS max_data
        FROM public.estabelecimentos
        {filtro_base}
        AND data_situacao_cadastral IS NOT NULL
        AND LENGTH(data_situacao_cadastral::text) = 8
        AND data_situacao_cadastral::text ~ '^[0-9]{8}$'
        """
        
        df_municipios = pd.read_sql_query(query_municipios, engine)
        df_cnaes = pd.read_sql_query(query_cnaes, engine)
        df_situacoes = pd.read_sql_query(query_situacoes, engine)
        df_datas = pd.read_sql_query(query_datas, engine)
        
        # Converter códigos de municípios para nomes
        municipios_nomes = []
        for codigo in df_municipios['municipio']:
            codigo_str = str(codigo).lstrip('0')
            nome = codigo_para_nome.get(codigo_str, f"Código {codigo}")
            municipios_nomes.append(nome)
        
        municipios_nomes = sorted(set(municipios_nomes))
        
        # Converte datas YYYYMMDD
        min_data = None
        max_data = None
        if not df_datas.empty:
            min_data_str = df_datas['min_data'].iloc[0]
            max_data_str = df_datas['max_data'].iloc[0]
            min_data = converter_yyyymmdd_para_date(min_data_str)
            max_data = converter_yyyymmdd_para_date(max_data_str)
        
        return {
            'municipios': municipios_nomes,
            'cnaes': df_cnaes['cnae'].tolist(),
            'situacoes': df_situacoes['situacao_cadastral'].tolist(),
            'min_data': min_data,
            'max_data': max_data
        }
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar opções de filtros: {e}")
        import traceback
        st.code(traceback.format_exc())
        return {
            'municipios': [],
            'cnaes': [],
            'situacoes': [],
            'min_data': None,
            'max_data': None
        }

# ==================== SOLUÇÃO 4: MATERIALIZED VIEWS ====================

def carregar_kpis() -> dict:
    """
    ⚡ SUPER RÁPIDO: Carrega KPIs da materialized view.
    """
    try:
        engine = get_engine()
        
        # Tenta materialized view primeiro
        query_mv = """
        SELECT
          total_empresas,
          empresas_ativas,
          empresas_baixadas,
          percent_ativas
        FROM public.mv_kpis_dashboard
        LIMIT 1
        """
        
        try:
            df = pd.read_sql_query(query_mv, engine)
            if not df.empty:
                return df.iloc[0].to_dict()
        except:
            pass
        
        # Fallback: query com filtro RS
        query_fallback = """
        SELECT
          COUNT(*) AS total_empresas,
          SUM(CASE WHEN situacao_cadastral = 2 THEN 1 ELSE 0 END) AS empresas_ativas,
          SUM(CASE WHEN situacao_cadastral = 8 THEN 1 ELSE 0 END) AS empresas_baixadas
        FROM public.estabelecimentos
        WHERE uf = 'RS' AND situacao_cadastral IS NOT NULL
        """
        
        df = pd.read_sql_query(query_fallback, engine)
        if not df.empty:
            total = df['total_empresas'].iloc[0]
            ativas = df['empresas_ativas'].iloc[0]
            baixadas = df['empresas_baixadas'].iloc[0]
            return {
                'total_empresas': total,
                'empresas_ativas': ativas,
                'empresas_baixadas': baixadas,
                'percent_ativas': (ativas / total * 100) if total > 0 else 0
            }
        
        return {
            'total_empresas': 0,
            'empresas_ativas': 0,
            'empresas_baixadas': 0,
            'percent_ativas': 0
        }
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar KPIs: {e}")
        return {
            'total_empresas': 0,
            'empresas_ativas': 0,
            'empresas_baixadas': 0,
            'percent_ativas': 0
        }

def carregar_agregacao_municipio() -> pd.DataFrame:
    """
    ⚡ SUPER RÁPIDO: Carrega agregação por município.
    FILTRADO PARA RS.
    """
    try:
        engine = get_engine()
        
        query_fallback = """
        SELECT
          municipio,
          COUNT(*) AS total_empresas,
          SUM(CASE WHEN situacao_cadastral = 2 THEN 1 ELSE 0 END) AS empresas_ativas,
          SUM(CASE WHEN situacao_cadastral = 8 THEN 1 ELSE 0 END) AS empresas_baixadas
        FROM public.estabelecimentos
        WHERE uf = 'RS' AND municipio IS NOT NULL
        GROUP BY municipio
        ORDER BY total_empresas DESC
        """
        
        df = pd.read_sql_query(query_fallback, engine)
        
        # Adicionar nomes dos municípios
        if not df.empty:
            mapeamento = carregar_mapeamento_municipios()
            codigo_para_nome = mapeamento['codigo_para_nome']
            df['municipio_nome'] = df['municipio'].astype(str).str.lstrip('0').map(codigo_para_nome)
            df['municipio_nome'] = df['municipio_nome'].fillna('Município ' + df['municipio'].astype(str))
        
        return df
        
    except Exception as e:
        st.error(f"❌ Erro ao carregar agregação por município: {e}")
        return pd.DataFrame()

# ==================== FUNÇÕES AUXILIARES ====================

def testar_conexao() -> bool:
    """Testa a conexão com o banco de dados."""
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        st.error(f"❌ Erro ao testar conexão: {e}")
        return False

def obter_metadados() -> dict:
    """Carrega metadados rápidos do banco (filtrado para RS)."""
    try:
        engine = get_engine()
        
        query = """
        SELECT
          COUNT(*) AS total_registros,
          COUNT(DISTINCT municipio) AS total_municipios
        FROM public.estabelecimentos
        WHERE uf = 'RS' AND situacao_cadastral = 2
        """
        
        query_cnaes = """
        SELECT COUNT(DISTINCT ec.cnae) AS total_cnaes
        FROM public.estabelecimento_cnaes ec
        INNER JOIN public.estabelecimentos e ON ec.cnpj = e.cnpj
        WHERE e.uf = 'RS' AND e.situacao_cadastral = 2
        """
        
        df = pd.read_sql_query(query, engine)
        df_cnaes = pd.read_sql_query(query_cnaes, engine)
        
        if not df.empty:
            result = df.iloc[0].to_dict()
            if not df_cnaes.empty:
                result['total_cnaes'] = df_cnaes['total_cnaes'].iloc[0]
            return result
        
        return {}
        
    except Exception as e:
        st.error(f"❌ Erro ao obter metadados: {e}")
        return {}
