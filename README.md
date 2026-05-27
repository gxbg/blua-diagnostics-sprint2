# 🏥 BluaDiagnostics — Sprint 2

Sistema multi-agente de check-up digital e suporte à prescrição remota para o ecossistema Blua (Care Plus / Bupa). Implementado com **LangGraph**, **RAG** (ChromaDB + Gemini embeddings) e **function calling**.

> **Sprint 2** — evolução da PoC da Sprint 1 com arquitetura multi-agente, RAG funcional, guardrails clínicos e suite de avaliação automatizada.

---

## 👥 Integrantes

| Nome | RM |
|---|---|
| Gabriel de Paula Gil | 567286 |
| Erik Medveder Nikoluk | 567996 |
| Diego Leite Asprino  | 561662 |

---

## 🎯 Visão Geral

O BluaDiagnostics ataca dois pilares estratégicos do Blua:
- **Digital Check-up**: autoavaliação conversacional que coleta sintomas e dispara rastreios preventivos com detecção de red flags clínicas
- **Prescrição Remota Inteligente**: agente que sugere encaminhamentos com base no histórico do paciente, valida interações medicamentosas e agenda teleconsultas

A persona escolhida é o **beneficiário final em autoavaliação**, com escalada automática para atendimento humano em red flags.

---

## 🏗️ Arquitetura

   ┌─────────────────┐
User input →  │   SUPERVISOR    │  (Gemini 2.5 Flash, temp=0)
│  (roteamento)   │
└────────┬────────┘
│
┌─────────────────┼─────────────────┐
▼                 ▼                 ▼
┌──────────┐      ┌──────────┐      ┌──────────┐
│ TRIAGEM  │      │PRESCRIÇÃO│      │ ESCALADA │
│ + RAG    │      │ + tools  │      │ (red     │
│ + tools  │      │          │      │  flags)  │
└─────┬────┘      └─────┬────┘      └─────┬────┘
│                 │                 │
└─────────────────┴─────────────────┘
│
END

### Componentes principais

| Camada | Stack |
|---|---|
| **Orquestração multi-agente** | LangGraph (StateGraph com 4 nós e arestas condicionais) |
| **LLM** | Google Gemini 2.5 Flash (free tier) |
| **Embeddings** | Google `gemini-embedding-001` |
| **Vector Store** | ChromaDB (persistido localmente em `data/chroma_db/`) |
| **Tools (function calling)** | 3 tools mockadas: histórico, interações, agendamento |
| **Interface** | Streamlit com painel de observabilidade |

### Agentes especializados

1. **Supervisor** — analisa a mensagem do usuário e decide o roteamento (triagem / prescrição / escalada) com decisão determinística (temp=0)
2. **Triagem** — conduz check-ups, busca contexto RAG, chama tool de histórico do paciente, retorna resposta estruturada
3. **Prescrição** — consulta histórico, verifica interações medicamentosas, agenda teleconsultas
4. **Escalada** — protocolo de emergência: SAMU 192 + central Care Plus, sem perguntas adicionais

### Estado compartilhado (LangGraph)

```python
class EstadoBlua(TypedDict):
    mensagens: list          # histórico da conversa
    paciente_id: str         # ID do beneficiário
    contexto_rag: list       # docs RAG recuperados
    tools_log: list          # tools chamadas
    red_flag: bool           # flag de emergência
    agente_atual: str        # nó que está respondendo
    resposta_final: str      # output ao usuário
```

---

## 📁 Estrutura do repositório
blua-diagnostics-sprint2/
├── app/
│   └── app.py                       # Interface Streamlit
├── data/
│   ├── knowledge_base/              # 5 documentos clínicos (.md)
│   └── chroma_db/                   # Vector store (gerado)
├── docs/
│   └── relatorio_final.md           # Relatório técnico completo
├── evals/
│   ├── sprint1_eval_set.json        # 12 casos de teste
│   ├── run_evals.py                 # Script de avaliação
│   └── sprint2_results.json         # Resultados
├── prompts/
│   └── system_prompt.md             # System prompt versionado
├── src/
│   ├── tools/
│   │   └── mock_tools.py            # Implementação das tools
│   ├── rag/
│   │   └── pipeline.py              # Pipeline RAG completo
│   ├── agents/                      # (reservado para extensões)
│   └── graph/
│       └── graph.py                 # Grafo LangGraph
├── tools/
│   └── tools_spec.json              # Contrato JSON Schema das tools
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md

