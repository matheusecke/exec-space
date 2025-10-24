# ExecSpace

Plataforma para execução de scripts em ambientes isolados usando namespaces e cgroups Linux diretamente.

## Arquitetura

- **Frontend**: HTML/CSS/JavaScript
- **Backend**: Python FastAPI
- **Banco de Dados**: MySQL 8.0
- **Isolamento**: Namespaces (PID, NET, MNT, UTS, IPC) e cgroups v2
- **Infraestrutura**: Vagrant + VirtualBox/VMware

## Estrutura do Projeto

```
execspace/
├── app/                      # Aplicação FastAPI
│   ├── environments.py       # Gerenciador de namespaces/cgroups
│   ├── main.py               # API REST
│   ├── models.py             # Modelos do banco de dados
│   ├── database.py           # Configuração do banco
│   ├── requirements.txt      # Dependências Python
│   └── static/               # Frontend
│       ├── index.html
│       ├── style.css
│       └── app.js
├── database/                 # Configuração do MySQL
│   ├── docker-compose.yml
│   └── init.sql
├── provisioning/             # Scripts de provisionamento
│   ├── app_setup.sh
│   └── db_setup.sh
└── Vagrantfile               # Configuração das VMs
```

## Requisitos

- Vagrant 2.3+
- VirtualBox ou VMware Desktop
- 8GB RAM disponível
- 20GB espaço em disco

## Como Executar

### 1. Subir as VMs

```bash
cd execspace

# Subir VM do banco de dados
vagrant up db

# Subir VM da aplicação
vagrant up app
```

### 2. Acessar a Aplicação

Abra o navegador em: **http://localhost:8000**

Ou via IP da VM: **http://192.168.56.11:8000**

## Funcionalidades

### Criar Ambiente de Execução

1. Acesse a interface web
2. Preencha os campos:
   - **Nome**: identificação do ambiente
   - **CPU**: limite em cores (ex: 0.5 = 50%)
   - **Memória**: limite em MB (64-4096)
   - **I/O**: peso de I/O (100-1000)
   - **Script**: código bash a executar
3. Clique em "Criar e Executar"

### Gerenciar Ambientes

- **Ver Logs**: visualizar saída do script em tempo real
- **Parar**: encerrar execução do ambiente
- **Remover**: deletar ambiente completamente
- **Atualizar**: atualizar lista de ambientes

### Status dos Ambientes

- **Executando**: processo em execução
- **Finalizado**: processo terminou normalmente
- **Erro**: processo terminou com erro

## Comandos Úteis

### Verificar Status das VMs

```bash
vagrant status
```

### Acessar VMs via SSH

```bash
# Acessar VM de aplicação
vagrant ssh app

# Acessar VM de banco de dados
vagrant ssh db
```

### Verificar Logs

```bash
# Logs da aplicação
vagrant ssh app -c 'sudo journalctl -u execspace -f'

# Logs do MySQL
vagrant ssh db -c 'cd database && sudo docker-compose logs -f'
```

### Reiniciar Serviço

```bash
vagrant ssh app -c 'sudo systemctl restart execspace'
```

### Parar e Destruir VMs

```bash
# Parar VMs
vagrant halt

# Destruir VMs (libera espaço)
vagrant destroy
```

## Detalhes Técnicos

### Isolamento com Namespaces

O ExecSpace usa `unshare` para criar os seguintes namespaces:

- **PID**: isolamento de processos
- **Mount**: isolamento de sistema de arquivos
- **UTS**: isolamento de hostname
- **IPC**: isolamento de comunicação entre processos
- **Network**: isolamento de rede (bridge)

### Limitação de Recursos com Cgroups

Os recursos são limitados via cgroups v2:

- **CPU**: `/sys/fs/cgroup/execspace/{env_id}/cpu.max`
- **Memória**: `/sys/fs/cgroup/execspace/{env_id}/memory.max`
- **I/O**: `/sys/fs/cgroup/execspace/{env_id}/io.weight`

### Estrutura de Arquivos

- **Scripts**: `/var/lib/execspace/environments/{env_id}.sh`
- **PIDs**: `/var/lib/execspace/environments/{env_id}.pid`
- **Logs**: `/var/log/execspace/{env_id}.log`
