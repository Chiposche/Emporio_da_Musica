# Empório da Música — Agente de Atendimento

## Como rodar
1. Instalar: `pip install google-genai`
2. Configurar chave: `export GEMINI_API_KEY="sua_chave"`
3. Executar: `python agent/app.py`

## Justificativas
- **IA**: Gemini Interactions API (cloud, rápido)
- **RAG manual**: CSVs + políticas
- **Persona**: tom acolhedor do Empório
- **Streaming/filtração**: para velocidade (regras do desafio valorizam experiência)

## Limitações
- Dados estáticos (CSVs)
- Sem persistência de conversa
- IA pode alucinar em perguntas complexas
