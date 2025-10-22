"""
Modelos do banco de dados usando SQLAlchemy
"""
from sqlalchemy import Column, String, Float, Integer, Text, TIMESTAMP, Enum
from sqlalchemy.sql import func
from database import Base
import enum

class EnvironmentStatus(str, enum.Enum):
    """Enum para status do ambiente"""
    RUNNING = "RUNNING"
    EXITED = "EXITED"
    ERROR = "ERROR"

class Environment(Base):
    """
    Modelo para ambientes de execução
    """
    __tablename__ = "environments"
    
    id = Column(String(64), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    status = Column(Enum(EnvironmentStatus), default=EnvironmentStatus.RUNNING)
    cpu_limit = Column(Float, nullable=False)
    memory_mb = Column(Integer, nullable=False)
    io_weight = Column(Integer, default=500)
    script_content = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    process_id = Column(String(64), nullable=True)
    
    def to_dict(self):
        """Converte o modelo para dicionário"""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status.value if isinstance(self.status, enum.Enum) else self.status,
            "cpu_limit": self.cpu_limit,
            "memory_mb": self.memory_mb,
            "io_weight": self.io_weight,
            "script_content": self.script_content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "process_id": self.process_id
        }

