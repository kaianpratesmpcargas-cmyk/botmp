import os
import re
import requests
from datetime import datetime

API_TRACKING = "https://ssw.inf.br/api/tracking"
API_TRACKING_DANFE = "https://ssw.inf.br/api/trackingdanfe"
API_TRACKING_PAG = "https://ssw.inf.br/api/trackingpag"
API_TRACKING_DEST = "https://ssw.inf.br/api/trackingdest"
API_TRACKING_PF = "https://ssw.inf.br/api/trackingpf"
DEFAULT_TIMEOUT = 30


def limpar_numeros(valor):
    """Remove qualquer caractere que não seja dígito numérico."""
    if not valor:
        return ""
    return "".join(caractere for caractere in str(valor) if caractere.isdigit())


def formatar_cnpj(cnpj):
    """Formata string numérica de 14 dígitos em XX.XXX.XXX/XXXX-XX."""
    c = limpar_numeros(cnpj)
    if len(c) == 14:
        return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:14]}"
    return c or "Não informado"


def formatar_cpf(cpf):
    """Formata string numérica de 11 dígitos em XXX.XXX.XXX-XX."""
    c = limpar_numeros(cpf)
    if len(c) == 11:
        return f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:11]}"
    return c or "Não informado"


def formatar_documento(doc):
    """Formata dinamicamente se for CPF (11 dígitos) ou CNPJ (14 dígitos)."""
    c = limpar_numeros(doc)
    if len(c) == 11:
        return formatar_cpf(c)
    if len(c) == 14:
        return formatar_cnpj(c)
    return str(doc or "Não informado")


def formatar_data(data):
    """Converte data ISO ou formatos conhecidos para 'DD/MM/YYYY às HH:MM'."""
    if not data:
        return "Data não informada"
    try:
        dt = datetime.fromisoformat(str(data).replace("Z", ""))
        return dt.strftime("%d/%m/%Y às %H:%M")
    except Exception:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(str(data).strip(), fmt)
                if "%H" in fmt:
                    return dt.strftime("%d/%m/%Y às %H:%M")
                return dt.strftime("%d/%m/%Y")
            except Exception:
                continue
        return str(data)


def status_amigavel(evento):
    """Mapeia o código ou texto da ocorrência para um status legível e humanizado."""
    codigo = str(evento.get("codigo_ocorrencia") or evento.get("codigo_ssw") or "").strip()
    ocorrencia = str(evento.get("ocorrencia", "")).upper()
    descricao = str(evento.get("descricao", "")).upper()

    # Códigos padrões SSW
    if codigo == "01":
        return "ENTREGUE"
    if codigo == "82":
        return "EM TRANSPORTE"
    if codigo == "84":
        return "CHEGOU NA UNIDADE"
    if codigo == "80":
        return "DOCUMENTO EMITIDO"

    # Verificação por texto na ocorrência ou descrição
    texto_combinado = f"{ocorrencia} {descricao}"
    if "ENTREGUE" in texto_combinado or "MERCADORIA ENTREGUE" in texto_combinado:
        return "ENTREGUE"
    if "SAIDA" in texto_combinado or "EM VIAGEM" in texto_combinado or "TRANSFERENCIA" in texto_combinado:
        return "EM TRANSPORTE"
    if "SAIU PARA ENTREGA" in texto_combinado or "EM ROTA DE ENTREGA" in texto_combinado:
        return "SAIU PARA ENTREGA"
    if "CHEGADA" in texto_combinado or "RECEBIDO NA UNIDADE" in texto_combinado:
        return "CHEGOU NA UNIDADE"
    if "EMISSAO" in texto_combinado or "DOCUMENTO" in texto_combinado:
        return "DOCUMENTO EMITIDO"

    return evento.get("ocorrencia") or evento.get("descricao") or "Atualização"


