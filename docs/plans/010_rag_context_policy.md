# Context Retrieval Policy (RAG)

## Resumo

Política implementada para projetos com índice semántico local, priorizando recuperação de contexto antes da leitura extensiva de arquivos. A mesmo premissa de governança, economia de tokens e clareza operacional.

## Principais Pontos
1. **Governança**
   - Regras para ativação do RAG (detecção de índice, limiar de score, reindexação automática)
   - Registro obrigatório de fontes em `Knowledge Sources`

2. **Economia de Tokens**
   - Limitação de leituras a arquivos indicados pelo RAG
   - Uso de `offset`/`limit` para fatias de contexto
   - Compressão contextual de trechos relevantes

3. **Clareza Operacional**
   - Ordenação clara de recuperação (RAG > código > documentação)
   - Processo padronizado para reindexação

## Gaps Identificados
- Sem wrapper vetorial FAISS funcional (search textual apenas)
- Dependência em MCP работал ao mesmo tempo é opcional
-necessidade de tooling de teste reforça para validação de recall

## Recomendações Estratégicas
1. Criar `~/.claude/scripts/rag_query.py` (wrapper FAISS)
2. Registrar MCP `claude-context-local` em `settings.json`
3. Usar linguagem de arquivo em pt-BR para coesão

## Próximos Passos
1. Implementar wrapper FAISS vásico
2. Validar com testes de recuperação
3. Configurar auto-reindex com gatilho de mudanças no repositório