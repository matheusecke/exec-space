-- Criação do banco de dados ExecSpace
CREATE DATABASE IF NOT EXISTS exec_space CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE exec_space;

-- Criação do usuário
CREATE USER IF NOT EXISTS 'execspace_user'@'%' IDENTIFIED BY 'execspace_pass123';
GRANT ALL PRIVILEGES ON exec_space.* TO 'execspace_user'@'%';
FLUSH PRIVILEGES;

-- Tabela de ambientes de execução
CREATE TABLE IF NOT EXISTS environments (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    status ENUM('RUNNING', 'EXITED', 'ERROR') DEFAULT 'RUNNING',
    cpu_limit FLOAT NOT NULL,
    memory_mb INT NOT NULL,
    io_weight INT DEFAULT 500,
    script_content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    process_id VARCHAR(64),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