def emoji_status(status):
    """Retorna um emoji representativo para o status da carga."""
    status_upper = str(status).upper()
    if "ENTREGUE" in status_upper:
        return "✅"
    if "SAIU PARA ENTREGA" in status_upper:
        return "🚛"
    if "EM TRANSPORTE" in status_upper or "TRANSPORTE" in status_upper:
        return "🚚"
    if "CHEGOU NA UNIDADE" in status_upper:
        return "🏢"
    if "DOCUMENTO EMITIDO" in status_upper:
        return "📄"
    if "PROBLEMA" in status_upper or "EXTRAVIO" in status_upper or "AVARIA" in status_upper or "RETEN" in status_upper:
        return "⚠️"
    return "📦"


def ordenar_tracking(tracking):
    """Ordena a lista de tracking de forma cronológica decrescente (mais recente primeiro)."""
    if not tracking:
        return []

    def obter_chave_data(evento):
        return str(evento.get("data_hora_efetiva") or evento.get("data_hora") or "")

    tracking_ordenado = sorted(tracking, key=obter_chave_data, reverse=True)

    for evento in tracking_ordenado:
        raw_date = evento.get("data_hora_efetiva") or evento.get("data_hora", "")
        evento["data_formatada"] = formatar_data(raw_date)
        evento["status_amigavel"] = status_amigavel(evento)
        evento["emoji"] = emoji_status(evento["status_amigavel"])

    return tracking_ordenado


def extrair_metadados_texto(texto_completo):
    """Extrai informações adicionais como Destino e Previsão via Regex resiliente."""
    dados_extraidos = {}

    match_destino = re.search(r"Destino:\s*([^.\n\r]+)", texto_completo, re.IGNORECASE)
    if match_destino:
        dados_extraidos["destino"] = match_destino.group(1).strip()

    match_previsao = re.search(r"Previs[aã]o\s+de\s+entrega:\s*([^.\n\r]+)", texto_completo, re.IGNORECASE)
    if match_previsao:
        dados_extraidos["previsao"] = match_previsao.group(1).strip()

    match_pedido = re.search(r"Pedido:\s*([^.\n\r]+)", texto_completo, re.IGNORECASE)
    if match_pedido:
        dados_extraidos["pedido"] = match_pedido.group(1).strip()

    return dados_extraidos


# ==============================================================================
# MÉTODOS OFICIAIS DE CONSULTA ÀS APIS DA SSW
# ==============================================================================

def consultar_chave(chave):
    """Faz a consulta na API SSW pelo número da chave de acesso NF-e (44 dígitos)."""
    chave_limpa = limpar_numeros(chave)
    if len(chave_limpa) != 44:
        raise ValueError("A chave de acesso da NF-e deve conter exatamente 44 dígitos numéricos.")

    resposta = requests.post(
        API_TRACKING_DANFE,
        json={"chave_nfe": chave_limpa},
        headers={"Content-Type": "application/json"},
        timeout=DEFAULT_TIMEOUT
    )
    resposta.raise_for_status()
    return resposta.json()


def consultar_nf(cnpj, nro_nf, senha=None):
    """Faz a consulta padrão na API SSW (Remetente) por CNPJ + Número da NF."""
    return consultar_remetente(cnpj=cnpj, nro_nf=nro_nf, senha=senha)


def consultar_remetente(cnpj, nro_nf=None, pedido=None, chave_nfe=None, senha=None):
    """
    Consulta o endpoint de Remetente (https://ssw.inf.br/api/tracking).
    """
    cnpj_limpo = limpar_numeros(cnpj)
    if not cnpj_limpo:
        raise ValueError("O CNPJ do remetente é obrigatório.")

    payload = {"cnpj": cnpj_limpo}

    if nro_nf:
        payload["nro_nf"] = str(limpar_numeros(nro_nf))
    elif pedido:
        payload["pedido"] = str(pedido).strip()
    elif chave_nfe:
        payload["chave_nfe"] = str(limpar_numeros(chave_nfe))
    else:
        raise ValueError("Informe ao menos um parâmetro identificador (NF, Pedido ou Chave).")

    if senha and str(senha).strip():
        payload["senha"] = str(senha).strip()

    resposta = requests.post(
        API_TRACKING,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=DEFAULT_TIMEOUT
    )
    resposta.raise_for_status()
    return resposta.json()


