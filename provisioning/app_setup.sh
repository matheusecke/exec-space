#!/bin/bash

echo "=========================================="
echo "Configurando VM de Aplicação ExecSpace"
echo "=========================================="

# Atualizar sistema
apt-get update
apt-get upgrade -y

# Instalar dependências
apt-get install -y build-essential python3-pip python3-dev python3-venv util-linux libcap-dev

# Criar ambiente virtual Python em /opt
echo "Criando ambiente virtual Python..."
python3 -m venv /opt/execspace-venv
chown -R vagrant:vagrant /opt/execspace-venv

# Instalar dependências Python
echo "Instalando dependências Python..."
sudo -u vagrant /opt/execspace-venv/bin/pip install --upgrade pip
sudo -u vagrant /opt/execspace-venv/bin/pip install -r /home/vagrant/app/requirements.txt

# Aguardar o MySQL estar pronto
echo "Aguardando MySQL estar disponível..."
sleep 15

# Criar diretórios necessários para execspace
echo "Criando diretórios do sistema..."
mkdir -p /var/lib/execspace/environments
mkdir -p /var/log/execspace
chown -R root:root /var/lib/execspace
chown -R root:root /var/log/execspace
chmod 755 /var/lib/execspace
chmod 755 /var/log/execspace

# Criar serviço systemd
cat > /etc/systemd/system/execspace.service <<EOF
[Unit]
Description=ExecSpace FastAPI Application
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/vagrant/app
Environment="PATH=/opt/execspace-venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/opt/execspace-venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Iniciar serviço
systemctl daemon-reload
systemctl enable execspace
systemctl start execspace

# Aguardar inicialização
sleep 5

# Verificar status
if systemctl is-active --quiet execspace; then
    echo "=========================================="
    echo "ExecSpace configurado e em execução!"
    echo "Serviço execspace está ATIVO"
    echo ""
    echo "Acesse: http://192.168.56.11:8000"
    echo "Ou via host: http://localhost:8000"
    echo ""
    echo "=========================================="
else
    echo "=========================================="
    echo "AVISO: Serviço execspace não iniciou"
    echo "Execute: vagrant ssh app -c 'sudo systemctl status execspace'"
    echo "Logs: vagrant ssh app -c 'sudo journalctl -u execspace -n 50'"
    echo "=========================================="
fi

