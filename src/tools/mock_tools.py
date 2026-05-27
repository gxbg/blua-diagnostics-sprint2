"""
Tools mockadas do BluaDiagnostics.

Cada função simula uma chamada a um sistema real da Care Plus:
- consultar_historico_paciente: simula consulta ao prontuário eletrônico
- verificar_interacoes_medicamentosas: simula consulta a base farmacológica
- agendar_teleconsulta: simula API de agendamento do Blua

O roteador `executar_tool` é o ponto de entrada usado pelos agentes:
recebe nome + inputs e despacha para a função correspondente.
"""

import json
from datetime import datetime


# ─── Base de dados simulada de pacientes ──────────────────────
# Em produção, isso seria uma chamada ao prontuário eletrônico Care Plus.

PACIENTES = {
    # Paciente exigida pelo enunciado da Sprint 2
    "BEN-MARIA": {
        "nome": "Maria Souza",
        "idade": 34,
        "sexo": "F",
        "condicoes_cronicas": ["Hipertensão arterial"],
        "medicamentos_atuais": [
            {"nome": "Losartana", "dose": "50mg", "frequencia": "1x/dia"},
        ],
        "alergias": [],
        "ultima_consulta": {
            "data": "2026-03-15",
            "medico": "Dr. João",
            "especialidade": "Clínica Geral",
            "resumo": "PA controlada (128/82). Manter Losartana. Retornar em 6 meses.",
        },
        "exames_recentes": [
            {"tipo": "Creatinina", "resultado": "0.9 mg/dL", "data": "2026-03-10"},
            {"tipo": "Potássio", "resultado": "4.2 mEq/L", "data": "2026-03-10"},
        ],
    },
    # Paciente da Sprint 1, mantida para retrocompatibilidade
    "BEN-DEMO": {
        "nome": "João Silva",
        "idade": 52,
        "sexo": "M",
        "condicoes_cronicas": ["Hipertensão arterial", "Diabetes tipo 2"],
        "medicamentos_atuais": [
            {"nome": "Losartana", "dose": "50mg", "frequencia": "1x/dia"},
            {"nome": "Metformina", "dose": "850mg", "frequencia": "2x/dia"},
            {"nome": "AAS", "dose": "100mg", "frequencia": "1x/dia"},
        ],
        "alergias": ["Penicilina"],
        "ultima_consulta": {
            "data": "2025-03-15",
            "medico": "Dr. Carlos Ferreira",
            "especialidade": "Endocrinologia",
            "resumo": "Controle glicêmico regular, PA controlada.",
        },
        "exames_recentes": [
            {"tipo": "HbA1c", "resultado": "7.2%", "data": "2025-02-10"},
            {"tipo": "Creatinina", "resultado": "1.1 mg/dL", "data": "2025-02-10"},
            {"tipo": "Colesterol total", "resultado": "195 mg/dL", "data": "2025-02-10"},
        ],
    },
}


# ─── Tool 1: consultar histórico do paciente ──────────────────

def consultar_historico_paciente(beneficiario_id: str, campos_solicitados: list) -> dict:
    """
    Simula consulta ao prontuário eletrônico Care Plus.

    Aplica minimização LGPD: retorna apenas os campos solicitados, não o prontuário completo.
    """
    paciente = PACIENTES.get(beneficiario_id)
    if not paciente:
        return {
            "error": "BENEFICIARY_NOT_FOUND",
            "message": (
                f"Beneficiário '{beneficiario_id}' não encontrado. "
                "Prossiga a avaliação sem histórico prévio."
            ),
        }

    resultado = {
        "beneficiario_id": beneficiario_id,
        "nome": paciente["nome"],
        "idade": paciente["idade"],
    }
    for campo in campos_solicitados:
        if campo in paciente:
            resultado[campo] = paciente[campo]
    return resultado


# ─── Tool 2: verificar interações medicamentosas ──────────────

