# core/search.py

import time
import unicodedata
from typing import Dict, List, Set, Tuple, Any
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from ddgs import DDGS

# --- Constantes de Configuração ---
# Boa prática: Centralizar configurações facilita a manutenção.
NUM_THREADS = 4             # Número de buscas paralelas. Ajuste conforme a capacidade da sua máquina.
TEMPO_ESPERA = 1            # Pausa em segundos entre as requisições para evitar bloqueios.
MAX_RESULTS_PER_SEARCH = 3  # Quantos resultados do Google analisar por empresa.
VALIDATION_THRESHOLD = 0.2  # Quão "parecido" o resultado da busca deve ser com os dados da empresa.


# ==================== Funções de Validação com Dados da RFB ====================

def normalizar_texto(texto: Any) -> str:
    """
    Normaliza texto para comparação (remove acentos, converte para minúsculo).
    # Boa prática: Usar 'Any' para tipagem de entrada, pois dados de DataFrame podem variar.
    """
    if pd.isna(texto):
        return ""
    
    texto = str(texto)
    # Decompõe caracteres acentuados (ex: 'á' -> 'a' + ´)
    texto = unicodedata.normalize('NFD', texto)
    # Remove os acentos (caracteres da categoria 'Mn')
    texto = ''.join(c for c in texto if unicodedata.category(c) != 'Mn')
    
    return texto.lower().strip()

def extrair_palavras_chave(empresa_data: pd.Series) -> Set[str]:
    """
    Extrai um conjunto de palavras-chave relevantes de uma empresa para validação.
    Cria um "DNA" da empresa para comparar com os resultados da busca.
    # Boa prática: Centralizar a lógica de extração de palavras-chave.
    """
    palavras = set()
    
    # Colunas que contêm informações valiosas para identificar a empresa
    campos_texto = [
        'razao_social', 'nome_fantasia', 'logradouro', 'complemento', 'cnpj_basico',
        'bairro', 'correio_eletronico', 'telefone1', 'cep_limpo', 'municipio_nome'
    ]
    
    for campo in campos_texto:
        # Verifica se a coluna existe e não é nula antes de processar
        if campo in empresa_data and pd.notna(empresa_data[campo]):
            valor = empresa_data[campo]
            if valor and str(valor).strip():
                texto_normalizado = normalizar_texto(valor)
                palavras_campo = {p for p in texto_normalizado.split() if len(p) >= 2}
                palavras.update(palavras_campo)
    
    # Remove palavras genéricas que não ajudam na identificação
    palavras_comuns = {
        'ltda', 'cia', 'comercial', 'industria', 'servicos', 'eireli', 'me', 'sa',
        'empresa', 'rua', 'avenida', 'centro', 'bairro', 'com', 'br', 'gov'
    }
    
    # Ponto-chave: O uso de um 'set' remove palavras duplicadas e é eficiente para buscas.
    return palavras - palavras_comuns

def verificar_correspondencia_descricao(
    palavras_chave_empresa: Set[str],
    descricao: str
) -> Tuple[bool, List[str]]:
    """
    Verifica se as palavras-chave da empresa aparecem na descrição do resultado da busca.
    Retorna um booleano para a correspondência e a lista de palavras encontradas.
    """
    if not palavras_chave_empresa or not descricao or pd.isna(descricao):
        return False, []
        
    descricao_norm = normalizar_texto(descricao)
    palavras_encontradas = [
        palavra for palavra in palavras_chave_empresa if palavra in descricao_norm
    ]
    
    if not palavras_encontradas:
        return False, []
    
    # Lógica de validação: considera válido se a taxa de correspondência for alta
    # OU se pelo menos 2 palavras-chave importantes forem encontradas.
    taxa_correspondencia = len(palavras_encontradas) / len(palavras_chave_empresa)
    tem_correspondencia = (taxa_correspondencia >= VALIDATION_THRESHOLD) or (len(palavras_encontradas) >= 2)
    
    return tem_correspondencia, palavras_encontradas


