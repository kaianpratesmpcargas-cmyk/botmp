"""
Base de conhecimento oficial de Praças e Prazos da MP AGENTE DE CARGAS LTDA
Endereço: Estrada de Pirajá, 334 - Pirajá
Contatos:
- Coleta: (71) 98314-9876
- Telefones: (71) 3246-3838 / (71) 99227-2629
"""

import re
import unicodedata
from datetime import datetime, timedelta

# Tabela completa de praças e prazos em dias úteis
PRACAS_PRAZOS = {
    # 2 Dias Úteis
    "barreiras": 2,
    "feira de santana": 2,
    "itaberaba": 2,
    "seabra": 2,

    # 3 Dias Úteis
    "ibotirama": 3,
    "luis eduardo magalhaes": 3,
    "luís eduardo magalhães": 3,
    "lem": 3,

    # 5 Dias Úteis
    "baianopolis": 5,
    "baianópolis": 5,
    "barrocas": 5,
    "biritinga": 5,
    "brumado": 5,
    "candeal": 5,
    "conceicao do coite": 5,
    "conceição do coité": 5,
    "euclides da cunha": 5,
    "guanambi": 5,
    "ichu": 5,
    "lamarao": 5,
    "lamarão": 5,
    "paratinga": 5,
    "sao desiderio": 5,
    "são desidério": 5,
    "senhor do bonfim": 5,
    "serrinha": 5,
    "teofilandia": 5,
    "teofilândia": 5,

    # 7 Dias Úteis
    "andorinha": 7,
    "antonio goncalves": 7,
    "antônio gonçalves": 7,
    "aracas": 7,
    "araçás": 7,
    "aramari": 7,
    "barra": 7,
    "bom jesus da lapa": 7,
    "cacule": 7,
    "caculé": 7,
    "campo formoso": 7,
    "cansancao": 7,
    "cansanção": 7,
    "central": 7,
    "entre rios": 7,
    "filadelfia": 7,
    "filadélfia": 7,
    "iacu": 7,
    "iaçu": 7,
    "ibitiara": 7,
    "inhambupe": 7,
    "iraquara": 7,
    "irece": 7,
    "irecê": 7,
    "itanagra": 7,
    "jaguarari": 7,
    "jussara": 7,
    "lencois": 7,
    "lençóis": 7,
    "macajuba": 7,
    "monte santo": 7,
    "ouricangas": 7,
    "ouriçangas": 7,
    "palmeiras": 7,
    "pedrao": 7,
    "pedrão": 7,
    "pindobacu": 7,
    "pindobaçu": 7,
    "ponto novo": 7,
    "presidente dutra": 7,
    "quijingue": 7,
    "ribeira do pombal": 7,
    "rio de contas": 7,
    "ruy barbosa": 7,
    "santa maria da vitoria": 7,
    "santa maria da vitória": 7,
    "sao felix do coribe": 7,
    "são félix do coribe": 7,
    "sao gabriel": 7,
    "são gabriel": 7,
    "serra do ramalho": 7,
    "sitio do mato": 7,
    "sítio do mato": 7,
    "tucano": 7,
    "uibai": 7,
    "uibaí": 7,
    "urandi": 7,

    # 10 Dias Úteis
    "angical": 10,
    "araci": 10,
    "banzae": 10,
    "banzaê": 10,
    "boquira": 10,
    "botupora": 10,
    "botuporã": 10,
    "brejolandia": 10,
    "brejolândia": 10,
    "buritirama": 10,
    "caetite": 10,
    "caetité": 10,
    "canapolis": 10,
    "canápolis": 10,
    "candiba": 10,
    "carinhanha": 10,
    "catolandia": 10,
    "catolândia": 10,
    "cotegipe": 10,
    "cristopolis": 10,
    "cristópolis": 10,
    "dom basilio": 10,
    "dom basílio": 10,
    "formosa do rio preto": 10,
    "ibiassuce": 10,
    "ibiassucê": 10,
    "igapora": 10,
    "igaporã": 10,
    "iuiu": 10,
    "lagoa real": 10,
    "livramento de nossa senhora": 10,
    "livramento de nosssa senhora": 10,
    "macaubas": 10,
    "macaúbas": 10,
    "maetinga": 10,
    "malhada de pedras": 10,
    "mansidao": 10,
    "mansidão": 10,
    "muquem do sao francisco": 10,
    "muquém do são francisco": 10,
    "oliveira dos brejinhos": 10,
    "palmas de monte alto": 10,
    "paramirim": 10,
    "riachao das neves": 10,
    "riachão das neves": 10,
    "rio do antonio": 10,
    "rio do antônio": 10,
    "rio do pires": 10,
    "santa rita de cassia": 10,
    "santa rita de cássia": 10,
    "santana": 10,
    "serra dourada": 10,
    "tabocas do brejo velho": 10,
    "tanque novo": 10,
    "wanderley": 10,
}

