import os
import sys
import requests
from flask import Flask, request, render_template, jsonify

# Configuração segura de codificação no Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


from services.ssw_service import (
    consultar_chave,
    consultar_nf,
    consultar_remetente,
    consultar_destinatario,
    consultar_pagador,
    consultar_pf,
    consultar_inteligente,
    preparar_resultado,
    limpar_numeros,
    formatar_documento,
)
from utils.bot_formatter import (
    formatar_mensagem_whatsapp,
    formatar_mensagem_erro,
    formatar_mensagem_saudacao,
    formatar_mensagem_falta_cnpj,
    formatar_mensagem_falta_nf,
)

app = Flask(__name__)


def extrair_parametros():
    """Captura parâmetros tanto de JSON (POST) quanto de query strings (GET) ou formulários."""
    dados = {}
    if request.is_json:
        dados.update(request.get_json(silent=True) or {})
    if request.args:
        dados.update(request.args.to_dict())
    if request.form:
        dados.update(request.form.to_dict())
    return dados


# ==============================================================================
# ROTAS DA INTERFACE WEB
# ==============================================================================

@app.route("/", methods=["GET", "POST"])
def index():
    erro = None
    dados = None
    documento = ""
    valor_busca = ""
    criterio = "nro_nf"
    tipo_consulta = "auto"
    senha = ""

    if request.method == "POST":
        # Suporta tanto novos campos quanto campos legados
        documento = (request.form.get("documento") or request.form.get("cnpj") or "").strip()
        criterio = request.form.get("criterio", "nro_nf").strip()
        valor_busca = (request.form.get("valor_busca") or request.form.get("nro_nf") or "").strip()
        tipo_consulta = request.form.get("tipo_consulta", "auto").strip()
        senha = request.form.get("senha", "").strip()

        doc_limpo = limpar_numeros(documento)

        if not doc_limpo:
            erro = "Informe o CNPJ ou CPF para prosseguir com a consulta."
        elif not valor_busca:
            erro = "Informe o número da Nota Fiscal, Pedido, Chave da NF-e ou Coleta."
        else:
            nro_nf = valor_busca if criterio == "nro_nf" else None
            pedido = valor_busca if criterio == "pedido" else None
            chave = valor_busca if criterio == "chave_nfe" else None
            nro_coleta = valor_busca if criterio == "nro_coleta" else None

            is_cpf = len(doc_limpo) == 11
            cpf_param = doc_limpo if is_cpf else None
            cnpj_param = doc_limpo if not is_cpf else None

            try:
                dados, erro = consultar_inteligente(
                    cnpj=cnpj_param,
                    cpf=cpf_param,
                    nro_nf=nro_nf,
                    pedido=pedido,
                    chave=chave,
                    nro_coleta=nro_coleta,
                    senha=senha if senha else None,
                    tipo="pf" if is_cpf else tipo_consulta,
                )
            except requests.exceptions.Timeout:
                erro = "A consulta demorou muito para responder (timeout). Tente novamente."
            except requests.exceptions.ConnectionError:
                erro = "Não foi possível conectar ao servidor da SSW."
            except requests.exceptions.HTTPError as erro_http:
                try:
                    resposta = erro_http.response.json()
                    erro = resposta.get("message", "O servidor SSW retornou um erro.")
                except Exception:
                    erro = f"O servidor SSW retornou erro HTTP {erro_http.response.status_code}."
            except ValueError as err_val:
                erro = str(err_val)
            except Exception as erro_geral:
                erro = "Ocorreu um erro inesperado durante a consulta."
                print(f"[ERRO GERAL]: {erro_geral}")

    return render_template(
        "index.html",
        erro=erro,
        dados=dados,
        documento=documento,
        valor_busca=valor_busca,
        criterio=criterio,
        tipo_consulta=tipo_consulta,
        cnpj=documento,
        nro_nf=valor_busca,
    )


# ==============================================================================
# ENDPOINTS REST API
# ==============================================================================

