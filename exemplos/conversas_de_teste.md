# 💬 Casos de Teste e Conversas Demonstrativas

Este documento reúne 5 cenários reais de atendimento cobrindo os principais desafios e requisitos técnicos do projeto **Empório da Música**.

---

## 1. Busca de produtos com filtro de preço e estoque
- **Usuário:** *"Olá! Quais violões vocês têm disponíveis por até R$ 1.000?"*
- **Ação do Agente (`search_products`):**
  - Argumentos: `{"query": "violão", "max_price": 1000.0, "in_stock_only": true}`
  - Retorno: Violão Acústico Nylon Giannini Start N-14 (R$ 389,00) e Violão Tagima Memphis MD-18 Folk (R$ 799,00).
- **Resposta da Marina:**
  - Apresenta os modelos com simpatia, detalha as características básicas (ideal para estudo/iniciante) e cita os preços oficiais do catálogo sem inventar valores.

---

## 2. Consulta e rastreamento de pedido
- **Usuário:** *"Gostaria de saber o status e rastreamento do pedido 1."*
- **Ação do Agente (`get_order_status`):**
  - Argumentos: `{"order_id": 1}`
  - Retorno: Cliente Pedro Henrique Oliveira, status `shipped`, código `BR100000001MS`, previsão de entrega e itens (Teclado Yamaha PSR-E373).
- **Resposta da Marina:**
  - Confirma que o pedido do Pedro Henrique já foi enviado, fornece o código de rastreio e estima a data de entrega.

---

## 3. Consulta de Políticas da Loja (Trocas e Devoluções)
- **Usuário:** *"Como funciona a política de devolução e prazo de arrependimento da loja?"*
- **Ação do Agente (`search_policies`):**
  - Argumentos: `{"topic": "devolução arrependimento"}`
  - Retorno: Trecho do PDF institucional informando o prazo legal de 7 dias corridos para compras online e procedimentos com embalagem original e nota fiscal.
- **Resposta da Marina:**
  - Explica os 7 dias corridos do Código de Defesa do Consumidor, orienta sobre o estado do instrumento e como solicitar via canal de atendimento.

---

## 4. Promoções ativas e desconto cumulativo à vista (PIX)
- **Usuário:** *"Quais produtos estão em promoção ativa hoje e como funciona o desconto no PIX?"*
- **Ações do Agente:**
  - `check_promotions()`: identifica guitarras ou baterias com 10% a 15% de desconto vigentes.
  - `search_policies(topic="pagamento pix")`: localiza a regra de 5% de desconto adicional para pagamentos à vista via PIX.
- **Resposta da Marina:**
  - Lista os itens em promoção com preço original e preço com desconto, e informa que o pagamento via PIX concede mais 5% de desconto à vista.

---

## 5. Pergunta fora do escopo (Tratamento educado)
- **Usuário:** *"Qual é a melhor receita de risoto de camarão?"*
- **Ação do Agente:**
  - Nenhuma ferramenta acionada.
- **Resposta da Marina:**
  - Responde com bom humor e simpatia que, embora adore boa comida e boa música, a sua especialidade na Empório da Música são os instrumentos musicais (violões, teclados, baterias, etc.), convidando o usuário a conhecer as novidades do catálogo.

---

## 6. Pedido de acessório (produto fora do escopo da loja)
- **Usuário:** *"Vocês vendem cordas de violão e palhetas?"*
- **Ação do Agente:**
  - Nenhuma ferramenta acionada (a persona já sabe que a loja não vende acessórios).
- **Resposta da Marina:**
  - Explica com simpatia que a Empório da Música é especializada em instrumentos musicais e não trabalha com acessórios como cordas, palhetas, cabos ou pedais. Sugere que o cliente confira os violões e guitarras disponíveis no catálogo.

---

## 7. Consulta sobre garantia de produto
- **Usuário:** *"Comprei um teclado há 2 meses e ele parou de funcionar. Tem garantia?"*
- **Ação do Agente (`search_policies`):**
  - Argumentos: `{"topic": "garantia defeito"}`
  - Retorno: Seção 8 das políticas — garantia legal de 90 dias (CDC) para defeito de fabricação, garantia do fabricante de 6 meses a 2 anos, exclusões (mau uso, danos por umidade, reparos não autorizados).
- **Resposta da Marina:**
  - Informa que o produto está dentro da garantia legal de 90 dias e que o cliente pode solicitar reparo ou troca. Orienta sobre como proceder e menciona que danos por mau uso não são cobertos. Oferece encaminhar para o suporte humano se necessário.

---

## 8. Produto não encontrado (busca sem resultado)
- **Usuário:** *"Vocês têm harpa paraguaia?"*
- **Ação do Agente (`search_products`):**
  - Argumentos: `{"query": "harpa paraguaia", "in_stock_only": true}`
  - Retorno: Lista vazia (nenhum produto encontrado).
- **Resposta da Marina:**
  - Informa que infelizmente não encontrou harpas no catálogo atual, mas sugere que o cliente confira outros instrumentos de cordas disponíveis (violões, violinos, ukuleles) e se oferece para buscar alternativas.
