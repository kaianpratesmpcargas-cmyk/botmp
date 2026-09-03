const {
    default: makeWASocket,
    useMultiFileAuthState,
    DisconnectReason
} = require('@whiskeysockets/baileys');
const pino = require('pino');
const qrcode = require('qrcode-terminal');
const axios = require('axios');
const fs = require('fs');

// URL da nossa API Flask que já está rodando no mesmo container
const portaAPI = process.env.PORT || 5000;
const API_PYTHON_URL = `http://127.0.0.1:${portaAPI}/api/v1/bot/consulta`;

async function iniciarBot() {
    console.log("\nIniciando sistema de conexão WhatsApp (Baileys) [Modo Normal]...");

    // Salva a sessão na pasta 'auth_info' para persistir e não precisar escanear toda vez
    const { state, saveCreds } = await useMultiFileAuthState('./auth_info');

    const sock = makeWASocket({
        auth: state,
        logger: pino({ level: 'silent' }), // Oculta logs internos para manter o terminal limpo
        printQRInTerminal: false
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            console.log("\n============================================================");
            console.log("   ESCANEIE O QR CODE ABAIXO COM O SEU WHATSAPP:");
            console.log("============================================================\n");
            qrcode.generate(qr, { small: true });
        }

        if (connection === 'close') {
            const statusCode = lastDisconnect?.error?.output?.statusCode;
            const foiDesconectado = statusCode === DisconnectReason.loggedOut || statusCode === 401;

            if (foiDesconectado) {
                console.log("\n[AVISO] A sessão anterior foi desconectada pelo WhatsApp (Status: 401).");
                try {
                    fs.rmSync('./auth_info', { recursive: true, force: true });
                } catch (err) {}
                setTimeout(() => iniciarBot(), 2000);
            } else {
                console.log(`Conexão fechada. Reconectando em 3s... (Status: ${statusCode})`);
                setTimeout(() => iniciarBot(), 3000);
            }
        } else if (connection === 'open') {
            console.log("\n============================================================");
            console.log("   [OK] BOT DO WHATSAPP CONECTADO COM SUCESSO!");
            console.log("============================================================\n");
        }
    });


    sock.ev.on('messages.upsert', async ({ messages, type }) => {
        if (type !== 'notify') return;

        for (const msg of messages) {
            if (msg.key.fromMe) continue;

            const remetente = msg.key.remoteJid;
            if (!remetente || remetente.includes('@broadcast') || remetente.includes('@newsletter')) {
                continue;
            }

            const texto = msg.message?.conversation ||
                          msg.message?.extendedTextMessage?.text ||
                          msg.message?.imageMessage?.caption ||
                          msg.message?.videoMessage?.caption || '';

            const textoLimpo = texto.trim();
            if (!textoLimpo) continue;

            const agora = new Date().toLocaleTimeString('pt-BR');
            console.log(`[${agora}] [Mensagem]: ${textoLimpo}`);

            try {
                await sock.readMessages([msg.key]);
                await sock.sendPresenceUpdate('composing', remetente);

                const resposta = await axios.post(API_PYTHON_URL, {
                    texto: textoLimpo,
                    usuario: remetente
                }, { timeout: 35000 });

                const mensagemBot = resposta.data?.mensagem_bot || "Não foi possível obter o rastreio da carga.";

                await new Promise(resolve => setTimeout(resolve, 800));
                await sock.sendPresenceUpdate('paused', remetente);

                await sock.sendMessage(remetente, { text: mensagemBot }, { quoted: msg });

            } catch (err) {
                console.error(`[Erro ao consultar API Python]:`, err.message);
                try {
                    await sock.sendPresenceUpdate('paused', remetente);
                    await sock.sendMessage(remetente, {
                        text: "⚠️ Ocorreu uma instabilidade temporária na consulta da carga. Por favor, tente novamente em alguns segundos."
                    }, { quoted: msg });
                } catch (e) {}
            }
        }
    });
}

iniciarBot().catch(err => console.error("Erro fatal ao iniciar bot:", err));
