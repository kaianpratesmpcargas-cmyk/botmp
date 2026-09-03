# MP CARGAS - Rastreamento & API para Bots (WhatsApp / Telegram)

Sistema de rastreamento de cargas e notas fiscais integrado diretamente à API do sistema SSW, equipado com interface Web moderna e **API REST sob medida para Bots de WhatsApp e Telegram**.

---

## 🚀 Como Executar

### 1. Instalar as dependências
```bash
pip install -r requirements.txt
```

### 2. Iniciar o servidor
```bash
python app.py
```
O servidor iniciará por padrão em `http://localhost:5000`.

---

## ⚡ Endpoints da API REST & Integração para Bots

### 1. Endpoint Unificado para Bots (WhatsApp / Telegram): `POST /api/v1/bot/consulta`
Este é o endpoint inteligente projetado para chatbots. Ele suporta:
- **Linguagem Natural:** Extrai CNPJ, CPF, NF, Pedido e Coleta mesmo em frases completas (ex: `"rastrear pedido 12345 cnpj 02.012.862/0037-70"` ou `"nota fiscal 130516 cpf 026.026.026-55"`).
- **Busca em Cascata Inteligente:** Quando recebe um CNPJ, pesquisa automaticamente como Destinatário ➔ Remetente ➔ Pagador.
- **Suporte a Pessoa Física:** Quando recebe um CPF (11 dígitos), consulta diretamente o WebAPI de Pessoa Física.
- **Dúvidas de Atendimento:** Responde sobre praças, prazos de entrega em dias úteis, endereços e telefones de coleta.
- **Memória de Conversa:** Se o cliente enviar apenas a NF ou Pedido, o bot retém e solicita o CNPJ/CPF. Na mensagem seguinte, a consulta é concluída automaticamente!

**Exemplo de Chamada (cURL):**
```bash
curl http://localhost:5000/api/v1/bot/consulta \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"texto": "33.041.260/1414-93 4224761"}'
```

---

### 2. SSW Tracking Destinatário WebAPI: `POST /api/v1/tracking/destinatario`
Acesso à informação de rastreamento para o **cliente destinatário**.
- `cnpj` (string, obrigatório): CNPJ do destinatário
- `senha` (string, **opcional**): Senha disponibilizada pela transportadora (se enviada e validada, libera comprovante de entrega)
- `sigla_emp` (string, opcional): Filtrar para a empresa em questão
- Envie **exatamente um** dos quatro: `nro_nf`, `pedido`, `chave_nfe` ou `nro_coleta`.

```bash
curl http://localhost:5000/api/v1/tracking/destinatario \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"cnpj": "02012862003770", "nro_nf": 130516}'
```

---

### 3. SSW Tracking Pagador WebAPI: `POST /api/v1/tracking/pagador`
Acesso à informação de rastreamento para o **cliente pagador da carga**.
- `cnpj` (string, obrigatório): CNPJ do pagador
- `senha` (string, **opcional**): Não obrigatória
- `sigla_emp` (string, opcional)
- Envie **exatamente um** dos quatro: `nro_nf`, `pedido`, `chave_nfe` ou `nro_coleta`.

```bash
curl http://localhost:5000/api/v1/tracking/pagador \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"cnpj": "02012862003770", "pedido": "12345678"}'
```

---

### 4. SSW Tracking Pessoa Física: `POST /api/v1/tracking/pf`
Acesso à informação de rastreamento para destinatário **pessoa física**.
- `cpf` (string, obrigatório): CPF do destinatário (11 dígitos)
- `nro_nf` (integer, opcional): Número da NF
- `pedido` (string, opcional): Número do pedido
- `chave_nfe` (string, opcional): Chave da NF-e
- Credenciais corporativas (`dominio`, `usuario`, `senha`) podem ser enviadas no JSON ou configuradas via variáveis de ambiente (`PF_DOMINIO`, `PF_USUARIO`, `PF_SENHA`).

```bash
curl http://localhost:5000/api/v1/tracking/pf \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"cpf": "02602602655", "nro_nf": 130516}'
```

---

### 5. Consulta por Chave DANFE: `POST /api/v1/tracking/danfe`
```bash
curl http://localhost:5000/api/v1/tracking/danfe \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"chave_nfe": "43160400850257000132550010000083991000083990"}'
```

---

### 6. Consulta por Remetente (CNPJ + NF): `POST /api/v1/tracking/remetente`
```bash
curl http://localhost:5000/api/v1/tracking/remetente \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"cnpj": "12345678000190", "nro_nf": "61750"}'
```

---

## 🤖 Exemplo de Integração em Python (Telegram Bot)

```python
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

API_URL = "http://localhost:5000/api/v1/bot/consulta"

async def responder_rastreio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto_usuario = update.message.text
    
    # Chama nossa API
    resposta = requests.post(API_URL, json={"texto": texto_usuario}).json()
    
    # Envia a mensagem já formatada para o cliente
    await update.message.reply_text(resposta["mensagem_bot"], parse_mode="Markdown")

app = ApplicationBuilder().token("SEU_TOKEN_TELEGRAM").build()
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, responder_rastreio))
app.run_polling()
```

---

## 📂 Estrutura do Projeto

```
ssw2/
├── app.py                     # Entry point Flask (rotas Web e API REST)
├── requirements.txt           # Dependências (Flask, requests)
├── README.md                  # Documentação completa
├── services/
│   ├── __init__.py
│   └── ssw_service.py         # Cliente SSW, validações, regex e parsing inteligente
├── utils/
│   ├── __init__.py
│   └── bot_formatter.py       # Formatador de mensagens para WhatsApp/Telegram
├── templates/
│   └── index.html             # Interface Web responsiva
└── static/
    ├── css/
    │   └── style.css          # Estilos visuais MP CARGAS
    └── js/
        └── main.js            # Interatividade das abas
```
