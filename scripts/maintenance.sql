-- ============================================================================
-- SCRIPT DE MANUTENÇÃO DO BANCO DE DADOS
-- ============================================================================
--
-- Este script contém comandos para manter o banco de dados otimizado e
-- as materialized views atualizadas.
--
-- FREQUÊNCIA RECOMENDADA:
-- - Atualização de Materialized Views: DIÁRIA (de preferência à noite)
-- - VACUUM ANALYZE: SEMANAL
-- - REINDEX: MENSAL
--
-- COMO AUTOMATIZAR:
-- 1. Usar cron (Linux/Mac):
--    0 2 * * * psql -U felipe -d cnpj_db2 -f /caminho/para/maintenance.sql
--
-- 2. Usar Task Scheduler (Windows):
--    Criar tarefa agendada executando:
--    psql -U felipe -d cnpj_db2 -f C:\caminho\maintenance.sql
--
-- 3. Usar pg_cron extension do PostgreSQL:
--    Ver seção AUTOMAÇÃO abaixo
--
-- ============================================================================

-- Conectar ao banco correto
\c cnpj_db2

\echo '==================== INÍCIO DA MANUTENÇÃO ===================='
\echo ''

-- ============================================================================
-- 1. ATUALIZAR MATERIALIZED VIEWS
-- ============================================================================

\echo '🔄 Atualizando Materialized Views...'
\echo ''

-- KPIs Dashboard
\echo '  - mv_kpis_dashboard'
REFRESH MATERIALIZED VIEW public.mv_kpis_dashboard;

-- Agregação por Município (CONCURRENTLY = não bloqueia leituras)
\echo '  - mv_empresas_por_municipio'
REFRESH MATERIALIZED VIEW CONCURRENTLY public.mv_empresas_por_municipio;

-- Agregação por CNAE
\echo '  - mv_empresas_por_cnae'
REFRESH MATERIALIZED VIEW CONCURRENTLY public.mv_empresas_por_cnae;

-- Timeline
\echo '  - mv_empresas_timeline'
REFRESH MATERIALIZED VIEW CONCURRENTLY public.mv_empresas_timeline;

-- Matriz Município x CNAE
\echo '  - mv_municipio_cnae_top'
REFRESH MATERIALIZED VIEW CONCURRENTLY public.mv_municipio_cnae_top;

\echo ''
\echo '✅ Materialized Views atualizadas!'
\echo ''


-- ============================================================================
-- 2. ATUALIZAR ESTATÍSTICAS DO BANCO
-- ============================================================================

\echo '📊 Atualizando estatísticas das tabelas...'
\echo ''

-- Atualiza estatísticas da tabela principal
ANALYZE public.estabelecimentos;

-- Atualiza estatísticas da tabela CNAE
ANALYZE public.cnae;

-- Atualiza estatísticas das materialized views
ANALYZE public.mv_kpis_dashboard;
ANALYZE public.mv_empresas_por_municipio;
ANALYZE public.mv_empresas_por_cnae;
ANALYZE public.mv_empresas_timeline;
ANALYZE public.mv_municipio_cnae_top;

\echo '✅ Estatísticas atualizadas!'
\echo ''


-- ============================================================================
-- 3. VACUUM (Limpeza e Otimização)
-- ============================================================================

\echo '🧹 Executando VACUUM nas tabelas...'
\echo ''

-- VACUUM recupera espaço de tuplas deletadas/atualizadas
-- ANALYZE atualiza estatísticas para o query planner

VACUUM ANALYZE public.estabelecimentos;
VACUUM ANALYZE public.cnae;

\echo '✅ VACUUM completo!'
\echo ''


-- ============================================================================
-- 4. VERIFICAR SAÚDE DOS ÍNDICES
-- ============================================================================

\echo '🔍 Verificando índices não utilizados...'
\echo ''

-- Lista índices que nunca foram usados (candidatos para remoção)
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan AS "Usos do Índice",
    pg_size_pretty(pg_relation_size(indexrelid)) AS "Tamanho"
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND idx_scan = 0
  AND indexrelid NOT IN (
      SELECT indexrelid
      FROM pg_index, pg_class
      WHERE pg_index.indrelid = pg_class.oid
        AND indisprimary
  )
ORDER BY pg_relation_size(indexrelid) DESC;

\echo ''
\echo 'ℹ️  Índices com "Usos do Índice" = 0 não estão sendo utilizados'
\echo ''


-- ============================================================================
-- 5. VERIFICAR INCHAÇO (BLOAT) DAS TABELAS
-- ============================================================================

\echo '📏 Verificando inchaço das tabelas...'
\echo ''

-- Query simplificada para detectar bloat
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS "Tamanho Total",
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS "Tamanho Tabela",
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) -
                   pg_relation_size(schemaname||'.'||tablename)) AS "Tamanho Índices"
FROM pg_tables
WHERE schemaname = 'public'
  AND tablename IN ('estabelecimentos', 'cnae')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

\echo ''


-- ============================================================================
-- 6. ESTATÍSTICAS DE PERFORMANCE
-- ============================================================================

\echo '📈 Estatísticas de queries lentas (top 5)...'
\echo ''

-- Requer pg_stat_statements extension
-- Para habilitar: CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

