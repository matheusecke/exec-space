#!/bin/bash

echo "=========================================="
echo "Configurando VM de Banco de Dados"
echo "=========================================="

# Atualizar sistema
apt-get update
apt-get upgrade -y

# Instalar Docker e Docker Compose
echo "Instalando Docker..."
apt-get install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io

# Instalar Docker Compose
echo "Instalando Docker Compose..."
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Adicionar usuário vagrant ao grupo docker
usermod -aG docker vagrant

# Iniciar Docker
systemctl start docker
systemctl enable docker

# Ir para o diretório do banco de dados
cd /home/vagrant/database

# Iniciar MySQL com Docker Compose
echo "Iniciando MySQL com Docker Compose..."
docker-compose up -d

# Aguardar MySQL inicializar
echo "Aguardando MySQL inicializar..."
sleep 20

# Verificar status
if docker-compose ps | grep -q "Up"; then
    echo "=========================================="
    echo "MySQL configurado e em execução!"
    echo "Banco de dados: exec_space"
    echo "Usuário: execspace_user"
    echo "IP: 192.168.56.10:3306"
    echo "=========================================="
else
    echo "=========================================="
    echo "AVISO: MySQL não iniciou corretamente"
    echo "=========================================="
fi

