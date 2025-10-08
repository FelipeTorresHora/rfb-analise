-- ============================================================================
-- SCRIPT DE CRIAÇÃO DE MATERIALIZED VIEWS - CORRIGIDO
-- ============================================================================
--
-- ESTRUTURA CORRETA DO BANCO:
-- - estabelecimentos: dados principais (cnpj, situacao_cadastral, municipio, etc)
-- - estabelecimento_cnaes: CNAEs (cnpj, cnae_fiscal)
-- - Relacionamento via coluna 'cnpj'
--
-- ============================================================================

-- Conectar ao banco correto
\c cnpj_db2

-- ============================================================================
-- 1. MATERIALIZED VIEW: KPIs PRINCIPAIS DO DASHBOARD
-- ============================================================================

DROP MATERIALIZED VIEW IF EXISTS public.mv_kpis_dashboard CASCADE;

CREATE MATERIALIZED VIEW public.mv_kpis_dashboard AS
SELECT
    COUNT(*) AS total_empresas,

    -- Empresas ativas (situacao_cadastral = 2)
    SUM(CASE WHEN situacao_cadastral = 2 THEN 1 ELSE 0 END) AS empresas_ativas,

    -- Empresas baixadas (situacao_cadastral = 8)
    SUM(CASE WHEN situacao_cadastral = 8 THEN 1 ELSE 0 END) AS empresas_baixadas,

    -- Empresas suspensas (situacao_cadastral = 3)
    SUM(CASE WHEN situacao_cadastral = 3 THEN 1 ELSE 0 END) AS empresas_suspensas,

    -- Empresas inaptas (situacao_cadastral = 4)
    SUM(CASE WHEN situacao_cadastral = 4 THEN 1 ELSE 0 END) AS empresas_inaptas,

    -- Percentual de ativas
    ROUND(
        (SUM(CASE WHEN situacao_cadastral = 2 THEN 1 ELSE 0 END)::NUMERIC / COUNT(*)::NUMERIC) * 100,
        2
    ) AS percent_ativas,

    -- Última atualização
    NOW() AS atualizado_em

FROM public.estabelecimentos
WHERE situacao_cadastral IS NOT NULL;

-- Criar índice na materialized view
CREATE UNIQUE INDEX idx_mv_kpis_atualizado
ON public.mv_kpis_dashboard(atualizado_em);

COMMENT ON MATERIALIZED VIEW public.mv_kpis_dashboard IS
'KPIs principais do dashboard - Atualizar diariamente com REFRESH MATERIALIZED VIEW';


-- ============================================================================
-- 2. MATERIALIZED VIEW: AGREGAÇÃO POR MUNICÍPIO
-- ============================================================================

DROP MATERIALIZED VIEW IF EXISTS public.mv_empresas_por_municipio CASCADE;

CREATE MATERIALIZED VIEW public.mv_empresas_por_municipio AS
SELECT
    municipio,
    COUNT(*) AS total_empresas,

    SUM(CASE WHEN situacao_cadastral = 2 THEN 1 ELSE 0 END) AS empresas_ativas,
    SUM(CASE WHEN situacao_cadastral = 8 THEN 1 ELSE 0 END) AS empresas_baixadas,
    SUM(CASE WHEN situacao_cadastral = 3 THEN 1 ELSE 0 END) AS empresas_suspensas,
    SUM(CASE WHEN situacao_cadastral = 4 THEN 1 ELSE 0 END) AS empresas_inaptas,

    -- Percentual de ativas
    ROUND(
        (SUM(CASE WHEN situacao_cadastral = 2 THEN 1 ELSE 0 END)::NUMERIC / COUNT(*)::NUMERIC) * 100,
        2
    ) AS percent_ativas,

    NOW() AS atualizado_em

FROM public.estabelecimentos
WHERE municipio IS NOT NULL
  AND situacao_cadastral IS NOT NULL
GROUP BY municipio;

-- Índices na materialized view
CREATE UNIQUE INDEX idx_mv_municipio_pk
ON public.mv_empresas_por_municipio(municipio);

CREATE INDEX idx_mv_municipio_total
ON public.mv_empresas_por_municipio(total_empresas DESC);

COMMENT ON MATERIALIZED VIEW public.mv_empresas_por_municipio IS
'Agregação de empresas por município - Atualizar diariamente';


-- ============================================================================
-- 3. MATERIALIZED VIEW: AGREGAÇÃO POR CNAE
-- ============================================================================

DROP MATERIALIZED VIEW IF EXISTS public.mv_empresas_por_cnae CASCADE;

CREATE MATERIALIZED VIEW public.mv_empresas_por_cnae AS
SELECT
    ec.cnae_fiscal,
    COUNT(DISTINCT e.cnpj) AS total_empresas,

    SUM(CASE WHEN e.situacao_cadastral = 2 THEN 1 ELSE 0 END) AS empresas_ativas,
    SUM(CASE WHEN e.situacao_cadastral = 8 THEN 1 ELSE 0 END) AS empresas_baixadas,

    -- Percentual de ativas
    ROUND(
        (SUM(CASE WHEN e.situacao_cadastral = 2 THEN 1 ELSE 0 END)::NUMERIC / 
         COUNT(DISTINCT e.cnpj)::NUMERIC) * 100,
        2
    ) AS percent_ativas,

    NOW() AS atualizado_em

FROM public.estabelecimento_cnaes ec
INNER JOIN public.estabelecimentos e ON ec.cnpj = e.cnpj
WHERE ec.cnae_fiscal IS NOT NULL
  AND e.situacao_cadastral IS NOT NULL
GROUP BY ec.cnae_fiscal;

