#!/bin/bash

echo "=========================================="
echo "Configurando VM de Banco de Dados"
echo "=========================================="

apt-get update
apt-get upgrade -y

echo "Instalando Docker..."
apt-get install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io

echo "Instalando Docker Compose..."
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

usermod -aG docker vagrant

systemctl start docker
systemctl enable docker

cd /home/vagrant/database

echo "Iniciando MySQL com Docker Compose..."
docker-compose up -d

echo "Aguardando MySQL inicializar..."
sleep 20

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