@app.route("/api/v1/health", methods=["GET"])
def healthcheck():
    """Verifica a saúde do serviço."""
    return jsonify({
        "status": "online",
        "servico": "MP CARGAS - API de Rastreamento",
        "versao": "2.1.0",
        "endpoints_disponiveis": [
            "/api/v1/tracking/destinatario",
            "/api/v1/tracking/pagador",
            "/api/v1/tracking/pf",
            "/api/v1/tracking/remetente",
            "/api/v1/tracking/danfe",
            "/api/v1/tracking/nf",
            "/api/v1/bot/consulta"
        ]
    }), 200


@app.route("/api/v1/tracking/destinatario", methods=["GET", "POST"])
def api_tracking_destinatario():
    """
    SSW Tracking Destinatário WebAPI (https://ssw.inf.br/api/trackingdest).
    Parâmetros: cnpj (obrigatório), senha (opcional), sigla_emp (opcional)
    E exatamente um entre: nro_nf, pedido, chave_nfe, nro_coleta.
    """
    payload = extrair_parametros()
    cnpj = limpar_numeros(payload.get("cnpj", ""))
    senha = payload.get("senha")
    sigla_emp = payload.get("sigla_emp")

    nro_nf = payload.get("nro_nf") or payload.get("nf")
    pedido = payload.get("pedido")
    chave_nfe = payload.get("chave_nfe") or payload.get("chave")
    nro_coleta = payload.get("nro_coleta") or payload.get("coleta")

    if not cnpj or not (nro_nf or pedido or chave_nfe or nro_coleta):
        return jsonify({
            "servico": "MP CARGAS - API Rastreamento por Destinatário",
            "metodos_aceitos": ["GET", "POST"],
            "parametros": {
                "cnpj": "CNPJ do destinatário da carga (obrigatório)",
                "senha": "Senha de acesso disponibilizada pela transportadora (opcional)",
                "sigla_emp": "Sigla da empresa para filtrar (opcional)",
                "identificador": "Envie exatamente UM entre: nro_nf, pedido, chave_nfe ou nro_coleta"
            },
            "exemplo": "/api/v1/tracking/destinatario?cnpj=02012862003770&nro_nf=130516"
        }), 200

    try:
        resultado = consultar_destinatario(
            cnpj=cnpj,
            nro_nf=nro_nf,
            pedido=pedido,
            chave_nfe=chave_nfe,
            nro_coleta=nro_coleta,
            senha=senha,
            sigla_emp=sigla_emp
        )
        dados, erro = preparar_resultado(
            resultado,
            cnpj=cnpj,
            nro_nf=nro_nf,
            chave_nfe=chave_nfe,
            pedido=pedido,
            nro_coleta=nro_coleta,
            tipo_consulta="Destinatário"
        )
        if erro:
            return jsonify({"success": False, "message": erro}), 404
        return jsonify({"success": True, "dados": dados}), 200
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "message": f"Erro de comunicação com a transportadora: {str(e)}"}), 502
    except ValueError as ve:
        return jsonify({"success": False, "message": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro interno: {str(e)}"}), 500


@app.route("/api/v1/tracking/pagador", methods=["GET", "POST"])
def api_tracking_pagador():
    """
    SSW Tracking Pagador WebAPI (https://ssw.inf.br/api/trackingpag).
    Parâmetros: cnpj (obrigatório), senha (opcional), sigla_emp (opcional)
    E exatamente um entre: nro_nf, pedido, chave_nfe, nro_coleta.
    """
    payload = extrair_parametros()
    cnpj = limpar_numeros(payload.get("cnpj", ""))
    senha = payload.get("senha")
    sigla_emp = payload.get("sigla_emp")

    nro_nf = payload.get("nro_nf") or payload.get("nf")
    pedido = payload.get("pedido")
    chave_nfe = payload.get("chave_nfe") or payload.get("chave")
    nro_coleta = payload.get("nro_coleta") or payload.get("coleta")

    if not cnpj or not (nro_nf or pedido or chave_nfe or nro_coleta):
        return jsonify({
            "servico": "MP CARGAS - API Rastreamento por Pagador",
            "metodos_aceitos": ["GET", "POST"],
            "parametros": {
                "cnpj": "CNPJ do pagador da carga (obrigatório)",
                "senha": "Senha de acesso disponibilizada pela transportadora (opcional)",
                "sigla_emp": "Sigla da empresa para filtrar (opcional)",
                "identificador": "Envie exatamente UM entre: nro_nf, pedido, chave_nfe ou nro_coleta"
            },
            "exemplo": "/api/v1/tracking/pagador?cnpj=02012862003770&pedido=12345678"
        }), 200

    try:
        resultado = consultar_pagador(
            cnpj=cnpj,
            nro_nf=nro_nf,
            pedido=pedido,
            chave_nfe=chave_nfe,
            nro_coleta=nro_coleta,
            senha=senha,
            sigla_emp=sigla_emp
        )
        dados, erro = preparar_resultado(
            resultado,
            cnpj=cnpj,
            nro_nf=nro_nf,
            chave_nfe=chave_nfe,
            pedido=pedido,
            nro_coleta=nro_coleta,
            tipo_consulta="Pagador"
        )
        if erro:
            return jsonify({"success": False, "message": erro}), 404
        return jsonify({"success": True, "dados": dados}), 200
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "message": f"Erro de comunicação com a transportadora: {str(e)}"}), 502
    except ValueError as ve:
        return jsonify({"success": False, "message": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro interno: {str(e)}"}), 500


@app.route("/api/v1/tracking/pf", methods=["GET", "POST"])
def api_tracking_pf():
    """
    SSW Tracking WebAPI - Pessoa Física (https://ssw.inf.br/api/trackingpf).
    Parâmetros: cpf (obrigatório), nro_nf (opcional), pedido (opcional), chave_nfe (opcional).
    Credenciais (dominio, usuario, senha) são carregadas do ambiente ou passadas no payload.
    """
    payload = extrair_parametros()
    cpf = limpar_numeros(payload.get("cpf", ""))

    nro_nf = payload.get("nro_nf") or payload.get("nf")
    pedido = payload.get("pedido")
    chave_nfe = payload.get("chave_nfe") or payload.get("chave")

    dominio = payload.get("dominio")
    usuario = payload.get("usuario")
    senha = payload.get("senha")

    if not cpf:
        return jsonify({
            "servico": "MP CARGAS - API Rastreamento por Pessoa Física (CPF)",
            "metodos_aceitos": ["GET", "POST"],
            "parametros": {
                "cpf": "CPF do destinatário da carga (11 dígitos, obrigatório)",
                "nro_nf": "Número da NF (opcional)",
                "pedido": "Número do pedido (opcional)",
                "chave_nfe": "Chave da NF-e (opcional)"
            },
            "exemplo": "/api/v1/tracking/pf?cpf=02602602655&nro_nf=130516"
        }), 200

    try:
        resultado = consultar_pf(
            cpf=cpf,
            nro_nf=nro_nf,
            pedido=pedido,
            chave_nfe=chave_nfe,
            dominio=dominio,
            usuario=usuario,
            senha=senha
        )
        dados, erro = preparar_resultado(
            resultado,
            cpf=cpf,
            nro_nf=nro_nf,
            chave_nfe=chave_nfe,
            pedido=pedido,
            tipo_consulta="Pessoa Física"
        )
        if erro:
            return jsonify({"success": False, "message": erro}), 404
        return jsonify({"success": True, "dados": dados}), 200
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "message": f"Erro de comunicação com a transportadora: {str(e)}"}), 502
    except ValueError as ve:
        return jsonify({"success": False, "message": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro interno: {str(e)}"}), 500


@app.route("/api/v1/tracking/remetente", methods=["GET", "POST"])
def api_tracking_remetente():
    """
    SSW Tracking Remetente WebAPI (https://ssw.inf.br/api/tracking).
    Parâmetros: cnpj (obrigatório), nro_nf / pedido / chave_nfe, senha (opcional).
    """
    payload = extrair_parametros()
    cnpj = limpar_numeros(payload.get("cnpj", ""))
    nro_nf = payload.get("nro_nf") or payload.get("nf")
    pedido = payload.get("pedido")
    chave_nfe = payload.get("chave_nfe") or payload.get("chave")
    senha = payload.get("senha")

    if not cnpj or not (nro_nf or pedido or chave_nfe):
        return jsonify({
            "servico": "MP CARGAS - API Rastreamento por Remetente",
            "metodos_aceitos": ["GET", "POST"],
            "instrucoes": "Informe o CNPJ e o número da NF (ou Pedido/Chave).",
            "exemplo": "/api/v1/tracking/remetente?cnpj=12345678000190&nro_nf=61750"
        }), 200

    try:
        resultado = consultar_remetente(cnpj, nro_nf=nro_nf, pedido=pedido, chave_nfe=chave_nfe, senha=senha)
        dados, erro = preparar_resultado(resultado, cnpj=cnpj, nro_nf=nro_nf, chave_nfe=chave_nfe, pedido=pedido, tipo_consulta="Remetente")
        if erro:
            return jsonify({"success": False, "message": erro}), 404
        return jsonify({"success": True, "dados": dados}), 200
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "message": f"Erro de comunicação com a transportadora: {str(e)}"}), 502
    except ValueError as ve:
        return jsonify({"success": False, "message": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro interno: {str(e)}"}), 500


@app.route("/api/v1/tracking/danfe", methods=["GET", "POST"])
def api_tracking_danfe():
    """
    Endpoint para consulta por Chave de NF-e (44 dígitos).
    Suporta POST com JSON ou GET com query param ?chave_nfe=...
    """
    payload = extrair_parametros()
    chave_nfe = limpar_numeros(payload.get("chave_nfe", "") or payload.get("chave", ""))

    if not chave_nfe:
        return jsonify({
            "servico": "MP CARGAS - API Rastreamento por Chave DANFE",
            "metodos_aceitos": ["GET", "POST"],
            "instrucoes": "Forneça a chave_nfe via JSON no corpo da requisição (POST) ou na URL (GET).",
            "exemplo_uso": "/api/v1/tracking/danfe?chave_nfe=35230912345678000199550010000617501234567890"
        }), 200

    if len(chave_nfe) != 44:
        return jsonify({
            "success": False,
            "message": "Chave de acesso inválida. Deve conter exatamente 44 dígitos numéricos."
        }), 400

    try:
        resultado = consultar_chave(chave_nfe)
        dados, erro = preparar_resultado(resultado, chave_nfe=chave_nfe, tipo_consulta="Chave DANFE")
        if erro:
            return jsonify({"success": False, "message": erro}), 404
        return jsonify({"success": True, "dados": dados}), 200
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "message": f"Erro de comunicação com a transportadora: {str(e)}"}), 502
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro interno: {str(e)}"}), 500