-- Índices na materialized view
CREATE UNIQUE INDEX idx_mv_cnae_pk
ON public.mv_empresas_por_cnae(cnae_fiscal);

CREATE INDEX idx_mv_cnae_total
ON public.mv_empresas_por_cnae(total_empresas DESC);

COMMENT ON MATERIALIZED VIEW public.mv_empresas_por_cnae IS
'Agregação de empresas por CNAE - Atualizar diariamente';


-- ============================================================================
-- 4. MATERIALIZED VIEW: EVOLUÇÃO TEMPORAL (TIMELINE)
-- ============================================================================

DROP MATERIALIZED VIEW IF EXISTS public.mv_empresas_timeline CASCADE;

CREATE MATERIALIZED VIEW public.mv_empresas_timeline AS
SELECT
    DATE_TRUNC('month', data_situacao_cadastral::date) AS mes_ano,
    EXTRACT(YEAR FROM data_situacao_cadastral::date) AS ano,
    EXTRACT(MONTH FROM data_situacao_cadastral::date) AS mes,

    COUNT(*) AS total_empresas,

    SUM(CASE WHEN situacao_cadastral = 2 THEN 1 ELSE 0 END) AS aberturas,
    SUM(CASE WHEN situacao_cadastral = 8 THEN 1 ELSE 0 END) AS baixas,

    NOW() AS atualizado_em

FROM public.estabelecimentos
WHERE data_situacao_cadastral IS NOT NULL
  AND situacao_cadastral IS NOT NULL
GROUP BY DATE_TRUNC('month', data_situacao_cadastral::date),
         EXTRACT(YEAR FROM data_situacao_cadastral::date),
         EXTRACT(MONTH FROM data_situacao_cadastral::date)
ORDER BY mes_ano;

-- Índices na materialized view
CREATE UNIQUE INDEX idx_mv_timeline_pk
ON public.mv_empresas_timeline(mes_ano);

CREATE INDEX idx_mv_timeline_ano
ON public.mv_empresas_timeline(ano);

COMMENT ON MATERIALIZED VIEW public.mv_empresas_timeline IS
'Evolução temporal mensal de empresas - Atualizar diariamente';


-- ============================================================================
-- 5. MATERIALIZED VIEW: MATRIZ MUNICÍPIO x CNAE (TOP 1000)
-- ============================================================================

DROP MATERIALIZED VIEW IF EXISTS public.mv_municipio_cnae_top CASCADE;

CREATE MATERIALIZED VIEW public.mv_municipio_cnae_top AS
SELECT
    e.municipio,
    ec.cnae_fiscal,
    COUNT(DISTINCT e.cnpj) AS total_empresas,

    SUM(CASE WHEN e.situacao_cadastral = 2 THEN 1 ELSE 0 END) AS empresas_ativas,

    NOW() AS atualizado_em

FROM public.estabelecimentos e
INNER JOIN public.estabelecimento_cnaes ec ON e.cnpj = ec.cnpj
WHERE e.municipio IS NOT NULL
  AND ec.cnae_fiscal IS NOT NULL
  AND e.situacao_cadastral IS NOT NULL
GROUP BY e.municipio, ec.cnae_fiscal
ORDER BY total_empresas DESC
LIMIT 1000;

-- Índices na materialized view
CREATE INDEX idx_mv_mun_cnae_municipio
ON public.mv_municipio_cnae_top(municipio);

CREATE INDEX idx_mv_mun_cnae_cnae
ON public.mv_municipio_cnae_top(cnae_fiscal);

CREATE INDEX idx_mv_mun_cnae_total
ON public.mv_municipio_cnae_top(total_empresas DESC);

COMMENT ON MATERIALIZED VIEW public.mv_municipio_cnae_top IS
'Top 1000 combinações município x CNAE - Atualizar diariamente';


-- ============================================================================
-- 6. ATUALIZAR ESTATÍSTICAS DAS MATERIALIZED VIEWS
-- ============================================================================

ANALYZE public.mv_kpis_dashboard;
ANALYZE public.mv_empresas_por_municipio;
ANALYZE public.mv_empresas_por_cnae;
ANALYZE public.mv_empresas_timeline;
ANALYZE public.mv_municipio_cnae_top;


-- ============================================================================
-- 7. VERIFICAR TAMANHO DAS MATERIALIZED VIEWS
-- ============================================================================

SELECT
    schemaname,
    matviewname AS viewname,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||matviewname)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||matviewname)) AS view_size
FROM pg_matviews
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||matviewname) DESC;


-- ============================================================================
-- 8. VERIFICAR ÚLTIMA ATUALIZAÇÃO DAS VIEWS
-- ============================================================================

SELECT 'mv_kpis_dashboard' AS view_name, atualizado_em FROM public.mv_kpis_dashboard
UNION ALL
SELECT 'mv_empresas_por_municipio', atualizado_em FROM public.mv_empresas_por_municipio LIMIT 1
UNION ALL
SELECT 'mv_empresas_por_cnae', atualizado_em FROM public.mv_empresas_por_cnae LIMIT 1
UNION ALL
SELECT 'mv_empresas_timeline', atualizado_em FROM public.mv_empresas_timeline LIMIT 1
UNION ALL
SELECT 'mv_municipio_cnae_top', atualizado_em FROM public.mv_municipio_cnae_top LIMIT 1
ORDER BY atualizado_em DESC;


-- ============================================================================
-- FIM DO SCRIPT
-- ============================================================================

\echo '✅ Materialized Views criadas com sucesso!'
\echo '⚡ KPIs e agregações agora são SUPER rápidos!'
\echo '🔄 Lembre-se de atualizar as views periodicamente'