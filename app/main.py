"""
API FastAPI para gerenciamento de ambientes de execução isolados
Utiliza namespaces e cgroups Linux diretamente para isolamento de processos
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import List, Optional
import uuid
import logging

from database import get_db, engine
from models import Base, Environment, EnvironmentStatus
from environments import EnvironmentManager, EnvironmentConfig

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Criar tabelas no banco de dados
Base.metadata.create_all(bind=engine)

# Inicializar FastAPI
app = FastAPI(
    title="ExecSpace Platform",
    description="Plataforma para execução de scripts em ambientes isolados usando namespaces e cgroups",
    version="1.0.0"
)

# Inicializar Environment Manager
env_manager = EnvironmentManager()

# Modelos Pydantic para validação de dados
class EnvironmentCreate(BaseModel):
    """Modelo para criação de ambiente"""
    name: str = Field(..., min_length=1, max_length=255, description="Nome do ambiente")
    cpu_limit: float = Field(..., gt=0, le=2, description="Limite de CPU em cores (ex: 0.5 para 50%)")
    memory_mb: int = Field(..., gt=0, le=4096, description="Limite de memória em MB")
    io_weight: int = Field(500, ge=100, le=1000, description="Peso de I/O (100-1000)")
    script_content: str = Field(..., min_length=1, description="Conteúdo do script a ser executado")

class EnvironmentResponse(BaseModel):
    """Modelo de resposta de ambiente"""
    id: str
    name: str
    status: str
    cpu_limit: float
    memory_mb: int
    io_weight: int
    created_at: Optional[str]
    process_id: Optional[str]

class LogsResponse(BaseModel):
    """Modelo de resposta de logs"""
    environment_id: str
    logs: str

# Endpoints da API

@app.get("/", response_class=HTMLResponse)
async def root():
    """Redirecionar para a interface web"""
    with open("static/index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/environments", response_model=EnvironmentResponse)
async def create_environment(
    env_data: EnvironmentCreate,
    db: Session = Depends(get_db)
):
    """
    Criar um novo ambiente de execução isolado
    
    - Cria ambiente com unshare (namespaces: PID, NET, MNT, UTS, IPC)
    - Usa cgroups v2 para limitar recursos (CPU, memória, I/O)
    - Salva metadados no banco de dados MySQL
    """
    try:
        # Gerar ID único para o ambiente
        env_id = str(uuid.uuid4())
        
        # Criar configuração
        config = EnvironmentConfig(
            env_id=env_id,
            script_content=env_data.script_content,
            cpu_limit=env_data.cpu_limit,
            memory_mb=env_data.memory_mb,
            io_weight=env_data.io_weight,
            name=env_data.name
        )
        
        # Criar e executar ambiente
        env_info = env_manager.create_and_run_environment(config)
        
        # Criar registro no banco de dados
        db_environment = Environment(
            id=env_id,
            name=env_data.name,
            status=EnvironmentStatus.RUNNING,
            cpu_limit=env_data.cpu_limit,
            memory_mb=env_data.memory_mb,
            io_weight=env_data.io_weight,
            script_content=env_data.script_content,
            process_id=str(env_info['pid'])
        )
        
        db.add(db_environment)
        db.commit()
        db.refresh(db_environment)
        
        logger.info(f"Ambiente {env_id} criado com sucesso")
        
        return db_environment.to_dict()
        
    except Exception as e:
        logger.error(f"Erro ao criar ambiente: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao criar ambiente: {str(e)}")

@app.get("/api/environments", response_model=List[EnvironmentResponse])
async def list_environments(db: Session = Depends(get_db)):
    """
    Listar todos os ambientes de execução
    
    - Retorna lista de ambientes do banco de dados
    - Atualiza status verificando processos
    """
    try:
        environments = db.query(Environment).order_by(Environment.created_at.desc()).all()
        
        # Atualizar status de cada ambiente
        for env in environments:
            current_status = env_manager.get_environment_status(env.id)
            if env.status.value != current_status:
                env.status = EnvironmentStatus(current_status)
                db.commit()
        
        return [env.to_dict() for env in environments]
        
    except Exception as e:
        logger.error(f"Erro ao listar ambientes: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao listar ambientes: {str(e)}")

@app.get("/api/environments/{environment_id}", response_model=EnvironmentResponse)
async def get_environment(environment_id: str, db: Session = Depends(get_db)):
    """
    Obter detalhes de um ambiente específico
    """
    try:
        environment = db.query(Environment).filter(Environment.id == environment_id).first()
        
        if not environment:
            raise HTTPException(status_code=404, detail="Ambiente não encontrado")
        
        # Atualizar status
        current_status = env_manager.get_environment_status(environment.id)
        if environment.status.value != current_status:
            environment.status = EnvironmentStatus(current_status)
            db.commit()
        
        return environment.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter ambiente: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao obter ambiente: {str(e)}")

@app.get("/api/environments/{environment_id}/logs", response_model=LogsResponse)
async def get_environment_logs(environment_id: str, db: Session = Depends(get_db)):
    """
    Obter logs de execução de um ambiente
    
    - Retorna conteúdo do arquivo de log
    """
    try:
        environment = db.query(Environment).filter(Environment.id == environment_id).first()
        
        if not environment:
            raise HTTPException(status_code=404, detail="Ambiente não encontrado")
        
        # Obter logs
        logs = env_manager.get_environment_logs(environment_id)
        
        return {
            "environment_id": environment_id,
            "logs": logs
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter logs: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao obter logs: {str(e)}")

@app.post("/api/environments/{environment_id}/stop")
async def stop_environment(environment_id: str, db: Session = Depends(get_db)):
    """
    Parar execução de um ambiente
    
    - Para o processo
    - Atualiza status no banco de dados
    """
    try:
        environment = db.query(Environment).filter(Environment.id == environment_id).first()
        
        if not environment:
            raise HTTPException(status_code=404, detail="Ambiente não encontrado")
        
        # Parar ambiente
        success = env_manager.stop_environment(environment_id)
        
        if success:
            environment.status = EnvironmentStatus.EXITED
            db.commit()
            return {"message": "Ambiente parado com sucesso", "status": "exited"}
        else:
            raise HTTPException(status_code=500, detail="Erro ao parar ambiente")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao parar ambiente: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao parar ambiente: {str(e)}")

@app.delete("/api/environments/{environment_id}")
async def delete_environment(environment_id: str, db: Session = Depends(get_db)):
    """
    Remover um ambiente
    
    - Para e remove o ambiente
    - Remove registro do banco de dados
    """
    try:
        environment = db.query(Environment).filter(Environment.id == environment_id).first()
        
        if not environment:
            raise HTTPException(status_code=404, detail="Ambiente não encontrado")
        
        # Remover ambiente
        env_manager.remove_environment(environment_id)
        
        # Remover do banco de dados
        db.delete(environment)
        db.commit()
        
        logger.info(f"Ambiente {environment_id} removido com sucesso")
        
        return {"message": "Ambiente removido com sucesso"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao remover ambiente: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao remover ambiente: {str(e)}")

# Servir arquivos estáticos (frontend)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Verificar status da aplicação"""
    return {
        "status": "healthy",
        "namespaces": "enabled",
        "database": "connected"
    }

