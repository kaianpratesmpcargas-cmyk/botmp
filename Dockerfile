FROM python:3.11-slim

# Impede a criação de .pyc e força os logs a aparecerem imediatamente
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instala pacotes do sistema e o Node.js v20
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Configura diretório de trabalho
WORKDIR /app

# Instala dependências do Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instala dependências do Node.js
# Copiamos apenas os package.json primeiro para usar o cache do Docker
COPY bot-whatsapp/package.json bot-whatsapp/package-lock.json* ./bot-whatsapp/
RUN cd bot-whatsapp && npm install --production

# Copia todo o restante do código para o container
COPY . .

# Garante que o script bash tem permissão de execução
RUN chmod +x start.sh

# Porta que o Render vai atribuir via variável PORT
EXPOSE 5000

# Inicia o gerenciador de processos
CMD ["./start.sh"]
