-- Codigo com o DDL de todas as tabelas do projeto 


CREATE TABLE integracao_chamados (
    -- Identificador único do registro (Primary Key)
    id INT AUTO_INCREMENT PRIMARY KEY,
    
    -- Dados do GLPI
    id_glpi INT NOT NULL,
    solicitante_id INT,                  -- ID do autor no GLPI
    solicitante_nome VARCHAR(255),       -- Nome do autor no GLPI
	tipo_demanda VARCHAR(100),           -- Ex: 'Melhoria de Sistemas', 'Correção'
    urgencia VARCHAR(50),                -- Ex: 'Alta', 'Baixa'
    
    -- Decisão do Script (novo_chamado.py)
    eh_novo_projeto BOOLEAN DEFAULT FALSE, -- TRUE = Novo Projeto, FALSE = Work Package
    
    -- Dados do OpenProject
    id_op INT,                           -- Pode ser NULL caso dê erro antes de criar
    tipo_op VARCHAR(50),                 -- 'work_package', 'project'
    categoria_op VARCHAR(100),           -- 'Bug', 'Funcionalidade', 'Tarefa' (ou ID do tipo_wp)
    prioridade_op INT,                   -- 1, 2, 3 ou 4 (mapeado pelo script)
    atribuido_op INT,                    -- ID do usuário (para fazer o rodízio / FIFO)
    
    -- Controle de Log e Execução
    status_integracao VARCHAR(50) DEFAULT 'pendente', -- 'pendente', 'sucesso', 'erro'
    mensagem_erro TEXT,                  -- Salva logs de erro (ex: 400 Bad Request, API fora)
    
    -- Datas de Auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);


