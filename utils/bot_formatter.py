def formatar_mensagem_whatsapp(dados, incluir_historico=True, limite_eventos=4):
    """
    Formata o resultado da consulta usando o layout escolhido pelo usuário.
    """
    if not dados:
        return "Nenhuma informação disponível para exibição."

    info = dados.get("info", {})
    ultima = dados.get("ultima", {})

    status = ultima.get("status_amigavel", "Atualização").capitalize()
    
    # Customizando a bolinha verde caso seja em transporte
    status_lower = status.lower()
    if "entregue" in status_lower:
        emoji_st = "✅"
    elif "transporte" in status_lower or "viagem" in status_lower or "transferencia" in status_lower:
        emoji_st = "🟢"
    elif "coleta" in status_lower:
        emoji_st = "🟡"
    else:
        emoji_st = "🔵"
        
    local = ultima.get("cidade") or ultima.get("filial") or "Não informado"
    data_hora = ultima.get("data_formatada", "Data não informada")

    nf = info.get("nf", "Não informado")
    pedido = info.get("pedido", "Não informado")
    coleta = info.get("nro_coleta", "Não informado")
    
    # Pegar o documento principal que o usuário usou
    identificador = ""
    if nf and nf != "Não informado":
        identificador = f"📄 NF: *{nf}*"
    elif pedido and pedido != "Não informado":
        identificador = f"🏷️ Pedido: *{pedido}*"
    elif coleta and coleta != "Não informado":
        identificador = f"📋 Coleta: *{coleta}*"
    elif info.get("documento") and info.get("documento") != "Não informado":
        identificador = f"🆔 {info.get('tipo_documento', 'Doc')}: *{info.get('documento')}*"

    destinatario = info.get("destinatario", "Não informado").title()
    previsao = info.get("previsao", "Não informada")
    origem = info.get("origem", "Não informado")
    destino = info.get("destino", "Não informado")

    # Formatação exata pedida pelo usuário
    linhas = [
        "📦 *MP CARGAS | RASTREAMENTO*",
        "",
        f"{emoji_st} *{status}*",
        "",
        f"📍 *{origem}* → *{destino}*",
        f"📅 Previsão de chegada: *{previsao}*",
        "",
        identificador,
        f"👤 Destinatário: *{destinatario}*",
        "",
        f"🕒 Atualizado em *{data_hora}*",
        "",
        "*© MP Agente de Cargas Ltda.*"
    ]

    return "\n".join(linhas)

def formatar_mensagem_erro(mensagem_erro):
    """Formata uma mensagem de erro orientando o usuário no chat do bot."""
    linhas = [
        "⚠️ *Atenção - Consulta de Carga*",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"Não foi possível localizar a carga com as informações fornecidas:\n_{mensagem_erro}_",
        "",
        "💡 *Dicas para consultar com sucesso:*",
        "• Envie o seu *CNPJ ou CPF* acompanhado da *Nota Fiscal* ou *Pedido*.",
        "• Exemplo: `33.041.260/1414-93 4224761`",
        "• Exemplo (CPF): `026.026.026-55 130516`",
        "• Ou envie a *chave de acesso de 44 dígitos* da NF-e.",
        "━━━━━━━━━━━━━━━━━━━━━━"
    ]
    return "\n".join(linhas)

def formatar_mensagem_saudacao():
    """Mensagem de boas-vindas no layout do usuário."""
    return (
        "📦 MP CARGAS | RASTREAMENTO\n\n"
        "Olá! Para consultar sua carga, escolha uma opção:\n\n"
        "📄 CNPJ + Nota Fiscal\n"
        "👤 CPF + Nota Fiscal\n"
        "🔑 Chave DANFE (44 dígitos)\n"
        "📋 CNPJ + Pedido\n"
        "📦 CNPJ + Coleta\n\n"
        "💬 Envie os dados da opção escolhida."
    )


def formatar_mensagem_falta_cnpj(id_ref):
    """Quando o usuário enviou apenas o número da NF, Pedido ou Coleta."""
    return (
        f"📄 Recebi a informação *{id_ref}*!\n\n"
        "Para que eu possa consultar na transportadora, por favor envie agora o seu *CNPJ* (empresa) ou *CPF* (pessoa física).\n\n"
        "💡 *Exemplo:* `33.041.260/1414-93` ou `026.026.026-55`"
    )


def formatar_mensagem_falta_nf(doc_formatado, tipo_doc="CNPJ"):
    """Quando o usuário enviou apenas o CNPJ ou CPF."""
    return (
        f"🏢 Recebi o {tipo_doc} *{doc_formatado}*!\n\n"
        "Agora, por favor, envie o *número da Nota Fiscal (NF)*, *Pedido* ou *Coleta* para que eu possa localizar sua carga."
    )

