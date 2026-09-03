#!/bin/bash

echo "Iniciando a API Flask em background..."
# O app.py vai usar a porta definida na variável de ambiente PORT (ou 5000)
python app.py &

echo "Aguardando o Flask iniciar..."
sleep 2

echo "Iniciando o Bot WhatsApp (Baileys)..."
cd bot-whatsapp
node index.js &

# Aguarda qualquer um dos processos em background terminar
wait -n

# O script sai com o código de erro do processo que caiu, derrubando o container.
# Assim, o Render sabe que o serviço falhou e tentará reiniciar.
EXIT_CODE=$?
echo "Um dos processos essenciais encerrou com o código $EXIT_CODE. Finalizando o container."
exit $EXIT_CODE