@app.route("/api/v1/tracking/nf", methods=["GET", "POST"])
def api_tracking_nf():
    """
    Endpoint retrocompatível de consulta por CNPJ + NF.
    Utiliza busca inteligente (Destinatário -> Remetente -> Pagador) para máxima taxa de sucesso.
    """
    payload = extrair_parametros()
    cnpj = limpar_numeros(payload.get("cnpj", ""))
    nro_nf = limpar_numeros(payload.get("nro_nf", "") or payload.get("nf", ""))
    senha = payload.get("senha")

    if not cnpj or not nro_nf:
        return jsonify({
            "servico": "MP CARGAS - API Rastreamento por CNPJ + NF",
            "metodos_aceitos": ["GET", "POST"],
            "instrucoes": "Informe o CNPJ e o número da NF via JSON (POST) ou na URL (GET).",
            "exemplo_uso": "/api/v1/tracking/nf?cnpj=12345678000190&nro_nf=61750"
        }), 200

    try:
        dados, erro = consultar_inteligente(cnpj=cnpj, nro_nf=nro_nf, senha=senha, tipo="auto")
        if erro:
            return jsonify({"success": False, "message": erro}), 404
        return jsonify({"success": True, "dados": dados}), 200
    except requests.exceptions.RequestException as e:
        return jsonify({"success": False, "message": f"Erro de comunicação com a transportadora: {str(e)}"}), 502
    except Exception as e:
        return jsonify({"success": False, "message": f"Erro interno: {str(e)}"}), 500


