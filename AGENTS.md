# AGENTS.md — Empório da Música
- IA: Multi-provedor (seletor na sidebar) — MiMo V2.6 Flash (OpenRouter) + Groq GPT-OSS 120B; ambos via API OpenAI-compatível.
- Dados: CSVs em `Data/`; políticas extraídas de `políticas_da_loja.pdf`.
- Componente: Python puro, modular (`agent/`), CLI interativo.
- Sem requisitos de IA no código base; integração via API.
- Corrigir erro 404: usar `client.interactions.create()` do SDK novo.