def consultar_pagador(cnpj, nro_nf=None, pedido=None, chave_nfe=None, nro_coleta=None, senha=None, sigla_emp=None):
    """
    SSW Tracking Pagador WebAPI (https://ssw.inf.br/api/trackingpag).
    Requer: cnpj (pagador) + EXATAMENTE UM de (nro_nf, pedido, chave_nfe, nro_coleta).
    A senha NÃO é obrigatória.
    """
    cnpj_limpo = limpar_numeros(cnpj)
    if 11 < len(cnpj_limpo) < 14:
        cnpj_limpo = cnpj_limpo.zfill(14)

    if not cnpj_limpo or len(cnpj_limpo) != 14:
        raise ValueError("O CNPJ do pagador é obrigatório e deve conter 14 dígitos numéricos.")

    payload = {"cnpj": cnpj_limpo}

    if senha and str(senha).strip():
        payload["senha"] = str(senha).strip()

    if sigla_emp and str(sigla_emp).strip():
        payload["sigla_emp"] = str(sigla_emp).strip()

    nf_limpa = limpar_numeros(nro_nf)
    pedido_limpo = str(pedido).strip() if pedido else ""
    chave_limpa = limpar_numeros(chave_nfe)
    coleta_limpa = limpar_numeros(nro_coleta)

    # Envia somente UM dos quatro parâmetros
    if nf_limpa:
        payload["nro_nf"] = int(nf_limpa)
    elif pedido_limpo:
        payload["pedido"] = pedido_limpo
    elif chave_limpa:
        payload["chave_nfe"] = chave_limpa
    elif coleta_limpa:
        payload["nro_coleta"] = int(coleta_limpa)
    else:
        raise ValueError("Informe exatamente um dos seguintes parâmetros: nro_nf, pedido, chave_nfe ou nro_coleta.")

    resposta = requests.post(
        API_TRACKING_PAG,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=DEFAULT_TIMEOUT
    )
    try:
        return resposta.json()
    except Exception:
        resposta.raise_for_status()
        return {"success": False, "message": "Resposta inválida da transportadora"}


def consultar_destinatario(cnpj, nro_nf=None, pedido=None, chave_nfe=None, nro_coleta=None, senha=None, sigla_emp=None):
    """
    SSW Tracking Destinatário WebAPI (https://ssw.inf.br/api/trackingdest).
    Requer: cnpj (destinatário) + EXATAMENTE UM de (nro_nf, pedido, chave_nfe, nro_coleta).
    A senha NÃO é obrigatória. Caso informada, pode liberar comprovante de entrega.
    """
    cnpj_limpo = limpar_numeros(cnpj)
    if 11 < len(cnpj_limpo) < 14:
        cnpj_limpo = cnpj_limpo.zfill(14)

    if not cnpj_limpo or len(cnpj_limpo) != 14:
        raise ValueError("O CNPJ do destinatário é obrigatório e deve conter 14 dígitos numéricos.")

    payload = {"cnpj": cnpj_limpo}

    if senha and str(senha).strip():
        payload["senha"] = str(senha).strip()

    if sigla_emp and str(sigla_emp).strip():
        payload["sigla_emp"] = str(sigla_emp).strip()

    nf_limpa = limpar_numeros(nro_nf)
    pedido_limpo = str(pedido).strip() if pedido else ""
    chave_limpa = limpar_numeros(chave_nfe)
    coleta_limpa = limpar_numeros(nro_coleta)

    # Envia somente UM dos quatro parâmetros
    if nf_limpa:
        payload["nro_nf"] = int(nf_limpa)
    elif pedido_limpo:
        payload["pedido"] = pedido_limpo
    elif chave_limpa:
        payload["chave_nfe"] = chave_limpa
    elif coleta_limpa:
        payload["nro_coleta"] = int(coleta_limpa)
    else:
        raise ValueError("Informe exatamente um dos seguintes parâmetros: nro_nf, pedido, chave_nfe ou nro_coleta.")

    resposta = requests.post(
        API_TRACKING_DEST,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=DEFAULT_TIMEOUT
    )
    try:
        return resposta.json()
    except Exception:
        resposta.raise_for_status()
        return {"success": False, "message": "Resposta inválida da transportadora"}