# ==================== Funções de Busca e Processamento ====================

def buscar_e_validar_perfil(
    termo_busca: str,
    palavras_chave_empresa: Set[str]
) -> Tuple[str | None, List[str]]:
    """
    Executa a busca e itera pelos resultados, validando cada um contra as palavras-chave.
    Retorna a URL do primeiro perfil validado e as palavras que confirmaram a validação.
    # Boa prática: Separar a busca da validação em funções distintas.
    """
    try:
        # Design robusto: O uso de 'with DDGS(...)' garante o fechamento correto dos recursos.
        with DDGS(timeout=10) as ddgs:
            for resultado in ddgs.text(termo_busca, max_results=MAX_RESULTS_PER_SEARCH):
                url = resultado.get("href", "")
                if "instagram.com" in url:
                    # Usa o título e o corpo do resultado da busca para validação
                    descricao = resultado.get("body", "") + " " + resultado.get("title", "")
                    
                    tem_corresp, palavras_encontradas = verificar_correspondencia_descricao(
                        palavras_chave_empresa, descricao
                    )
                    
                    if tem_corresp:
                        # Limpa a URL de parâmetros de rastreamento
                        clean_url = url.split("?")[0]
                        if clean_url.endswith('/'):
                            clean_url = clean_url[:-1]
                        return clean_url, palavras_encontradas
                        
        return None, []  # Nenhum perfil validado encontrado
    except Exception as e:
        # Imprime o erro no console do servidor para depuração
        print(f"❌ Erro durante a busca por '{termo_busca}': {e}")
        return None, []

def processar_empresa(empresa_dados: pd.Series) -> Dict[str, Any]:
    """
    Orquestra o processo para uma única empresa: extrai palavras-chave, busca e valida.
    # Boa prática: Retornar um dicionário estruturado facilita a conversão para DataFrame.
    """
    cnpj = empresa_dados.get('cnpj_basico', '')
    razao_social = empresa_dados.get('razao_social', '')
    municipio = empresa_dados.get('municipio_nome', '') # Usa a coluna padronizada
    
    if not razao_social or not municipio:
        return {
            "cnpj_basico": cnpj, "razao_social": razao_social, "municipio": municipio,
            "instagram_url": "Dados insuficientes", "status_validacao": "Falha",
            "palavras_encontradas": [], "palavras_chave_usadas": []
        }
    
    palavras_chave = extrair_palavras_chave(empresa_dados)
    termo = f'"{razao_social}" {municipio} instagram'
    time.sleep(TEMPO_ESPERA)
    url_encontrada, palavras_match = buscar_e_validar_perfil(termo, palavras_chave)
    
    status = "Perfil Validado" if url_encontrada else "Nenhum perfil validado"
    url_final = url_encontrada if url_encontrada else "Não encontrado"
        
    return {
        "cnpj_basico": cnpj,
        "razao_social": razao_social,
        "municipio": municipio,
        "instagram_url": url_final,
        "status_validacao": status,
        "palavras_encontradas": ", ".join(palavras_match),
        "palavras_chave_usadas": ", ".join(sorted(list(palavras_chave)))
    }

def buscar_em_lote(empresas_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Função principal. Usa ThreadPoolExecutor para processar um DataFrame de empresas em paralelo.
    # Ponto-chave da performance: ThreadPoolExecutor para paralelizar as buscas que são limitadas por I/O (rede).
    """
    resultados = []
    
    # O 'with' garante que todas as threads sejam concluídas antes de sair do bloco.
    with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        # Cria uma "tarefa" para cada linha do DataFrame
        futures = [
            executor.submit(processar_empresa, row)
            for index, row in empresas_df.iterrows()
        ]
        
        # Coleta os resultados à medida que ficam prontos
        for future in as_completed(futures):
            try:
                resultados.append(future.result())
            except Exception as e:
                print(f"❌ Erro ao processar o resultado de uma thread: {e}")
                
    return resultados