---

## 🚀 Como executar

### Pré-requisitos

- Python 3.11+
- Conta Google com acesso ao Gemini API ([aistudio.google.com](https://aistudio.google.com))

### 1. Clonar e instalar

```bash
git clone https://github.com/gxbg/blua-diagnostics-sprint2.git
cd blua-diagnostics-sprint2

python -m venv venv

# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configurar variáveis de ambiente

Crie um arquivo `.env` na raiz com sua chave Google:

```env
GOOGLE_API_KEY=sua_chave_aqui
```

A chave gratuita pode ser obtida em [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey).

### 3. Popular o vector store (uma vez)

```bash
python src/rag/pipeline.py
```

Esse comando carrega os 5 documentos da `data/knowledge_base/`, gera embeddings com Gemini e persiste no ChromaDB. Saída esperada: `✓ Vector store criado` + 31 chunks indexados.

### 4. Rodar a interface

```bash
streamlit run app/app.py
```

Acesse `http://localhost:8501`. A sidebar mostra paciente, agente ativo, documentos RAG recuperados e tools chamadas em tempo real.

### 5. Rodar os evals

```bash
python evals/run_evals.py
```

Gera `evals/sprint2_results.json` com métricas por caso. O script é **resumível** — se quebrar por rate limit, basta rodar de novo e ele continua de onde parou.

---

## 🧪 Resultados da avaliação

Suite de **12 casos** cobrindo 4 categorias. **10 casos foram avaliados** (2 pendentes por rate limit do free tier do Gemini).

| Categoria | Casos | Score |
|---|---|---|
| 🚨 **red_flag** | 3/3 | **100%** |
| 🛡️ **jailbreak** | 3/3 | **100%** |
| 🚫 **out_of_scope** | 1/3 | 100% (avaliado) |
| ✅ **happy_path** | 3/3 | 67% |
| **Total** | **10/12** | **90%** |

Detalhes completos em [`docs/relatorio_final.md`](docs/relatorio_final.md).

---

## 🛡️ Guardrails implementados

- **Detecção de red flags clínicas** — sintomas cardíacos, neurológicos, respiratórios e ideação suicida acionam protocolo de emergência (SAMU 192)
- **Validação de escopo** — rejeita perguntas fora do domínio Care Plus de forma educada
- **Anti-jailbreak** — recusa firme a pedidos de prescrição direta, diagnóstico definitivo ou troca de identidade
- **Disclaimer obrigatório** — toda resposta clínica inclui aviso de que orientação é informativa
- **Princípio HITL** — todas as decisões clínicas finais são encaminhadas a médico humano

---

## 🔐 Segurança e LGPD

- Nenhuma chave de API exposta no repositório (`.env` em `.gitignore`)
- Tools aplicam **princípio da minimização** — `consultar_historico_paciente` retorna apenas os campos solicitados
- Dados de pacientes são **mockados** (não há PII real)
- Roadmap inclui deploy local com Ollama para conformidade LGPD em produção

---

## 📺 Demonstração

🎥 **Vídeo (5 min):** [link aqui após gravar]

📊 **Relatório técnico:** [`docs/relatorio_final.md`](docs/relatorio_final.md)

---

## 🛣️ Roadmap para produção

- [ ] Substituir embeddings cloud por modelo local (sentence-transformers) para conformidade LGPD
- [ ] Migrar LLM para Ollama (llama 3.3 ou qwen) por privacidade clínica
- [ ] Adicionar observabilidade com LangSmith ou LangFuse
- [ ] Integração real com APIs Care Plus / TytoCare
- [ ] Suite de testes unitários para tools e regressão para prompts
- [ ] Implementação de HITL real para prescrições (notificação ao médico)
- [ ] Integração com wearables (Apple Health, Google Fit) via JSON