def consultar_pf(cpf, nro_nf=None, pedido=None, chave_nfe=None, dominio=None, usuario=None, senha=None):
    """
    SSW Tracking WebAPI - Pessoa Física (https://ssw.inf.br/api/trackingpf).
    Requer: dominio, usuario, senha (da transportadora) + cpf (do destinatário PF).
    Parâmetros opcionais: nro_nf, pedido, chave_nfe.
    """
    cpf_limpo = limpar_numeros(cpf)
    if not cpf_limpo or len(cpf_limpo) != 11:
        raise ValueError("O CPF do destinatário deve conter 11 dígitos numéricos.")

    dom = dominio or os.environ.get("PF_DOMINIO") or os.environ.get("SSW_DOMINIO") or "TES"
    usr = usuario or os.environ.get("PF_USUARIO") or os.environ.get("SSW_USUARIO") or "sswlogin"
    pwd = senha or os.environ.get("PF_SENHA") or os.environ.get("SSW_SENHA") or "SWORDFISH"

    payload = {
        "dominio": str(dom).strip(),
        "usuario": str(usr).strip(),
        "senha": str(pwd).strip(),
        "cpf": cpf_limpo
    }

    if nro_nf:
        payload["nro_nf"] = int(limpar_numeros(nro_nf))
    elif pedido:
        payload["pedido"] = str(pedido).strip()
    elif chave_nfe:
        payload["chave_nfe"] = str(limpar_numeros(chave_nfe))

    resposta = requests.post(
        API_TRACKING_PF,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=DEFAULT_TIMEOUT
    )
    resposta.raise_for_status()
    return resposta.json()


# ==============================================================================
# TRATAMENTO E NORMALIZAÇÃO DE RESULTADOS
# ==============================================================================

