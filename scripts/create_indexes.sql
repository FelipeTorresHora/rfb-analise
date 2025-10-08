-- ============================================================================
-- SCRIPT DE CRIAÇÃO DE ÍNDICES - CORRIGIDO
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
-- 1. ÍNDICES NA TABELA ESTABELECIMENTOS
-- ============================================================================

-- Índice na chave primária CNPJ (fundamental para JOINs)
CREATE INDEX IF NOT EXISTS idx_estabelecimentos_cnpj
ON public.estabelecimentos(cnpj);

-- Índice para filtros por município
CREATE INDEX IF NOT EXISTS idx_estabelecimentos_municipio
ON public.estabelecimentos(municipio);

-- Índice para filtros por situação cadastral
CREATE INDEX IF NOT EXISTS idx_estabelecimentos_situacao_cadastral
ON public.estabelecimentos(situacao_cadastral);

-- Índice para ordenação e busca por razão social
CREATE INDEX IF NOT EXISTS idx_estabelecimentos_razao_social
ON public.estabelecimentos(razao_social);

-- BRIN para data (eficiente para dados ordenados temporalmente)
CREATE INDEX IF NOT EXISTS idx_estabelecimentos_data_situacao_brin
ON public.estabelecimentos USING BRIN (data_situacao_cadastral);


-- ============================================================================
-- 2. ÍNDICES COMPOSTOS NA TABELA ESTABELECIMENTOS
-- ============================================================================

-- Índice composto: município + situação
CREATE INDEX IF NOT EXISTS idx_estabelecimentos_municipio_situacao
ON public.estabelecimentos(municipio, situacao_cadastral);

-- Índice composto: situação + data
CREATE INDEX IF NOT EXISTS idx_estabelecimentos_situacao_data
ON public.estabelecimentos(situacao_cadastral, data_situacao_cadastral);


-- ============================================================================
-- 3. ÍNDICES PARCIAIS (Conditional) NA TABELA ESTABELECIMENTOS
-- ============================================================================

-- Índice apenas para estabelecimentos ATIVOS (situacao_cadastral = 2)
CREATE INDEX IF NOT EXISTS idx_estabelecimentos_ativos
ON public.estabelecimentos(municipio, cnpj)
WHERE situacao_cadastral = 2;

-- Índice apenas para estabelecimentos BAIXADOS (situacao_cadastral = 8)
CREATE INDEX IF NOT EXISTS idx_estabelecimentos_baixados
ON public.estabelecimentos(municipio, cnpj)
WHERE situacao_cadastral = 8;


-- ============================================================================
-- 4. ÍNDICES NA TABELA ESTABELECIMENTO_CNAES
-- ============================================================================

-- Índice na chave estrangeira CNPJ (CRÍTICO para JOINs)
CREATE INDEX IF NOT EXISTS idx_estabelecimento_cnaes_cnpj
ON public.estabelecimento_cnaes(cnpj);

-- Índice no código CNAE
CREATE INDEX IF NOT EXISTS idx_estabelecimento_cnaes_cnae_fiscal
ON public.estabelecimento_cnaes(cnae_fiscal);

-- Índice composto: CNPJ + CNAE (para queries que filtram ambos)
CREATE INDEX IF NOT EXISTS idx_estabelecimento_cnaes_cnpj_cnae
ON public.estabelecimento_cnaes(cnpj, cnae_fiscal);


-- ============================================================================
-- 5. ATUALIZAR ESTATÍSTICAS DO BANCO
-- ============================================================================

ANALYZE public.estabelecimentos;
ANALYZE public.estabelecimento_cnaes;


-- ============================================================================
-- 6. VERIFICAR ÍNDICES CRIADOS
-- ============================================================================

SELECT
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename IN ('estabelecimentos', 'estabelecimento_cnaes')
  AND schemaname = 'public'
ORDER BY tablename, indexname;


-- ============================================================================
-- 7. VERIFICAR TAMANHO DOS ÍNDICES
-- ============================================================================

SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
  AND tablename IN ('estabelecimentos', 'estabelecimento_cnaes')
ORDER BY pg_relation_size(indexrelid) DESC;


-- ============================================================================
-- DICAS DE MANUTENÇÃO
-- ============================================================================

-- 1. REINDEXAÇÃO (executar mensalmente)
--    REINDEX TABLE public.estabelecimentos;
--    REINDEX TABLE public.estabelecimento_cnaes;

-- 2. VACUUM (libera espaço e atualiza estatísticas)
--    VACUUM ANALYZE public.estabelecimentos;
--    VACUUM ANALYZE public.estabelecimento_cnaes;

-- 3. MONITORAR USO DOS ÍNDICES
--    SELECT * FROM pg_stat_user_indexes WHERE schemaname = 'public';

-- ============================================================================
-- FIM DO SCRIPT
-- ============================================================================

\echo '✅ Índices criados com sucesso!'
\echo '⚡ Performance do dashboard deve melhorar significativamente.'
\echo 'Execute o script de materialized views para ganhos adicionais.'