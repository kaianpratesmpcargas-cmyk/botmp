#!/bin/bash
set -e

PORT="${PORT:-5000}"

echo "============================================================"
echo " Iniciando MP CARGAS Bot"
echo " Porta Flask: $PORT"
echo "============================================================"

# Inicia o Flask via Gunicorn (servidor de produção, sem o aviso de dev)
echo "[Flask] Iniciando Gunicorn na porta $PORT..."
gunicorn app:app \
    --bind "0.0.0.0:${PORT}" \
    --workers 1 \
    --timeout 120 \
    --log-level info &

FLASK_PID=$!
echo "[Flask] PID: $FLASK_PID"

# Aguarda o Flask estar pronto antes de iniciar o Node
echo "[Bot] Aguardando Flask iniciar..."
sleep 4

# Inicia o bot Node.js/Baileys com reinício automático em caso de crash
echo "[Bot] Iniciando Baileys (index.js)..."
cd bot-whatsapp

while true; do
    node index.js
    EXIT_CODE=$?
    echo "[Bot] Node.js encerrou com código $EXIT_CODE. Reiniciando em 5s..."
    sleep 5
done &

NODE_LOOP_PID=$!
echo "[Bot] Loop de reinício PID: $NODE_LOOP_PID"

echo "[Sistema] Ambos os processos iniciados. Monitorando Flask (PID $FLASK_PID)..."

# Aguarda o Flask — se ele morrer, derruba tudo (o Render reiniciará o container)
wait $FLASK_PID
echo "[ERRO CRÍTICO] Flask encerrou inesperadamente. Encerrando container."
kill $NODE_LOOP_PID 2>/dev/null
exit 1