def preparar_resultado(resultado, cnpj="", cpf="", nro_nf="", chave_nfe="", pedido="", nro_coleta="", tipo_consulta=""):
    """
    Processa a resposta da API SSW (qualquer endpoint), organizando em uma estrutura limpa
    e rica com informações de cabeçalho, última ocorrência, histórico e comprovante se houver.
    """
    if not resultado:
        return None, "Não foi recebida nenhuma resposta do servidor."

    if not resultado.get("success"):
        return None, resultado.get("message", "Documento não localizado na base da transportadora.")

    documento = resultado.get("documento") or {}
    header = resultado.get("header") or documento.get("header") or {}
    tracking_raw = resultado.get("tracking") or documento.get("tracking") or []

    if not tracking_raw:
        return None, "O documento foi localizado, mas ainda não possui movimentações disponíveis."

    tracking = ordenar_tracking(tracking_raw)

    texto_completo = " ".join(
        str(evento.get("descricao", "")) + " " + str(evento.get("ocorrencia", ""))
        for evento in tracking
    )
    metadados = extrair_metadados_texto(texto_completo)

    nf_detectada = (
        nro_nf
        or header.get("nro_nf")
        or header.get("numero_nf")
        or "Não informado"
    )

    pedido_detectado = (
        pedido
        or header.get("pedido")
        or metadados.get("pedido")
        or "Não informado"
    )

    origem = "Não informado"
    if tracking:
        evento_origem = tracking[-1]
        origem = (
            evento_origem.get("cidade")
            or evento_origem.get("filial")
            or "Não informado"
        )

    destino = metadados.get("destino", "Não informado")
    previsao = metadados.get("previsao", "Não informada")

    # Documento informado ou detectado
    doc_formatado = "Não informado"
    tipo_doc = "CNPJ"
    if cpf:
        doc_formatado = formatar_cpf(cpf)
        tipo_doc = "CPF"
    elif cnpj:
        doc_formatado = formatar_cnpj(cnpj)
        tipo_doc = "CNPJ"
    else:
        doc_bruto = header.get("cnpj") or header.get("cpf") or ""
        if not doc_bruto and chave_nfe and len(limpar_numeros(chave_nfe)) == 44:
            doc_bruto = limpar_numeros(chave_nfe)[6:20]
        if doc_bruto:
            doc_formatado = formatar_documento(doc_bruto)
            tipo_doc = "CPF" if len(limpar_numeros(doc_bruto)) == 11 else "CNPJ"

    # Comprovante de entrega se retornado
    comprovante = (
        header.get("comprovante")
        or header.get("comprovante_entrega")
        or documento.get("comprovante")
        or documento.get("comprovante_entrega")
        or resultado.get("comprovante")
        or ""
    )

    # Pagador detectado
    pagador_detectado = (
        header.get("pagador")
        or documento.get("pagador")
        or resultado.get("pagador")
        or (doc_formatado if tipo_consulta == "Pagador" else "Não informado")
    )

    dados = {
        "ultima": tracking[0],
        "tracking": tracking,
        "info": {
            "nf": nf_detectada,
            "documento": doc_formatado,
            "tipo_documento": tipo_doc,
            "tipo_consulta": tipo_consulta or "Consulta de Carga",
            "remetente": header.get("remetente", "Não informado"),
            "destinatario": header.get("destinatario", "Não informado"),
            "pagador": pagador_detectado,
            "pedido": pedido_detectado,
            "nro_coleta": nro_coleta or header.get("nro_coleta", "Não informado"),
            "ctrc": header.get("ctrc", "Não informado"),
            "cte": header.get("cte", "Não informado"),
            "origem": origem,
            "destino": destino,

            "previsao": previsao,
            "chave_nfe": chave_nfe or header.get("chave_nfe", ""),
            "comprovante": comprovante
        }
    }

    return dados, None


# Memória de conversação por remetente/usuário
SESSOES_BOT = {}


