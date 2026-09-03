// Máscara dinâmica para CPF ou CNPJ
function mascaraDocumento(valor, forcarCPF) {
    var apenasDigitos = valor.replace(/\D/g, "");

    // Se for Pessoa Física ou até 11 dígitos
    if (forcarCPF || apenasDigitos.length <= 11) {
        if (apenasDigitos.length <= 3) return apenasDigitos;
        if (apenasDigitos.length <= 6) return apenasDigitos.replace(/^(\d{3})(\d+)/, "$1.$2");
        if (apenasDigitos.length <= 9) return apenasDigitos.replace(/^(\d{3})(\d{3})(\d+)/, "$1.$2.$3");
        return apenasDigitos.slice(0, 11).replace(/^(\d{3})(\d{3})(\d{3})(\d{2})/, "$1.$2.$3-$4");
    }

    // CNPJ (14 dígitos)
    if (apenasDigitos.length <= 2) return apenasDigitos;
    if (apenasDigitos.length <= 5) return apenasDigitos.replace(/^(\d{2})(\d+)/, "$1.$2");
    if (apenasDigitos.length <= 8) return apenasDigitos.replace(/^(\d{2})(\d{3})(\d+)/, "$1.$2.$3");
    if (apenasDigitos.length <= 12) return apenasDigitos.replace(/^(\d{2})(\d{3})(\d{3})(\d+)/, "$1.$2.$3/$4");
    return apenasDigitos.slice(0, 14).replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, "$1.$2.$3/$4-$5");
}

document.addEventListener("DOMContentLoaded", function () {
    var inputDoc = document.getElementById("documento") || document.getElementById("cnpj");
    var selectTipo = document.getElementById("tipo_consulta");
    var selectCriterio = document.getElementById("criterio");
    var labelDoc = document.getElementById("label-documento");
    var labelValor = document.getElementById("label-valor-busca");
    var inputValor = document.getElementById("valor_busca") || document.getElementById("nro_nf");
    var formConsulta = document.getElementById("form-consulta");
    var btnSubmit = document.getElementById("btn-submit");
    var btnText = document.getElementById("btn-text");

    function atualizarTipo() {
        if (!selectTipo || !inputDoc) return;
        var tipo = selectTipo.value;
        if (tipo === "pf") {
            if (labelDoc) labelDoc.textContent = "CPF do Destinatário";
            inputDoc.placeholder = "000.000.000-00";
            inputDoc.maxLength = 14;
        } else if (tipo === "destinatario") {
            if (labelDoc) labelDoc.textContent = "CNPJ do Destinatário";
            inputDoc.placeholder = "00.000.000/0000-00";
            inputDoc.maxLength = 18;
        } else if (tipo === "remetente") {
            if (labelDoc) labelDoc.textContent = "CNPJ do Remetente";
            inputDoc.placeholder = "00.000.000/0000-00";
            inputDoc.maxLength = 18;
        } else if (tipo === "pagador") {
            if (labelDoc) labelDoc.textContent = "CNPJ do Pagador";
            inputDoc.placeholder = "00.000.000/0000-00";
            inputDoc.maxLength = 18;
        } else {
            if (labelDoc) labelDoc.textContent = "CNPJ ou CPF";
            inputDoc.placeholder = "00.000.000/0000-00 ou 000.000.000-00";
            inputDoc.maxLength = 18;
        }
        var forcarCPF = tipo === "pf";
        inputDoc.value = mascaraDocumento(inputDoc.value, forcarCPF);
    }

    function atualizarCriterio() {
        if (!selectCriterio || !inputValor) return;
        var crit = selectCriterio.value;
        if (crit === "nro_nf") {
            if (labelValor) labelValor.textContent = "Número da Nota Fiscal (NF)";
            inputValor.placeholder = "Ex: 4224761";
        } else if (crit === "pedido") {
            if (labelValor) labelValor.textContent = "Número do Pedido";
            inputValor.placeholder = "Ex: A2341232B";
        } else if (crit === "chave_nfe") {
            if (labelValor) labelValor.textContent = "Chave da NF-e (44 dígitos)";
            inputValor.placeholder = "44 dígitos numéricos";
        } else if (crit === "nro_coleta") {
            if (labelValor) labelValor.textContent = "Número da Coleta";
            inputValor.placeholder = "Ex: 65981";
        }
    }

    if (inputDoc) {
        inputDoc.addEventListener("input", function (e) {
            var forcarCPF = selectTipo && selectTipo.value === "pf";
            e.target.value = mascaraDocumento(e.target.value, forcarCPF);
        });

        if (inputDoc.value) {
            var forcarCPF = selectTipo && selectTipo.value === "pf";
            inputDoc.value = mascaraDocumento(inputDoc.value, forcarCPF);
        }
    }

    if (selectTipo) {
        selectTipo.addEventListener("change", atualizarTipo);
        atualizarTipo();
    }

    if (selectCriterio) {
        selectCriterio.addEventListener("change", atualizarCriterio);
        atualizarCriterio();
    }

    if (formConsulta && btnSubmit) {
        formConsulta.addEventListener("submit", function () {
            btnSubmit.disabled = true;
            if (btnText) {
                btnText.textContent = "⏳ Buscando carga na transportadora...";
            }
        });
    }
});