DADOS_EMPRESA = {
    "nome": "MP AGENTE DE CARGAS LTDA",
    "endereco": "Estrada de Pirajá, 334 - Pirajá, Salvador - BA",
    "telefone_coleta": "(71) 98314-9876",
    "telefones_gerais": "(71) 3246-3838 / (71) 99227-2629",
    "horario": "Segunda a Sexta, das 08h às 18h"
}


def normalizar_texto(texto):
    """Remove acentos e caracteres especiais para busca tolerante."""
    if not texto:
        return ""
    texto_norm = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in texto_norm if not unicodedata.combining(c))
    return sem_acento.lower().strip()


def buscar_cidade_no_texto(texto):
    """Procura se alguma cidade da tabela foi mencionada na mensagem."""
    texto_norm = normalizar_texto(texto)

    # Ordena por tamanho decrescente para pegar 'Santa Maria da Vitória' antes de 'Santa Maria'
    cidades_ordenadas = sorted(PRACAS_PRAZOS.keys(), key=lambda c: len(c), reverse=True)

    for cidade in cidades_ordenadas:
        cidade_norm = normalizar_texto(cidade)
        # Busca como palavra ou expressão completa
        padrao = r"\b" + re.escape(cidade_norm) + r"\b"
        if re.search(padrao, texto_norm):
            return cidade.title(), PRACAS_PRAZOS[cidade]

    return None, None


def proximo_dia_util(data):
    """Retorna o próximo dia útil a partir de uma data dada."""
    dia = data + timedelta(days=1)
    while dia.weekday() >= 5:  # 5 = Sábado, 6 = Domingo
        dia += timedelta(days=1)
    return dia


def calcular_previsao_dias_uteis(data_inicio, dias_uteis):
    """
    Calcula a data de entrega pulando fins de semana.
    Regra da transportadora: A contagem inicia no próximo dia útil após a coleta/emissão (D+1 útil).
    Se foi coletado na sexta-feira, o primeiro dia útil de contagem é a segunda-feira!
    """
    dia_atual = proximo_dia_util(data_inicio)
    dias_contados = 1

    while dias_contados < dias_uteis:
        dia_atual += timedelta(days=1)
        # Se for dia de semana (segunda=0 a sexta=4)
        if dia_atual.weekday() < 5:
            dias_contados += 1

    return dia_atual


DIAS_SEMANA_PT = [
    "Segunda-feira",
    "Terça-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
    "Sábado",
    "Domingo"
]