@app.route("/api/v1/bot/consulta", methods=["GET", "POST"])
def api_bot_consulta():
    """
    Endpoint inteligente unificado feito sob medida para Bots (WhatsApp / Telegram).
    Suporta linguagem natural, CPF (Pessoa Física), CNPJ (Destinatário/Remetente/Pagador),
    número de NF, Pedido, Chave DANFE e número de Coleta.
    """
    payload = extrair_parametros()

    termo = payload.get("texto") or payload.get("mensagem") or payload.get("termo") or payload.get("q")
    chave = payload.get("chave") or payload.get("chave_nfe")
    cnpj = payload.get("cnpj")
    cpf = payload.get("cpf")
    nro_nf = payload.get("nro_nf") or payload.get("nf")
    pedido = payload.get("pedido")
    coleta = payload.get("coleta") or payload.get("nro_coleta")
    senha = payload.get("senha")
    tipo = payload.get("tipo")
    sigla_emp = payload.get("sigla_emp")

    if not termo and not chave and not ((cnpj or cpf) and (nro_nf or pedido or coleta)):
        return jsonify({
            "servico": "MP CARGAS - API para Bots de Chat (WhatsApp / Telegram)",
            "metodos_aceitos": ["GET", "POST"],
            "descricao": "Recebe o texto enviado pelo cliente e retorna a mensagem pré-formatada pronta para envio no chat.",
            "parametros_suportados": {
                "texto": "Texto livre enviado pelo cliente (ex: chave de 44 digitos, CNPJ/CPF e NF/Pedido)",
                "chave": "Chave de acesso com 44 digitos",
                "cnpj": "CNPJ do destinatário/remetente/pagador",
                "cpf": "CPF do destinatário (Pessoa Física)",
                "nro_nf": "Número da nota fiscal",
                "pedido": "Número do pedido",
                "coleta": "Número da coleta"
            },
            "exemplos_teste_navegador": [
                "/api/v1/bot/consulta?texto=35230912345678000199550010000617501234567890",
                "/api/v1/bot/consulta?texto=12345678000190+61750",
                "/api/v1/bot/consulta?texto=02602602655+130516"
            ]
        }), 200

    usuario = payload.get("usuario") or payload.get("sender") or request.remote_addr

    try:
        dados, erro = consultar_inteligente(
            termo=termo,
            chave=chave,
            cnpj=cnpj,
            cpf=cpf,
            nro_nf=nro_nf,
            pedido=pedido,
            nro_coleta=coleta,
            senha=senha,
            sigla_emp=sigla_emp,
            tipo=tipo,
            usuario=usuario,
        )

        if erro:
            if erro == "SAUDACAO":
                return jsonify({
                    "success": True,
                    "tipo": "saudacao",
                    "mensagem_bot": formatar_mensagem_saudacao()
                }), 200

            if erro.startswith("DUVIDA:"):
                msg_duvida = erro.split(":", 1)[1]
                return jsonify({
                    "success": True,
                    "tipo": "duvida",
                    "mensagem_bot": msg_duvida
                }), 200

            if erro.startswith("FALTA_DOC:"):
                id_ref = erro.split(":", 1)[1]
                return jsonify({
                    "success": True,
                    "tipo": "aguardando_doc",
                    "identificador": id_ref,
                    "mensagem_bot": formatar_mensagem_falta_cnpj(id_ref)
                }), 200

            if erro.startswith("FALTA_ID:"):
                partes = erro.split(":")
                tipo_doc = partes[1] if len(partes) > 2 else "CNPJ"
                doc_valor = partes[2] if len(partes) > 2 else partes[1]
                doc_fmt = formatar_documento(doc_valor)
                return jsonify({
                    "success": True,
                    "tipo": "aguardando_identificador",
                    "documento": doc_fmt,
                    "mensagem_bot": formatar_mensagem_falta_nf(doc_fmt, tipo_doc=tipo_doc)
                }), 200

            if erro.startswith("FALTA_CNPJ:"):
                nf_esperada = erro.split(":", 1)[1]
                return jsonify({
                    "success": True,
                    "tipo": "aguardando_cnpj",
                    "nf": nf_esperada,
                    "mensagem_bot": formatar_mensagem_falta_cnpj(nf_esperada)
                }), 200

            if erro.startswith("FALTA_NF:"):
                cnpj_esperado = erro.split(":", 1)[1]
                doc_fmt = formatar_documento(cnpj_esperado)
                return jsonify({
                    "success": True,
                    "tipo": "aguardando_nf",
                    "cnpj": doc_fmt,
                    "mensagem_bot": formatar_mensagem_falta_nf(doc_fmt, tipo_doc="CNPJ")
                }), 200

            return jsonify({
                "success": False,
                "message": erro,
                "mensagem_bot": formatar_mensagem_erro(erro)
            }), 200

        if not dados:
            msg_erro = "Carga não localizada na transportadora com os dados informados."
            return jsonify({
                "success": False,
                "message": msg_erro,
                "mensagem_bot": formatar_mensagem_erro(msg_erro)
            }), 200

        mensagem_bot = formatar_mensagem_whatsapp(dados)

        return jsonify({
            "success": True,
            "mensagem_bot": mensagem_bot,
            "dados": dados
        }), 200

    except requests.exceptions.Timeout:
        msg = "O sistema da transportadora demorou para responder. Tente novamente em instantes."
        return jsonify({"success": False, "message": msg, "mensagem_bot": formatar_mensagem_erro(msg)}), 200
    except requests.exceptions.ConnectionError:
        msg = "Não foi possível conectar aos servidores de rastreamento no momento."
        return jsonify({"success": False, "message": msg, "mensagem_bot": formatar_mensagem_erro(msg)}), 200
    except requests.exceptions.HTTPError as he:
        try:
            msg = he.response.json().get("message", "A transportadora informou um erro na consulta.")
        except Exception:
            msg = "A transportadora informou um erro na consulta."
        return jsonify({"success": False, "message": msg, "mensagem_bot": formatar_mensagem_erro(msg)}), 200
    except Exception as e:
        msg = f"Erro ao processar consulta: {str(e)}"
        return jsonify({"success": False, "message": msg, "mensagem_bot": formatar_mensagem_erro(msg)}), 200


