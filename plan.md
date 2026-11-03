# 🎸 Plano — Agente de Atendimento Empório da Música

> Desafio Técnico — AI Engineer | Artefact  
> Última atualização: Novembro 2026

---

## 📋 Resumo do Desafio

Construir um **agente de atendimento em Python** para a **Empório da Música**, loja fictícia de instrumentos musicais em Campo Grande/MS.

O agente deve:
- Ter uma **persona humanizada**, alinhada ao tom da loja ("amigo que entende de música")
- Consultar **dados estruturados** (CSVs: produtos, pedidos, clientes, promoções)
- Consultar **políticas** (PDF: trocas, devoluções, horários, frete, formas de pagamento)
- Lidar com **perguntas fora do escopo** da loja de forma educada
- Manter **histórico de conversa** por sessão

---

## 🗂️ Dados Disponíveis

| Arquivo | Conteúdo | Uso |
|---|---|---|
| `Data/políticas_da_loja.pdf` | Horários, pagamento, trocas, frete, garantia, promoções | Busca por tópico (keyword-based no texto extraído) |
| `categories.csv` | 9 categorias de instrumentos | Lookup para filtros |
| `products.csv` | 65 produtos com preço, estoque, specs | Busca por produto/preço/estoque |
| `customers.csv` | 50 clientes com nome/telefone/e-mail | Lookup por ID de cliente |
| `orders.csv` | 20 pedidos com status, rastreamento, entrega | Status de pedido / rastreamento |
| `order_items.csv` | Itens de cada pedido | Join com pedidos e produtos |
| `promotions.csv` | 25 promoções (ativas e inativas) | Desconto vigente por produto |

---

## 🏗️ Arquitetura Escolhida — ReAct Agent + Function Calling

### Por quê ReAct?

- **Simplicidade explícita**: o agente raciocina passo a passo (Thought → Action → Observation → Answer), fácil de depurar.
- **Escopo controlado**: ferramentas bem definidas evitam alucinações sobre dados.
- **Sem infra pesada**: sem vector DB externo, sem orquestrador — só Python e a API do LLM.
- **Raciocínio visível**: o avaliador consegue ver exatamente o que o agente consultou e por quê.

### Alternativas consideradas e descartadas

| Abordagem | Motivo de descarte |
|---|---|
| RAG com embeddings + vector DB | Over-engineering para 65 produtos e 8 páginas de PDF |
| SQL Agent puro | Não lida bem com perguntas sobre políticas do PDF |
| LlamaIndex / LangChain | Dependência externa desnecessária — "requisito de IA" no código |
| Fine-tuning | Custo/tempo inviável para o escopo |

---

## 🧩 Estrutura de Componentes

```
emporio_agent/
├── app.py                  # Entrypoint Streamlit — interface de chat
├── agent.py                # Loop ReAct principal — orquestra Thought/Action/Observation
├── persona.py              # System prompt + persona da "Marina" (atendente virtual)
├── tools/
│   ├── __init__.py
│   ├── product_search.py   # Busca de produtos por nome, categoria, preço máximo, estoque
│   ├── order_lookup.py     # Status de pedido por order_id ou customer_id
│   ├── promotion_check.py  # Promoções ativas para um produto
│   └── policy_search.py    # Busca por tópico no texto do PDF (keyword-based)
├── data/
│   └── loader.py           # Carrega e normaliza todos os CSVs + extrai texto do PDF
├── persona.py              # System prompt da Marina
├── requirements.txt        # Dependências mínimas
├── .env.example            # Template de variáveis de ambiente
├── .streamlit/
│   └── secrets.toml        # API key (local) — no Cloud vai via painel do Streamlit
└── README.md               # Documentação completa
```

---

## 🎭 Persona — "Marina"

- **Nome**: Marina
- **Tom**: informal mas profissional, empática, entende de música
- **Regras embutidas no system prompt**:
  - Nunca inventa preço ou disponibilidade — sempre chama a ferramenta
  - Sempre verifica se promoção está ativa antes de mencionar desconto
  - Redireciona acessórios (cordas, cabos, palhetas) educadamente
  - Informa horários de funcionamento
  - Escala reclamações complexas para equipe humana

---

## 🔧 Ferramentas (Function Calling)

### 1. `search_products`
- **Parâmetros**: `query` (str), `max_price` (float|None), `category` (str|None), `in_stock_only` (bool)
- **Retorna**: lista de produtos filtrados com nome, preço, estoque, specs resumidas

### 2. `get_order_status`
- **Parâmetros**: `order_id` (int|None), `customer_name` (str|None)
- **Retorna**: status, rastreamento, previsão de entrega, itens do pedido

### 3. `check_promotions`
- **Parâmetros**: `product_id` (int|None), `product_name` (str|None)
- **Retorna**: desconto ativo (%), descrição da promoção

### 4. `search_policies`
- **Parâmetros**: `topic` (str) — ex: "devolução", "horário", "frete", "garantia"
- **Retorna**: trecho relevante do PDF de políticas

---

## 🤖 Modelos e Provedores

Dois modelos integrados, selecionáveis via sidebar — pensado para o avaliador comparar comportamentos:

| Modelo | Provedor | Custo | SDK |
|---|---|---|---|
| `gemini-1.5-flash` | Google AI | **Grátis** (free tier) | `google-generativeai` |
| `gpt-4o-mini` | OpenAI | ~$0.15/1M tokens | `openai` |

- Ambos suportam **function calling** nativamente
- Ambos têm excelente desempenho em **português**
- A lógica do agente é **idêntica** para os dois — só o cliente HTTP muda
- Chaves configuradas via **Streamlit Secrets** no Cloud

---

## 💻 Interface — Streamlit

- **`app.py`** rodando com `streamlit run app.py`
- Chat visual com `st.chat_message` + `st.chat_input` (nativo do Streamlit)
- Histórico de conversa gerenciado pelo `st.session_state` — sem banco de dados
- **Sidebar** com:
  - Seletor de modelo: `Gemini 3.8 Flash` ou `GPT-4o-mini`
  - **Debug Mode** (checkbox) — exibe o raciocínio ReAct (Pensamento → Ação → Observação)
  - Botão **"Nova conversa"**
- **Mensagem de boas-vindas automática** — ao abrir o site, Marina já escreve sozinha (sem o usuário digitar nada):
  > *"Olá! Sou a Marina, assistente virtual da Empório da Música 🎸 [explica o que faz]... Para os avaliadores: você pode testar o Debug Mode na sidebar para ver meu raciocínio, trocar entre Gemini e GPT-4o-mini, e usar as sugestões abaixo para começar rápido!"*
  - Implementado via `st.session_state` pré-populado com a mensagem da Marina na primeira carga
  - Tom duplo: humanizado para cliente + informativo para avaliador
- **Sugestões rápidas** logo abaixo da boas-vindas (botões clicáveis): `🎸 Ver produtos` `📦 Meu pedido` `💰 Promoções` `🕐 Horários`
- **Spinner humanizado** enquanto a Marina "pensa": *"Marina está consultando o catálogo..."*
- **Tema visual** customizado via `.streamlit/config.toml` (cores da loja: marrom/dourado)
- Trocar o modelo **reinicia a conversa** automaticamente
- Deploy: **Streamlit Cloud** (gratuito, conecta direto ao GitHub)
- API keys configuradas via **Streamlit Secrets** no painel (segura, sem expor no código)

---

## 💾 Persistência de Histórico

- **`st.session_state`**: o Streamlit mantém o histórico enquanto a aba do browser estiver aberta
- **Sem banco de dados**: perfeito para o protótipo — o Streamlit Cloud gerencia o estado por sessão automaticamente
- Lista `[{role, content}]` passada diretamente na chamada da API OpenAI

---

## 🛡️ Tratamento de Casos Especiais

| Situação | Comportamento |
|---|---|
| Produto fora de estoque | Informa + sugere alternativa similar disponível |
| Promoção expirada | Informa que não está ativa, passa preço atual |
| Pergunta fora do escopo | Responde com educação que loja é só instrumentos |
| Acessório (corda, palheta) | Redireciona educadamente |
| Reclamação | Registra e informa prazo de 24h para retorno |
| Dados insuficientes | Pede mais detalhes ao cliente |

---

## 📦 Dependências (zero framework de IA)

```
openai>=1.10.0            # Client HTTP para API OpenAI (GPT-4o-mini)
google-genai>=2.0.0       # Client oficial para API Google (Gemini via Interactions API)
streamlit>=1.30.0          # Interface de chat + deploy
pdfplumber>=0.9.0          # Extração de texto do PDF de políticas
pandas>=2.0.0              # Manipulação dos CSVs
python-dotenv>=1.0.0       # Variáveis de ambiente (.env) — local only
```

> ⚠️ Zero dependência de LangChain, LlamaIndex, Haystack ou similar.  
> A "IA" são os modelos chamados via API REST — o código em si é Python puro.

---

## 📁 Exemplos de Conversa (Entregáveis)

5 conversas cobrindo:
1. Busca de produto com filtro de preço ("violões até R$1000")
2. Status de pedido com rastreamento
3. Política de devolução / arrependimento
4. Promoção ativa + desconto PIX cumulado
5. Pergunta fora do escopo (redirecionamento educado)

---

## 🚀 Ordem de Implementação

- [x] Leitura e entendimento dos dados e políticas
- [x] `data/loader.py` — carregamento e normalização dos CSVs + PDF
- [x] `tools/product_search.py`
- [x] `tools/order_lookup.py`
- [x] `tools/promotion_check.py`
- [x] `tools/policy_search.py`
- [x] `persona.py` — system prompt da Marina
- [x] `agent.py` — loop ReAct com function calling (Gemini & OpenAI)
- [x] `app.py` — interface Streamlit (chat + sidebar + sugestões rápidas + spinner humanizado + assinatura de rodapé)
- [x] `.streamlit/config.toml` — tema visual personalizado da loja
- [x] `requirements.txt` + `.env.example` + `.streamlit/secrets.toml.example`
- [x] `README.md` — documentação completa para avaliadores
- [x] `exemplos/conversas_de_teste.md` — 5 conversas demonstrativas
- [ ] Deploy no Streamlit Cloud (conectar GitHub + configurar secrets)