def verificar_interacoes_medicamentosas(medicamentos: list) -> dict:
    """
    Simula consulta a base de interações medicamentosas.

    Retorna apenas interações INFORMATIVAS. Decisão clínica é sempre do médico.
    """
    meds_normalizados = {m["nome"].lower().strip() for m in medicamentos}

    base_interacoes = [
        {
            "par": {"aas", "ibuprofeno"},
            "nivel": "moderado",
            "descricao": "Ibuprofeno pode antagonizar o efeito antiagregante do AAS.",
            "recomendacao": "Discutir alternativa analgésica com médico (ex: paracetamol).",
        },
        {
            "par": {"warfarina", "ibuprofeno"},
            "nivel": "grave",
            "descricao": "AINEs aumentam risco de sangramento em usuários de Warfarina.",
            "recomendacao": "Contraindicado sem supervisão médica estrita.",
        },
        {
            "par": {"losartana", "ibuprofeno"},
            "nivel": "moderado",
            "descricao": "AINEs reduzem o efeito anti-hipertensivo da losartana e podem afetar função renal.",
            "recomendacao": "Evitar uso prolongado concomitante. Preferir paracetamol.",
        },
        {
            "par": {"losartana", "espironolactona"},
            "nivel": "moderado",
            "descricao": "Risco de hipercalemia (aumento de potássio).",
            "recomendacao": "Monitorar potássio sérico periodicamente.",
        },
        {
            "par": {"metformina", "contraste iodado"},
            "nivel": "grave",
            "descricao": "Risco de acidose lática em exames com contraste.",
            "recomendacao": "Suspender metformina 48h antes do exame contrastado.",
        },
    ]

    encontradas = []
    for interacao in base_interacoes:
        if interacao["par"].issubset(meds_normalizados):
            encontradas.append({
                "medicamentos": list(interacao["par"]),
                "nivel": interacao["nivel"],
                "descricao": interacao["descricao"],
                "recomendacao": interacao["recomendacao"],
            })

    return {
        "medicamentos_verificados": medicamentos,
        "interacoes_encontradas": len(encontradas) > 0,
        "total_interacoes": len(encontradas),
        "interacoes": encontradas,
        "aviso_clinico": "Verificação informativa. Decisão terapêutica compete ao médico.",
    }


# ─── Tool 3: agendar teleconsulta ─────────────────────────────

def agendar_teleconsulta(
    beneficiario_id: str,
    especialidade: str,
    motivo_consulta: str,
    urgencia: str = "rotina",
) -> dict:
    """
    Simula agendamento de teleconsulta no Blua.

    Não deve ser usada em emergências — nesses casos orientar SAMU 192.
    """
    medicos = {
        "clinica_geral": "Dr. Carlos Ferreira",
        "cardiologia": "Dra. Ana Paula Rocha",
        "dermatologia": "Dr. Marcos Oliveira",
        "ginecologia": "Dra. Juliana Santos",
        "pediatria": "Dra. Fernanda Alves",
        "psiquiatria": "Dra. Beatriz Lima",
        "ortopedia": "Dr. Pedro Mendes",
        "endocrinologia": "Dr. Rafael Costa",
    }

    horarios = {
        "urgente": "Hoje às 16:30",
        "preferencial": "Amanhã às 10:00",
        "rotina": "Sexta-feira às 14:30",
    }

    agendamento_id = f"AGD-{abs(hash(beneficiario_id + especialidade)) % 999999:06d}"

    return {
        "agendamento_id": agendamento_id,
        "status": "confirmado",
        "beneficiario_id": beneficiario_id,
        "medico": medicos.get(especialidade, "Médico de plantão"),
        "especialidade": especialidade.replace("_", " ").title(),
        "urgencia": urgencia,
        "data_hora": horarios.get(urgencia, "A definir"),
        "motivo": motivo_consulta,
        "link_teleconsulta": f"https://blua.careplus.com.br/teleconsulta/{agendamento_id}",
        "instrucoes": (
            "Acesse o link 10 minutos antes do horário. "
            "Tenha em mãos seus medicamentos e exames recentes."
        ),
        "criado_em": datetime.now().isoformat(),
    }


