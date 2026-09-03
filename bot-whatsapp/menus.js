/**
 * menus.js — Menus textuais otimizados para números normais do WhatsApp
 */

function criarMenuPrincipal() {
    return {
        text: `👋 *Bem-vindo ao Rastreamento MP CARGAS!* 📦

Responda com o *NÚMERO* da opção que deseja:

*1️⃣* ➔ CNPJ + Nota Fiscal
*2️⃣* ➔ CPF + Nota Fiscal (Pessoa Física)
*3️⃣* ➔ Chave DANFE (44 dígitos)
*4️⃣* ➔ CNPJ + Número do Pedido
*5️⃣* ➔ CNPJ + Número de Coleta

_Exemplo: Digite apenas *1* para a primeira opção._`
    };
}

function criarBotoesAposResultado() {
    return {
        text: `✅ Consulta finalizada!
        
Digite *0* para voltar ao Menu Principal ou mande um novo número de documento para rastrear novamente.`
    };
}

function criarBotoesAposErro() {
    return {
        text: `❌ Não localizamos a carga.
        
Digite *0* para voltar ao Menu Principal ou digite as informações novamente.`
    };
}

function criarBotaoCancelar(textoExibicao) {
    return {
        text: `${textoExibicao}\n\n_(Para cancelar e voltar, digite *0*)_`
    };
}

module.exports = {
    criarMenuPrincipal,
    criarBotoesAposResultado,
    criarBotoesAposErro,
    criarBotaoCancelar
};