def extrair_entidades_mensagem(texto):
    """
    Parser robusto em linguagem natural capaz de extrair CPF, CNPJ, NF, Pedido,
    Coleta, Chave de NF-e (44 dígitos) e intenções/saudações.
    """
    t = str(texto or "").strip()

    # 1. Saudação ou comandos de menu (sem números)
    if re.match(r"^(oi|ol[aá]|bom dia|boa tarde|boa noite|menu|ajuda|in[ií]cio|come[cç]ar|hey|opa|como rastrear|rastreio)\b", t, re.IGNORECASE):
        if not re.search(r"\d", t):
            return {"tipo": "saudacao"}

    # 2. Chave de 44 dígitos
    t_sem_espacos = re.sub(r"\s+", "", t)
    m_chave = re.search(r"\b(\d{44})\b", t_sem_espacos)
    if m_chave:
        return {"tipo": "chave", "chave": m_chave.group(1)}

    # 3. CNPJ (formatado ou 14 dígitos contínuos)
    m_cnpj = re.search(r"(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})", t)
    if not m_cnpj:
        m_cnpj = re.search(r"\b(\d{14})\b", t)

    cnpj_encontrado = None
    texto_restante = t
    if m_cnpj:
        cnpj_raw = m_cnpj.group(1)
        cnpj_encontrado = limpar_numeros(cnpj_raw)
        texto_restante = texto_restante.replace(cnpj_raw, " ")

    # 4. CPF (formatado ou 11 dígitos contínuos, caso não seja CNPJ)
    cpf_encontrado = None
    if not cnpj_encontrado:
        m_cpf = re.search(r"(\d{3}\.\d{3}\.\d{3}-\d{2})", texto_restante)
        if not m_cpf:
            m_cpf = re.search(r"\b(\d{11})\b", texto_restante)
        if m_cpf:
            cpf_raw = m_cpf.group(1)
            cpf_encontrado = limpar_numeros(cpf_raw)
            texto_restante = texto_restante.replace(cpf_raw, " ")

    # 5. Pedido (ex: pedido 1234, ped: A123)
    m_pedido = re.search(r"(?:pedido|ped)\s*[:=]?\s*([A-Za-z0-9\-_]+)\b", texto_restante, re.IGNORECASE)
    pedido_encontrado = None
    if m_pedido:
        pedido_encontrado = m_pedido.group(1)
        texto_restante = texto_restante.replace(m_pedido.group(0), " ")

    # 6. Coleta (ex: coleta 65981)
    m_coleta = re.search(r"(?:coleta|nro_coleta)\s*[:=]?\s*(\d+)\b", texto_restante, re.IGNORECASE)
    coleta_encontrada = None
    if m_coleta:
        coleta_encontrada = m_coleta.group(1)
        texto_restante = texto_restante.replace(m_coleta.group(0), " ")

    # 7. Nota Fiscal (ex: nf 4224761, nota fiscal: 130516 ou número isolado)
    m_nf = re.search(r"(?:nf|nota|nfe|nota\s*fiscal|n[oº])\s*[:=]?\s*(\d{1,9})\b", texto_restante, re.IGNORECASE)
    nf_encontrada = None
    if m_nf:
        nf_encontrada = m_nf.group(1)
    else:
        candidatos = re.findall(r"\b\d{1,9}\b", texto_restante)
        if candidatos:
            nf_encontrada = candidatos[0]

    # 8. Detecção de intenção de modalidade explícita
    modalidade = None
    if re.search(r"\b(pagador|pagadora|frete\s*pago)\b", t, re.IGNORECASE):
        modalidade = "pagador"
    elif re.search(r"\b(destinat[aá]rio|destinataria|recebedor)\b", t, re.IGNORECASE):
        modalidade = "destinatario"
    elif re.search(r"\b(remetente|embarcador|expedidor)\b", t, re.IGNORECASE):
        modalidade = "remetente"

    return {
        "tipo": "consulta",
        "cnpj": cnpj_encontrado,
        "cpf": cpf_encontrado,
        "nf": nf_encontrada,
        "pedido": pedido_encontrado,
        "coleta": coleta_encontrada,
        "modalidade": modalidade
    }