# ─── Roteador central ─────────────────────────────────────────

def executar_tool(nome: str, inputs: dict) -> dict:
    """
    Roteador central de tools.

    Recebe o nome da tool e seus inputs (no formato esperado pelo function calling)
    e retorna o resultado da execução. Usado pelos agentes do LangGraph.
    """
    dispatch = {
        "consultar_historico_paciente": lambda i: consultar_historico_paciente(
            beneficiario_id=i["beneficiario_id"],
            campos_solicitados=i["campos_solicitados"],
        ),
        "verificar_interacoes_medicamentosas": lambda i: verificar_interacoes_medicamentosas(
            medicamentos=i["medicamentos"],
        ),
        "agendar_teleconsulta": lambda i: agendar_teleconsulta(
            beneficiario_id=i["beneficiario_id"],
            especialidade=i["especialidade"],
            motivo_consulta=i["motivo_consulta"],
            urgencia=i.get("urgencia", "rotina"),
        ),
    }

    func = dispatch.get(nome)
    if func is None:
        return {"error": "TOOL_NOT_FOUND", "message": f"Tool '{nome}' não encontrada."}

    try:
        return func(inputs)
    except KeyError as e:
        return {"error": "MISSING_PARAMETER", "message": f"Parâmetro ausente: {e}"}
    except Exception as e:
        return {"error": "EXECUTION_ERROR", "message": str(e)}


# ─── Teste rápido das tools ───────────────────────────────────
# Roda só se você executar este arquivo direto: python src/tools/mock_tools.py

if __name__ == "__main__":
    print("=" * 60)
    print("Teste das tools mockadas")
    print("=" * 60)

    # Teste 1: histórico da Maria
    print("\n[1] consultar_historico_paciente — BEN-MARIA")
    r1 = executar_tool("consultar_historico_paciente", {
        "beneficiario_id": "BEN-MARIA",
        "campos_solicitados": ["condicoes_cronicas", "medicamentos_atuais", "ultima_consulta"],
    })
    print(json.dumps(r1, indent=2, ensure_ascii=False))

    # Teste 2: interação Losartana + Ibuprofeno
    print("\n[2] verificar_interacoes_medicamentosas")
    r2 = executar_tool("verificar_interacoes_medicamentosas", {
        "medicamentos": [
            {"nome": "Losartana", "dose": "50mg"},
            {"nome": "Ibuprofeno", "dose": "600mg"},
        ],
    })
    print(json.dumps(r2, indent=2, ensure_ascii=False))

    # Teste 3: agendamento de teleconsulta
    print("\n[3] agendar_teleconsulta")
    r3 = executar_tool("agendar_teleconsulta", {
        "beneficiario_id": "BEN-MARIA",
        "especialidade": "clinica_geral",
        "urgencia": "preferencial",
        "motivo_consulta": "Avaliação de rotina e renovação de receita.",
    })
    print(json.dumps(r3, indent=2, ensure_ascii=False))

    # Teste 4: paciente inexistente
    print("\n[4] consultar_historico_paciente — paciente inexistente")
    r4 = executar_tool("consultar_historico_paciente", {
        "beneficiario_id": "BEN-XXXXXX",
        "campos_solicitados": ["condicoes_cronicas"],
    })
    print(json.dumps(r4, indent=2, ensure_ascii=False))

    # Teste 5: tool inexistente
    print("\n[5] tool inexistente")
    r5 = executar_tool("tool_que_nao_existe", {})
    print(json.dumps(r5, indent=2, ensure_ascii=False))

    print("\n" + "=" * 60)
    print("Testes concluídos.")