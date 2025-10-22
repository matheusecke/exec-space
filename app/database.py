"""
Configuração do banco de dados MySQL
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Configuração da conexão com MySQL
MYSQL_HOST = os.getenv("DB_HOST", "192.168.56.10")
MYSQL_PORT = os.getenv("DB_PORT", "3306")
MYSQL_USER = os.getenv("DB_USER", "execspace_user")
MYSQL_PASSWORD = os.getenv("DB_PASSWORD", "execspace_pass123")
MYSQL_DATABASE = os.getenv("DB_NAME", "exec_space")

# String de conexão
DATABASE_URL = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"

# Criar engine do SQLAlchemy
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verificar conexão antes de usar
    pool_recycle=3600,   # Reciclar conexões a cada hora
    echo=False           # Não mostrar queries SQL no console (mude para True para debug)
)

# SessionLocal para criar sessões de banco de dados
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para os modelos
Base = declarative_base()

# Dependency para FastAPI
def get_db():
    """
    Dependency que fornece uma sessão de banco de dados
    e garante que ela seja fechada após o uso
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