# ==============================================================================
# INICIALIZAÇÃO DO SERVIDOR
# ==============================================================================

if __name__ == "__main__":
    porta = int(os.environ.get("PORT", 5000))
    print()
    print("=" * 65)
    print("                    MP CARGAS")
    print("      SISTEMA DE RASTREAMENTO & API PARA BOTS (v2.1)")
    print("=" * 65)
    print()
    print("Endpoints disponíveis:")
    print(f"  * Web UI:                 http://localhost:{porta}/")
    print(f"  * Healthcheck:            http://localhost:{porta}/api/v1/health")
    print(f"  * API Bot WhatsApp:       http://localhost:{porta}/api/v1/bot/consulta (POST)")
    print(f"  * API Destinatário:       http://localhost:{porta}/api/v1/tracking/destinatario (POST)")
    print(f"  * API Pagador:            http://localhost:{porta}/api/v1/tracking/pagador (POST)")
    print(f"  * API Pessoa Física (PF): http://localhost:{porta}/api/v1/tracking/pf (POST)")
    print(f"  * API Remetente:          http://localhost:{porta}/api/v1/tracking/remetente (POST)")
    print(f"  * API Chave DANFE:        http://localhost:{porta}/api/v1/tracking/danfe (POST)")
    print(f"  * API Legada CNPJ+NF:     http://localhost:{porta}/api/v1/tracking/nf (POST)")
    print()
    print("Pressione CTRL+C para encerrar.")
    print()

    app.run(
        host="0.0.0.0",
        port=porta,
        debug=False
    )