def consultar_inteligente(
    termo=None,
    chave=None,
    chave_nfe=None,
    cnpj=None,
    cpf=None,
    nro_nf=None,
    pedido=None,
    nro_coleta=None,
    coleta=None,
    senha=None,
    sigla_emp=None,
    tipo=None,
    usuario=None,
):
    """
    Função universal de consulta para bots e web:
    - Entende saudações e dúvidas sobre cidades/prazos
    - Suporta CPF (Pessoa Física) e CNPJ (Destinatário, Remetente, Pagador)
    - Busca inteligente em cascata quando o tipo não for especificado
    - Mantém memória de conversa caso o usuário envie dados em etapas
    """
    chave_final = chave or chave_nfe
    coleta_final = nro_coleta or coleta

    # 1. Consulta direta por Chave DANFE (44 dígitos) apenas se NÃO fornecido CNPJ nem CPF
    if chave_final and not cnpj and not cpf:
        chave_limpa = limpar_numeros(chave_final)
        if len(chave_limpa) == 44:
            resultado = consultar_chave(chave_limpa)
            return preparar_resultado(resultado, chave_nfe=chave_limpa, tipo_consulta="Chave DANFE")

    # 2. Se for CPF (Pessoa Física)
    if cpf:
        cpf_limpo = limpar_numeros(cpf)
        if 9 < len(cpf_limpo) < 11:
            cpf_limpo = cpf_limpo.zfill(11)
        if len(cpf_limpo) == 11:
            try:
                res = consultar_pf(
                    cpf=cpf_limpo,
                    nro_nf=nro_nf,
                    pedido=pedido,
                    chave_nfe=chave_final,
                    senha=senha
                )
                return preparar_resultado(
                    res,
                    cpf=cpf_limpo,
                    nro_nf=nro_nf,
                    pedido=pedido,
                    chave_nfe=chave_final,
                    tipo_consulta="Pessoa Física"
                )
            except Exception as e:
                return None, str(e)

    # 3. Se for CNPJ com tipo explícito ou automático
    if cnpj and (nro_nf or pedido or chave_final or coleta_final):
        cnpj_limpo = limpar_numeros(cnpj)
        if 11 < len(cnpj_limpo) < 14:
            cnpj_limpo = cnpj_limpo.zfill(14)
        tipo_lower = (tipo or "").strip().lower()

        if tipo_lower in ("destinatario", "dest"):
            res = consultar_destinatario(cnpj_limpo, nro_nf=nro_nf, pedido=pedido, chave_nfe=chave_final, nro_coleta=coleta_final, senha=senha, sigla_emp=sigla_emp)
            return preparar_resultado(res, cnpj=cnpj_limpo, nro_nf=nro_nf, pedido=pedido, chave_nfe=chave_final, nro_coleta=coleta_final, tipo_consulta="Destinatário")

        if tipo_lower in ("pagador", "pag"):
            res = consultar_pagador(cnpj_limpo, nro_nf=nro_nf, pedido=pedido, chave_nfe=chave_final, nro_coleta=coleta_final, senha=senha, sigla_emp=sigla_emp)
            return preparar_resultado(res, cnpj=cnpj_limpo, nro_nf=nro_nf, pedido=pedido, chave_nfe=chave_final, nro_coleta=coleta_final, tipo_consulta="Pagador")

        if tipo_lower in ("remetente", "rem"):
            res = consultar_remetente(cnpj_limpo, nro_nf=nro_nf, pedido=pedido, chave_nfe=chave_final, senha=senha)
            return preparar_resultado(res, cnpj=cnpj_limpo, nro_nf=nro_nf, pedido=pedido, chave_nfe=chave_final, tipo_consulta="Remetente")

        # Se tipo for automático (ou não informado), faz cascata inteligente
        tentativas = [
            ("Destinatário", lambda: consultar_destinatario(cnpj_limpo, nro_nf=nro_nf, pedido=pedido, chave_nfe=chave_final, nro_coleta=coleta_final, senha=senha, sigla_emp=sigla_emp)),
        ]
        # Remetente não suporta coleta, então só tenta se houver NF, pedido ou chave
        if nro_nf or pedido or chave_final:
            tentativas.append(
                ("Remetente", lambda: consultar_remetente(cnpj_limpo, nro_nf=nro_nf, pedido=pedido, chave_nfe=chave_final, senha=senha))
            )
        tentativas.append(
            ("Pagador", lambda: consultar_pagador(cnpj_limpo, nro_nf=nro_nf, pedido=pedido, chave_nfe=chave_final, nro_coleta=coleta_final, senha=senha, sigla_emp=sigla_emp))
        )

        ultimo_erro = None
        for nome_tipo, func_consulta in tentativas:
            try:
                res = func_consulta()
                if res and res.get("success"):
                    return preparar_resultado(
                        res,
                        cnpj=cnpj_limpo,
                        nro_nf=nro_nf,
                        pedido=pedido,
                        chave_nfe=chave_final,
                        nro_coleta=coleta_final,
                        tipo_consulta=nome_tipo
                    )
                if res and not res.get("success"):
                    ultimo_erro = res.get("message")
            except Exception as ex:
                ultimo_erro = str(ex)

        msg_final = ultimo_erro or "Documento não localizado na transportadora (verificado como Destinatário, Remetente e Pagador)."
        return None, msg_final


    # 4. Processamento de Texto Livre (Chatbots de WhatsApp/Telegram ou campo único)
    if termo:
        parse = extrair_entidades_mensagem(termo)
        user_key = str(usuario or "anonimo")

        # Saudação
        if parse.get("tipo") == "saudacao":
            return None, "SAUDACAO"

        # Dúvidas gerais sobre prazos / cidades / filiais
        if not (parse.get("cnpj") or parse.get("cpf") or parse.get("chave")):
            try:
                from services.pracas_service import responder_duvida_geral
                resposta_duvida = responder_duvida_geral(termo)
                if resposta_duvida:
                    return None, f"DUVIDA:{resposta_duvida}"
            except Exception:
                pass

        # Chave DANFE identificada no texto
        if parse.get("tipo") == "chave":
            chave_t = parse["chave"]
            res = consultar_chave(chave_t)
            return preparar_resultado(res, chave_nfe=chave_t, tipo_consulta="Chave DANFE")

        cnpj_cand = parse.get("cnpj")
        cpf_cand = parse.get("cpf")
        nf_cand = parse.get("nf")
        pedido_cand = parse.get("pedido")
        coleta_cand = parse.get("coleta")

        # Recupera sessão anterior
        sessao_anterior = SESSOES_BOT.get(user_key, {})
        if not cnpj_cand and sessao_anterior.get("cnpj"):
            cnpj_cand = sessao_anterior.get("cnpj")
        if not cpf_cand and sessao_anterior.get("cpf"):
            cpf_cand = sessao_anterior.get("cpf")
        if not nf_cand and sessao_anterior.get("nf"):
            nf_cand = sessao_anterior.get("nf")
        if not pedido_cand and sessao_anterior.get("pedido"):
            pedido_cand = sessao_anterior.get("pedido")
        if not coleta_cand and sessao_anterior.get("coleta"):
            coleta_cand = sessao_anterior.get("coleta")

        tem_doc = bool(cnpj_cand or cpf_cand)
        tem_identificador = bool(nf_cand or pedido_cand or coleta_cand)

        # Se temos documento e identificador: executa!
        if tem_doc and tem_identificador:
            SESSOES_BOT.pop(user_key, None)
            if cpf_cand:
                return consultar_inteligente(
                    cpf=cpf_cand,
                    nro_nf=nf_cand,
                    pedido=pedido_cand,
                    senha=senha,
                    tipo="pf"
                )
            return consultar_inteligente(
                cnpj=cnpj_cand,
                nro_nf=nf_cand,
                pedido=pedido_cand,
                nro_coleta=coleta_cand,
                senha=senha,
                sigla_emp=sigla_emp,
                tipo="auto"
            )

        # Se só temos o identificador (NF / Pedido / Coleta), salva e pede o CNPJ ou CPF
        if tem_identificador and not tem_doc:
            SESSOES_BOT[user_key] = {
                "nf": nf_cand,
                "pedido": pedido_cand,
                "coleta": coleta_cand
            }
            id_ref = nf_cand or pedido_cand or coleta_cand
            return None, f"FALTA_DOC:{id_ref}"

        # Se só temos o documento (CNPJ ou CPF), salva e pede o identificador
        if tem_doc and not tem_identificador:
            if cpf_cand:
                SESSOES_BOT[user_key] = {"cpf": cpf_cand}
                return None, f"FALTA_ID:CPF:{cpf_cand}"
            SESSOES_BOT[user_key] = {"cnpj": cnpj_cand}
            return None, f"FALTA_ID:CNPJ:{cnpj_cand}"

        return None, "Formato não compreendido. Envie seu CNPJ ou CPF junto com o número da Nota Fiscal ou Pedido (ex: `33.041.260/1414-93 4224761`)."

    return None, "Nenhum parâmetro de consulta fornecido."
