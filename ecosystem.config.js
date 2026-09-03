module.exports = {
    apps: [
        {
            name: 'mp-cargas-api',
            script: 'python',
            args: 'app.py',
            cwd: 'C:/Users/Kaian/Desktop/ssw2',
            interpreter: 'none',
            autorestart: true,
            watch: false,
            max_restarts: 10,
            restart_delay: 3000,
            env: {
                PORT: 5000,
                PAGADOR_SENHA: 'SWORDFISH',
                DESTINATARIO_SENHA: 'SWORDFISH',
                PF_DOMINIO: 'TES',
                PF_USUARIO: 'sswlogin',
                PF_SENHA: 'SWORDFISH'
            }
        }
        // Remova o bot se ele não existir ou ajuste o caminho
        // {
        //   name: 'mp-cargas-bot',
        //   script: 'index.js',
        //   cwd: 'C:/Users/Kaian/Desktop/ssw2/bot-whatsapp',
        //   ...
        // }
    ]
};