SELECT
    LEFT(query, 60) AS "Query (60 chars)",
    calls AS "Chamadas",
    ROUND(total_exec_time::numeric, 2) AS "Tempo Total (ms)",
    ROUND(mean_exec_time::numeric, 2) AS "Tempo Médio (ms)",
    ROUND((100 * total_exec_time / SUM(total_exec_time) OVER())::numeric, 2) AS "% do Total"
FROM pg_stat_statements
WHERE query NOT LIKE '%pg_stat_statements%'
  AND query NOT LIKE 'REFRESH MATERIALIZED VIEW%'
ORDER BY total_exec_time DESC
LIMIT 5;

\echo ''


-- ============================================================================
-- 7. INFORMAÇÕES DE ÚLTIMA ATUALIZAÇÃO
-- ============================================================================

\echo '🕒 Última atualização das Materialized Views:'
\echo ''

SELECT
    'mv_kpis_dashboard' AS "View",
    atualizado_em AS "Última Atualização"
FROM public.mv_kpis_dashboard
UNION ALL
SELECT 'mv_empresas_por_municipio', atualizado_em
FROM public.mv_empresas_por_municipio LIMIT 1
UNION ALL
SELECT 'mv_empresas_por_cnae', atualizado_em
FROM public.mv_empresas_por_cnae LIMIT 1
UNION ALL
SELECT 'mv_empresas_timeline', atualizado_em
FROM public.mv_empresas_timeline LIMIT 1
UNION ALL
SELECT 'mv_municipio_cnae_top', atualizado_em
FROM public.mv_municipio_cnae_top LIMIT 1
ORDER BY "Última Atualização" DESC;

\echo ''


-- ============================================================================
-- 8. TAMANHO TOTAL DO BANCO
-- ============================================================================

\echo '💾 Tamanho do banco de dados:'
\echo ''

SELECT
    pg_database.datname AS "Banco",
    pg_size_pretty(pg_database_size(pg_database.datname)) AS "Tamanho"
FROM pg_database
WHERE datname = 'cnpj_db2';

\echo ''


-- ============================================================================
-- 9. CONEXÕES ATIVAS
-- ============================================================================

\echo '👥 Conexões ativas:'
\echo ''

SELECT
    COUNT(*) AS "Total de Conexões",
    COUNT(*) FILTER (WHERE state = 'active') AS "Ativas",
    COUNT(*) FILTER (WHERE state = 'idle') AS "Ociosas"
FROM pg_stat_activity
WHERE datname = 'cnpj_db2';

\echo ''


-- ============================================================================
-- MANUTENÇÃO MENSAL (Descomente para executar)
-- ============================================================================

-- Executar uma vez por mês ou quando houver degradação de performance

-- \echo '🔧 MANUTENÇÃO MENSAL: Reindexando tabelas...'
-- \echo ''
--
-- -- Reindexação da tabela estabelecimentos
-- REINDEX TABLE public.estabelecimentos;
--
-- -- Reindexação da tabela cnae
-- REINDEX TABLE public.cnae;
--
-- -- Reindexação das materialized views
-- REINDEX TABLE public.mv_empresas_por_municipio;
-- REINDEX TABLE public.mv_empresas_por_cnae;
-- REINDEX TABLE public.mv_empresas_timeline;
-- REINDEX TABLE public.mv_municipio_cnae_top;
--
-- \echo '✅ Reindexação completa!'
-- \echo ''


-- ============================================================================
-- AUTOMAÇÃO COM PG_CRON (Avançado)
-- ============================================================================

-- Para automatizar a manutenção diretamente no PostgreSQL:

-- 1. Instalar pg_cron extension:
--    CREATE EXTENSION IF NOT EXISTS pg_cron;

-- 2. Adicionar job para atualizar MVs diariamente às 2h da manhã:
--
-- SELECT cron.schedule(
--     'refresh-materialized-views-daily',
--     '0 2 * * *',  -- Cron: 2h da manhã todos os dias
--     $$
--     REFRESH MATERIALIZED VIEW public.mv_kpis_dashboard;
--     REFRESH MATERIALIZED VIEW CONCURRENTLY public.mv_empresas_por_municipio;
--     REFRESH MATERIALIZED VIEW CONCURRENTLY public.mv_empresas_por_cnae;
--     REFRESH MATERIALIZED VIEW CONCURRENTLY public.mv_empresas_timeline;
--     REFRESH MATERIALIZED VIEW CONCURRENTLY public.mv_municipio_cnae_top;
--     ANALYZE public.estabelecimentos;
--     ANALYZE public.cnae;
--     $$
-- );

-- 3. Adicionar job semanal de VACUUM (Domingo, 3h da manhã):
--
-- SELECT cron.schedule(
--     'vacuum-weekly',
--     '0 3 * * 0',  -- Domingo 3h
--     $$
--     VACUUM ANALYZE public.estabelecimentos;
--     VACUUM ANALYZE public.cnae;
--     $$
-- );

-- 4. Listar jobs agendados:
--    SELECT * FROM cron.job;

-- 5. Remover job:
--    SELECT cron.unschedule('nome-do-job');


-- ============================================================================
-- FIM DO SCRIPT
-- ============================================================================

\echo '==================== MANUTENÇÃO CONCLUÍDA ===================='
\echo ''
\echo '✅ Banco de dados otimizado!'
\echo '⚡ Dashboard deve estar com performance máxima.'
\echo ''
