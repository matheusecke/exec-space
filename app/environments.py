import os
import subprocess
import uuid
import signal
import time
import logging
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EnvironmentConfig:
    """Configuração de um ambiente de execução"""
    env_id: str
    script_content: str
    cpu_limit: float  # Em cores (ex: 0.5 = 50% de 1 core)
    memory_mb: int
    io_weight: int
    name: str


class EnvironmentManager:
    """Gerenciador de namespaces e cgroups"""
    
    def __init__(self):
        """Inicializar gerenciador"""
        self.cgroup_root = Path("/sys/fs/cgroup")
        self.environments_dir = Path("/var/lib/execspace/environments")
        self.logs_dir = Path("/var/log/execspace")
        
        # Criar diretórios necessários
        self.environments_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        
        # Verificar se tem permissões de root
        if os.geteuid() != 0:
            logger.warning("⚠️  Este gerenciador precisa de permissões de root!")
        
        # Inicializar cgroup base para execspace
        self._init_base_cgroup()
    
    def _init_base_cgroup(self):
        """Inicializar cgroup base para execspace"""
        try:
            execspace_cgroup = self.cgroup_root / "execspace"
            execspace_cgroup.mkdir(exist_ok=True)
            
            # Habilitar controladores necessários
            needed_controllers = ["cpu", "memory", "io"]
            
            # Nos cgroups raiz e execspace
            for path in [self.cgroup_root, execspace_cgroup]:
                subtree = path / "cgroup.subtree_control"
                if subtree.exists():
                    for controller in needed_controllers:
                        try:
                            subtree.write_text(f"+{controller}\n")
                        except Exception:
                            pass
            
            logger.info("Controladores habilitados no cgroup execspace")
                
        except Exception as e:
            logger.error(f"Erro ao inicializar cgroup base: {e}")
    
    def create_and_run_environment(self, config: EnvironmentConfig) -> Dict[str, str]:
        """Criar e executar ambiente isolado"""
        try:
            logger.info(f"Criando ambiente: {config.name}")
            
            cgroup_path = self._create_cgroup(config.env_id)
            self._configure_resource_limits(cgroup_path, config)
            
            # Salvar script e preparar comando
            script_path = self._save_script(config.env_id, config.script_content)
            command = self._build_unshare_command(script_path, config.env_id)
            
            log_file = self.logs_dir / f"{config.env_id}.log"
            with open(log_file, 'w') as log:
                process = subprocess.Popen(
                    command,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    preexec_fn=lambda: self._add_to_cgroup(config.env_id)
                )
            
            # Salvar PID
            (self.environments_dir / f"{config.env_id}.pid").write_text(str(process.pid))
            
            logger.info(f"✓ Ambiente criado: PID={process.pid}")
            
            return {
                "env_id": config.env_id,
                "pid": process.pid,
                "status": "running",
                "cgroup": str(cgroup_path),
                "log_file": str(log_file)
            }
            
        except Exception as e:
            logger.error(f"Erro ao criar ambiente: {e}")
            raise
    
    def _create_cgroup(self, env_id: str) -> Path:
        """Criar cgroup para o ambiente em /sys/fs/cgroup/execspace/{env_id}/"""
        cgroup_path = self.cgroup_root / "execspace" / env_id
        cgroup_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Cgroup criado: {cgroup_path}")
        return cgroup_path
    
    def _configure_resource_limits(self, cgroup_path: Path, config: EnvironmentConfig):
        """Configurar todos os limites de recursos de uma vez"""
        # CPU: converter cores para microsegundos (0.5 cores = 50000/100000)
        cpu_quota = int(config.cpu_limit * 100000)
        cpu_period = 100000
        cpu_max_file = cgroup_path / "cpu.max"
        cpu_max_file.write_text(f"{cpu_quota} {cpu_period}\n")
        
        # Memória: converter MB para bytes
        memory_bytes = config.memory_mb * 1024 * 1024
        memory_max_file = cgroup_path / "memory.max"
        memory_max_file.write_text(f"{memory_bytes}\n")
        
        # I/O: peso entre 1 e 10000
        try:
            io_weight_file = cgroup_path / "io.weight"
            if io_weight_file.exists():
                io_weight_file.write_text(f"default {config.io_weight}\n")
        except Exception:
            pass
        
        logger.info(f"Limites: {config.cpu_limit} cores, {config.memory_mb}MB, I/O {config.io_weight}")
    
    def _save_script(self, env_id: str, script_content: str) -> Path:
        """Salvar script em arquivo executável"""
        script_path = self.environments_dir / f"{env_id}.sh"
        script_path.write_text(script_content)
        script_path.chmod(0o755)
        return script_path
    
    def _build_unshare_command(self, script_path: Path, env_id: str) -> list:
        """Construir comando unshare com namespaces isolados"""
        command = [
            "unshare",
            "--pid",          # Namespace de PID
            "--mount",        # Namespace de montagens
            "--uts",          # Namespace de hostname
            "--ipc",          # Namespace de IPC
            "--fork",         # Fork antes de executar
            "--mount-proc",   # Montar /proc
            "bash",
            str(script_path)
        ]
        return command
    
    def _add_to_cgroup(self, env_id: str):
        """Adicionar processo atual ao cgroup"""
        cgroup_procs = self.cgroup_root / "execspace" / env_id / "cgroup.procs"
        try:
            cgroup_procs.write_text(f"{os.getpid()}\n")
        except Exception as e:
            logger.error(f"Erro ao adicionar ao cgroup: {e}")
    
    def _get_pid(self, env_id: str) -> Optional[int]:
        """Obter PID do ambiente"""
        try:
            pid_file = self.environments_dir / f"{env_id}.pid"
            if pid_file.exists():
                pid_content = pid_file.read_text().strip()
                pid = int(pid_content)
                return pid
        except Exception:
            pass
        return None
    
    def get_environment_status(self, env_id: str) -> str:
        """Obter status do ambiente"""
        pid = self._get_pid(env_id)
        if not pid:
            return "ERROR"
        
        try:
            os.kill(pid, 0)  # Signal 0 apenas verifica existência
            status = "RUNNING"
        except OSError:
            status = "EXITED"
        
        return status
    
    def get_environment_logs(self, env_id: str) -> str:
        """Obter logs do ambiente"""
        try:
            log_file = self.logs_dir / f"{env_id}.log"
            
            if log_file.exists():
                logs = log_file.read_text()
            else:
                logs = "Sem logs disponíveis"
            
            return logs
        except Exception as e:
            logger.error(f"Erro ao ler logs: {e}")
            return f"Erro ao ler logs: {str(e)}"
    
    def stop_environment(self, env_id: str) -> bool:
        """Parar ambiente (envia SIGTERM e depois SIGKILL se necessário)"""
        try:
            pid = self._get_pid(env_id)
            if not pid:
                return False
            
            # Tentar terminar graciosamente
            try:
                os.kill(pid, signal.SIGTERM)
                time.sleep(1)  # Aguardar 1 segundo
            except OSError:
                pass
            
            # Forçar se ainda estiver rodando
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass  # Já terminou
            
            logger.info(f"Ambiente parado: {env_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao parar ambiente: {e}")
            return False
    
    def remove_environment(self, env_id: str) -> bool:
        """Remover ambiente completamente (processo + cgroup + arquivos)"""
        try:
            # 1. Parar processo
            self.stop_environment(env_id)
            
            # 2. Remover cgroup (matar processos restantes)
            cgroup_path = self.cgroup_root / "execspace" / env_id
            if cgroup_path.exists():
                procs_file = cgroup_path / "cgroup.procs"
                if procs_file.exists():
                    for pid in procs_file.read_text().strip().split('\n'):
                        if pid:
                            try:
                                os.kill(int(pid), signal.SIGKILL)
                            except OSError:
                                pass
                
                time.sleep(0.5)  # Aguardar processos terminarem
                cgroup_path.rmdir()
            
            # 3. Remover arquivos
            for filename in [f"{env_id}.pid", f"{env_id}.sh"]:
                (self.environments_dir / filename).unlink(missing_ok=True)
            (self.logs_dir / f"{env_id}.log").unlink(missing_ok=True)
            
            logger.info(f"Ambiente removido: {env_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao remover ambiente: {e}")
            return False
    
    def list_environments(self) -> list:
        """Listar todos os ambientes"""
        environments = []
        
        for pid_file in self.environments_dir.glob("*.pid"):
            env_id = pid_file.stem
            status = self.get_environment_status(env_id)
            
            environments.append({
                "id": env_id,
                "status": status
            })
        
        return environments