def formatar_resposta_praca(cidade, dias_uteis, data_base=None):
    """Gera uma resposta completa, amigável e explicativa sobre o prazo."""
    linhas = [
        f"📍 *Praça de Atendimento: {cidade}*",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"⏱️ *Prazo de entrega:* *{dias_uteis} dias úteis*.",
        "",
        "ℹ️ *Como funciona a contagem em dias úteis:*",
        "• Não são contados sábados, domingos e feriados.",
        "• A contagem inicia no *próximo dia útil* após a coleta/emissão.",
        "_(Por exemplo: se a carga foi coletada em uma sexta-feira, o primeiro dia útil contado é a segunda-feira)._"
    ]

    if data_base:
        previsao = calcular_previsao_dias_uteis(data_base, dias_uteis)
        nome_dia = DIAS_SEMANA_PT[previsao.weekday()]
        linhas.extend([
            "",
            f"📅 *Previsão estimada para seu envio:*",
            f"👉 *{previsao.strftime('%d/%m/%Y')}* ({nome_dia})"
        ])

    linhas.extend([
        "━━━━━━━━━━━━━━━━━━━━━━",
        "📦 *MP AGENTE DE CARGAS LTDA*",
        f"📞 *Dúvidas ou Coletas:* {DADOS_EMPRESA['telefone_coleta']} / {DADOS_EMPRESA['telefones_gerais']}"
    ])

    return "\n".join(linhas)


def responder_duvida_geral(texto):
    """
    Analisa se o texto é uma dúvida sobre a empresa, endereço, coletas ou funcionamento de dias úteis.
    """
    t_norm = normalizar_texto(texto)

    # 1. Pergunta sobre cidade / praça específica
    cidade, prazo = buscar_cidade_no_texto(texto)
    if cidade:
        return formatar_resposta_praca(cidade, prazo)

    # 2. Pergunta sobre endereço ou localização
    if any(p in t_norm for p in ["onde fica", "endereco", "endereço", "localizacao", "localizacao", "onde voces estao", "filial", "piraja"]):
        return (
            "🏢 *Endereço da MP CARGAS:*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 {DADOS_EMPRESA['endereco']}\n"
            f"⏰ Horário: {DADOS_EMPRESA['horario']}\n"
            f"📞 Telefones: {DADOS_EMPRESA['telefones_gerais']}\n"
            f"🚛 Coleta: {DADOS_EMPRESA['telefone_coleta']}\n"
            "━━━━━━━━━━━━━━━━━━━━━━"
        )

    # 3. Pergunta sobre contato / telefone
    if any(p in t_norm for p in ["telefone", "contato", "whatsapp", "falar com atendente", "numero"]):
        return (
            "📞 *Contatos da MP CARGAS:*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🚛 *Setor de Coletas:* {DADOS_EMPRESA['telefone_coleta']}\n"
            f"☎️ *Atendimento Geral:* {DADOS_EMPRESA['telefones_gerais']}\n"
            f"📍 *Endereço:* {DADOS_EMPRESA['endereco']}\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Como posso te ajudar com sua encomenda hoje?"
        )

    # 4. Dúvida sobre contagem de dias úteis ou regras
    if any(p in t_norm for p in ["dias uteis", "dias úteis", "como conta", "conta fim de semana", "sabado", "domingo", "sexta"]):
        return (
            "⏱️ *Como funciona o prazo em Dias Úteis da MP CARGAS:*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "• *Sábados, domingos e feriados NÃO são contados.*\n"
            "• O prazo começa a ser contado a partir do **próximo dia útil** após o dia da coleta/emissão.\n\n"
            "💡 *Exemplo Prático:*\n"
            "Se sua carga tem prazo de **3 dias úteis** e foi coletada na **sexta-feira (dia 01)**:\n"
            "• Sábado e domingo: não contam.\n"
            "• 1º dia útil: Segunda-feira\n"
            "• 2º dia útil: Terça-feira\n"
            "• 3º dia útil: Quarta-feira (Previsão de entrega)\n\n"
            "📍 Quer saber o prazo para alguma cidade? Basta me mandar o nome da cidade (Ex: *'Qual o prazo para Serrinha?'*)!"
        )

    # 5. Agradecimentos
    if any(p in t_norm for p in ["obrigado", "obrigada", "valeu", "show", "perfeito", "agradeco"]):
        return (
            "😊 De nada! Estamos sempre à disposição para cuidar do transporte da sua carga.\n"
            "Se precisar de algo mais, é só me chamar por aqui! 🚚📦"
        )

    return None
