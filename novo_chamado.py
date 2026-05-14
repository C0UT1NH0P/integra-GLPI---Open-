import logging
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import json
import uvicorn
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import base64
import httpx
import requests
import pymysql
import re
import unicodedata
import glpi

load_dotenv(override=True) 

app = FastAPI()

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Definir diretório base e de logs automaticamente para não depender de caminho fixo
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

# URL base da API do OpenProject 
OPENPROJECT_URL = os.getenv('OPENPROJECT_URL')

# Token de acesso (Bearer Token) pegando do .env
API_KEY = os.getenv('APIKEY_OPEN')

APP_TOKEN = os.getenv("GLPI_APP_TOKEN_TESTES")
GLPI_API_URL = os.getenv("GLPI_API_URL_TESTES")
user_glpi = os.getenv('USER_GLPI')
pass_glpi = os.getenv('PASS_GLPI')

HOST_MYSQL = os.getenv('HOST_MYSQL')
PORT_MYSQL = int(os.getenv('PORT_MYSQL', 3306)) if os.getenv('PORT_MYSQL') else 3306
USER_MYSQL = os.getenv('USER_MYSQL')
PASS_MYSQL = os.getenv('PASS_MYSQL')
SCHEMA_MYSQL = os.getenv('SCHEMA_MYSQL')

# Handler para gravar o log da API em arquivo
api_handler = logging.FileHandler(os.path.join(LOGS_DIR, 'api.log'), encoding='utf-8')

# Handler para gravar apenas os erros em error.log
error_handler = logging.FileHandler(os.path.join(LOGS_DIR, 'error.log'), encoding='utf-8')
error_handler.setLevel(logging.ERROR)

# antes verificar se api.log, error.log e chamaados_dados.log existem, se não existir criar os arquivos
for log_file in ['api.log', 'error.log', 'chamados_dados.log']:
    log_path = os.path.join(LOGS_DIR, log_file)
    if not os.path.exists(log_path):
        with open(log_path, 'w') as f:
            f.write('')
        print(f'criado o arquivo {log_path}')

# Formatação e adição dos handlers
formatter = logging.Formatter('%(asctime)s - %(message)s')
api_handler.setFormatter(formatter)
error_handler.setFormatter(formatter)

logger.addHandler(api_handler)
logger.addHandler(error_handler)

# Logger específico para os dados dos chamados
dados_logger = logging.getLogger('dados_chamado')
dados_logger.setLevel(logging.INFO)
dados_handler = logging.FileHandler(os.path.join(LOGS_DIR, 'chamados_dados.log'), encoding='utf-8')
dados_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
dados_logger.addHandler(dados_handler)
dados_logger.propagate = False

DESCRICAO_ABERTURA = """**Definição:** Um documento de 1-2 páginas que autoriza o projeto. É o "contrato" inicial entre quem pede e quem faz.

**Conteúdo Essencial:**

* **Justificativa / Problema:** Por que estamos fazendo isso? (Ex: "Reduzir o tempo de lançamento de notas fiscais em 50%").
* **Objetivos e Critérios de Sucesso:** O que define que o projeto foi um sucesso?
* **Escopo (Alto Nível):** O que está e o que não está incluído.
* **Stakeholders:** Principais Envolvidos."""

DESCRICAO_LEVANTAMENTO = """**Definição:** Especificação Funcional. Uma lista viva e priorizada de tudo que o software precisa fazer, do ponto de vista do usuário. Nesta etapa realizar um levantamento da regra de negócio. Ao fim da tarefa, gerar o documento de Levantamento de Requisitos.

**Conteúdo Essencial:**

* **Épicos:** Grandes blocos de funcionalidade (Ex: "Gerenciamento de Usuários").
* **Histórias de Usuário:** O formato "Eu, como [Usuário], quero [Ação], para que [Benefício]". (Ex: "Eu, como administrador, quero redefinir a senha de um usuário, para que ele possa recuperar o acesso").
* **Critérios de Aceite:** Para cada história, a definição de "pronto". (Ex: "A senha deve ter 8 caracteres. O usuário recebe um e-mail de confirmação.").
* **Requisitos Não-Funcionais:** Coisas como performance, segurança, tempo de resposta, compatibilidade (Ex: "O sistema deve rodar no Chrome e Firefox").

*O conteúdo essencial se traduzirá nos pacotes de trabalho durante o Desenvolvimento.*"""

DESCRICAO_DESIGN = """**Definição:** Um documento técnico que descreve a arquitetura e as principais decisões de design.

**Conteúdo Essencial:**

* **Arquitetura (Diagrama):** Um diagrama simples mostrando os principais componentes (Ex: Frontend, Backend API, Banco de Dados, APIs Externas).
* **Tecnologias (Stack):** Linguagem, framework, banco de dados (Ex: Python/Django, React, PostgreSQL).
* **Contratos de API:** Se houver integração, como as APIs vão se comunicar (endpoints, o que enviam, o que recebem)."""

DESCRICAO_DESENVOLVIMENTO = """**Definição:** Enquanto o projeto é executado, documentar o uso e a manutenção.

**Documentação de Usuário:**
* **O que é?** Explica como usar o software.
* **Conteúdo Essencial:** Focado em tarefas. "Como cadastrar um cliente", "Como gerar um relatório".

**Documentação de Operação:**
* **O que é?** A documentação README para a equipe de TI/DevOps ou futuros desenvolvedores.
* **Conteúdo Essencial:**
  * Como instalar o projeto do zero.
  * Como fazer o GoLive de uma nova versão."""

DESCRICAO_HOMOLOGACAO = """**Definição:** A homologação valida se o software atende aos requisitos de negócio e às necessidades do usuário final. Durante os testes, caso sejam identificadas anomalias, o usuário deve registrá-las no Registro de Anomalias, e a equipe as classifica em:

* **Defeito/Bug:** o sistema não funciona conforme especificado → retorna para desenvolvimento para correção.
* **Mudança de Escopo (Nova Funcionalidade):** o sistema funciona, mas o usuário solicita algo não previsto → registrado no backlog para versões futuras.
* **Problema de Usabilidade ou Treinamento:** o sistema funciona, porém é confuso → pode gerar ajuste simples ou ser tratado com treinamento/melhoria futura.

*O objetivo é garantir que o sistema esteja adequado ao propósito para o qual foi desenvolvido, evitando aumento de escopo no fim do projeto.*

**Definir uma quantidade mínima de iterações com o sistema para que a homologação seja concluída.**"""

DESCRICAO_ENCERRAMENTO =  """**Definição:** O documento final. O cliente/Sponsor assina, concordando que o que foi pedido no "Termo de Abertura" foi entregue.

**Conteúdo Essencial:**

* Resumo do que foi entregue.
* Confirmação de que os critérios de sucesso foram atingidos.
* Assinatura do solicitante."""

def salvar_erro_banco(id_glpi, mensagem_erro):
    """Salva a mensagem de erro no banco de dados para o chamado correspondente"""
    if not id_glpi:
        return
    try:
        conn = pymysql.connect(
            host=HOST_MYSQL, port=PORT_MYSQL, user=USER_MYSQL,
            password=PASS_MYSQL, database=SCHEMA_MYSQL
        )
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE integracao_chamados 
                SET status_integracao = 'erro', mensagem_erro = %s
                WHERE id_glpi = %s
            """, (str(mensagem_erro), id_glpi))
            
            # Se não houver linha atualizada (ex: chamado não foi inserido antes), insere o erro
            if cursor.rowcount == 0:
                cursor.execute("""
                    INSERT INTO integracao_chamados (id_glpi, status_integracao, mensagem_erro)
                    VALUES (%s, 'erro', %s)
                """, (id_glpi, str(mensagem_erro)))
        conn.commit()
        conn.close()
    except Exception as db_e:
        logger.error(f"Erro ao tentar salvar erro no banco para o chamado {id_glpi}: {db_e}")

def obter_lockversion_pacote_de_trabalho(id__pacote_de_trabalho):
    """Obtém o último LockVersion de um pacote de trabalho para fazer PATCH em suas propriedades evitando problemas de concorrência

    Args:
        id__pacote_de_trabalho (int): ID do pacote de trabalho
        
    Returns:
        int: O último LockVersion do pacote de trabalho
    """
    url = f"{OPENPROJECT_URL}/api/v3/work_packages/{id__pacote_de_trabalho}"
    
    response = requests.get(url, auth=('apikey', API_KEY))
    response.raise_for_status()
    
    return response.json().get("lockVersion")

def atualizar_status_projeto(id__projeto, id__status):
    """Atualiza o status de um projeto de acordo com as opções do GLPI

    Args:
        id__projeto (int): ID do projeto no OpenProject
        id__status (int): ID do status de acordo com a lista: [ 7 - Novo, 8 - Em Andamento, 9 - Aguardando, 10 - Resolvido ]
        
    Returns:
        int: Status code da resposta da API do OpenProject
    """    
    url = f"{OPENPROJECT_URL}/api/v3/projects/{id__projeto}"
    
    data = {
        "_links": {
            "customField6": {
                "href": f"/api/v3/custom_options/{id__status}"
            }
        }
    }
    
    response = requests.patch(url, json=data, auth=('apikey', API_KEY))
    
    response.raise_for_status()
    
    return response.status_code
 
def rejeitar_pacote_de_trabalho(id__pacote_de_trabalho, id__status):
    """Atualiza o status de um pacote de trabalho de acordo com as opções do GLPI

    Args:
        id__pacote_de_trabalho (int): ID do pacote de trabalho no OpenProject
        id__status (int): ID do status de acordo com a lista: [1 - Novo, 2 até 10 - Em Progresso, 12 - Fechado, 14 - Rejeitado, 15 - Rejeitado pelo solicitante]
        
    Returns:
        int: Status code da resposta da API do OpenProject
        text: Texto da resposta da API do OpenProject
    """    
    url = f"{OPENPROJECT_URL}/api/v3/work_packages/{id__pacote_de_trabalho}"
    
    lockVersion = obter_lockversion_pacote_de_trabalho(id__pacote_de_trabalho)
    
    data = {
            "lockVersion": lockVersion,
            "_links": {
                "status": {
                        "href": f"/api/v3/statuses/{id__status}"
                }
            }
    }
    
    response = requests.patch(url, json=data, auth=('apikey', API_KEY))
    
    response.raise_for_status()
    
    return response.status_code, response.text

def atualizar_status_pacote_de_trabalho(id__pacote_de_trabalho, id__status):
    """Atualiza o status de um pacote de trabalho de acordo com as opções do GLPI

    Args:
        id__pacote_de_trabalho (int): ID do pacote de trabalho no OpenProject
        id__status (int): ID do status de acordo com a lista: [ 11 - Novo, 12 - Em Andamento, 13 - Aguardando, 14 - Resolvido ]
        
    Returns:
        int: Status code da resposta da API do OpenProject
    """    
    url = f"{OPENPROJECT_URL}/api/v3/work_packages/{id__pacote_de_trabalho}"
    
    lockVersion = obter_lockversion_pacote_de_trabalho(id__pacote_de_trabalho)
    
    data = {
            "lockVersion": lockVersion,
            "_links": {
                "customField7": {
                        "href": f"/api/v3/custom_options/{id__status}"
                }
            }
    }
    
    response = requests.patch(url, json=data, auth=('apikey', API_KEY))
    
    response.raise_for_status()
    
    return response.status_code

def adicionar_comentario_pacote_de_trabalho(id__pacote_de_trabalho, comentario):
    """Adiciona um comentário em um pacote de trabalho existente
    
    Args:
        id__pacote_de_trabalho (int): ID do pacote de trabalho
        comentario (str): Texto do comentário (suporta markdown)
        
    Returns:
        int: Status code da resposta da API do OpenProject
    """
    url = f"{OPENPROJECT_URL}/api/v3/work_packages/{id__pacote_de_trabalho}"
    lockVersion = obter_lockversion_pacote_de_trabalho(id__pacote_de_trabalho)
    
    data = {
        "lockVersion": lockVersion,
        "journal": {
            "notes": {
                "format": "markdown",
                "raw": comentario
            }
        }
    }
    
    response = requests.patch(url, json=data, auth=('apikey', API_KEY))
    response.raise_for_status()
    return response.status_code
    
def atualizar_prioridade_pacote_de_trabalho(id__pacote_de_trabalho, id__prioridade):
    """Atualiza a prioridade de um pacote de trabalho de acordo com as opções da API do OpenProject

    Args:
        id__pacote_de_trabalho (int): ID do pacote de trabalho
        id__prioridade (int): ID da prioridade de acordo com a lista:[ 7 - Baixa, 8 - Normal, 9 - Alta, 10 - Imediata ] 
        
    Returns:
        int: Status code da resposta da API do OpenProject
    """    
    url = f"{OPENPROJECT_URL}/api/v3/work_packages/{id__pacote_de_trabalho}"
    
    lockVersion = obter_lockversion_pacote_de_trabalho(id__pacote_de_trabalho)
    
    data = {
        'lockVersion': lockVersion,
        '_links': {
            "priority": {
                "href": f"/api/v3/priorities/{id__prioridade}"
            }
        }
    }
    
    response = requests.patch(url, json=data, auth=('apikey', API_KEY))
    
    response.raise_for_status()
    
    return response.status_code

def add_project_member(project_id, user_id, role_id):
    """
    Adiciona um usuário a um projeto no OpenProject com um cargo específico.
    
    Parâmetros:
    - project_id (int): O ID do projeto.
    - user_id (int): O ID do usuário (ex: 6 para Pedro, 3 para Gabriel).
    - role_id (int): O ID do cargo a ser atribuído (ex: 3, 4, 8 - depende da sua configuração).
    """
    url = f"{OPENPROJECT_URL}/api/v3/memberships"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "_links": {
            "project": {"href": f"/api/v3/projects/{project_id}"},
            "principal": {"href": f"/api/v3/users/{user_id}"},
            "roles": [
                {"href": f"/api/v3/roles/{role_id}"}
            ]
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, auth=('apikey', API_KEY))
        response.raise_for_status()
        print(f"Usuário ID {user_id} adicionado ao projeto {project_id} com sucesso!")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao adicionar usuário {user_id}: {e}")
        if e.response is not None and e.response.text:
            print(f"Detalhes: {e.response.text}")
        return None

def add_project_group(project_id, user_id, role_id):
    """
    Adiciona um usuário a um projeto no OpenProject com um cargo específico.
    
    Parâmetros:
    - project_id (int): O ID do projeto.
    - user_id (int): O ID do usuário (ex: 6 para Pedro, 3 para Gabriel, 10 para IA).
    - role_id (int): O ID do cargo a ser atribuído (ex: 3, 4, 8 - depende da sua configuração).
    """
    url = f"{OPENPROJECT_URL}/api/v3/memberships"
    headers = {"Content-Type": "application/json"}
    
    payload = {
        "_links": {
            "project": {"href": f"/api/v3/projects/{project_id}"},
            "principal": {"href": f"/api/v3/groups/{user_id}"},
            "roles": [
                {"href": f"/api/v3/roles/{role_id}"}
            ]
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, auth=('apikey', API_KEY))
        response.raise_for_status()
        print(f"Usuário ID {user_id} adicionado ao projeto {project_id} com sucesso!")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao adicionar usuário {user_id}: {e}")
        if e.response is not None and e.response.text:
            print(f"Detalhes: {e.response.text}")
        return None

def criar_identificador_valido(texto):
    """
    Transforma um texto comum em um identificador válido para o OpenProject.
    Ex: 'Projeto Fluxo de caixa_0012535' vira 'projeto-fluxo-de-caixa_0012535'
    """
    # 1. Remove acentos e caracteres especiais (ex: á -> a, ç -> c)
    texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    
    # 2. Converte tudo para minúsculas
    texto = texto.lower()
    
    # 3. Substitui espaços e qualquer coisa que não seja letra, número ou sublinhado por hífen
    texto = re.sub(r'[^a-z0-9_]', '-', texto)
    
    # 4. Remove hifens duplicados (ex: 'projeto---teste' vira 'projeto-teste')
    texto = re.sub(r'-+', '-', texto)
    
    # 5. Remove hifens nas pontas do texto
    return texto.strip('-')

def create_project(name, identifier, description="", public=False, active=True, parent_id=None, file_paths=None):
    """
    Cria um novo Projeto no OpenProject via API.
    
    Parâmetros:
    - name (str): O nome de exibição do projeto.
    - identifier (str): Um identificador único para o projeto (ex: 'meu-novo-projeto'). 
                        Geralmente minúsculas, sem espaços ou caracteres especiais.
    - description (str): A descrição detalhada do projeto (suporta formatação Markdown).
    - public (bool): Se o projeto é público (acessível a todos) ou privado. Padrão: True.
    - active (bool): Se o projeto já nasce ativo. Padrão: True.
    - parent_id (int/str): (Opcional) O ID do projeto pai, caso seja um subprojeto.
    """
    
    if not API_KEY or not OPENPROJECT_URL:
        print("Erro: OPENPROJECT_URL ou APIKEY_OPEN não encontradas no ambiente.")
        return None

    # Endpoint para criação de projetos
    url = f"{OPENPROJECT_URL}/api/v3/projects"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    # Construindo o payload base
    payload = {
        "name": name,
        "identifier": identifier,
        "public": public,
        "active": active
    }

    # Adicionando descrição em Markdown, se fornecida
    if description:
        payload["description"] = {
            "format": "markdown",
            "raw": description
        }

    _links = {}

    # Adicionando vínculo a um projeto pai, se for um subprojeto
    if parent_id:
        _links["parent"] = {
            "href": f"/api/v3/projects/{parent_id}"
        }


    # Se houver links a serem adicionados, insere no payload
    if _links:
        payload["_links"] = _links

    print(f"Criando Projeto '{name}' (Identificador: {identifier})...")
    
    try:
        response = requests.post(
            url,
            headers=headers,
            json=payload,
            auth=('apikey', API_KEY) 
        )
        
        response.raise_for_status()
        data = response.json()
        project_id = data.get('id')
    
        users = [4, 6]
        for user_id in users:
            "Adiciona os tecnicos como membros do projeto"
            add_project_member(project_id, user_id, 3) # adiciona como membro do projeto 


        user_adm = [11]
        for user_id in user_adm:
            "Adiciona o administrador do projeto"
            add_project_member(project_id, user_id, 5) # adiciona como administrador do projeto

        user_group = [10]
        for user_id in user_group:
            "Adiciona o grupo IA no projeto para filtros de atualizações"
            add_project_group(project_id, user_id, 3) # adiciona como membro do projeto
        
        print(f"Sucesso! Projeto criado com ID: {project_id}")
        print(f"Link: {OPENPROJECT_URL}/projects/{identifier}")

        if file_paths:
            # criar um pacote de trabalho como historia de usuario com o nome de anexos
            create_work_package(project_id, subject='Anexos do GLPI', priority=7, description="Anexos do GLPI", type_id=6, notify=False, file_paths=file_paths) 
        
        # depois de criado o novo projeto precisamos criar os pacotes de trabalho padrão
        pacotes_padrao = [
            {'subject': 'Termo de Abertura', 'description': DESCRICAO_ABERTURA, 'type_id': 3},
            {'subject': 'Levantamento de Requisitos', 'description': DESCRICAO_LEVANTAMENTO, 'type_id': 3},
            {'subject': 'Design Simplificado da Solução', 'description': DESCRICAO_DESIGN, 'type_id': 3},
            {'subject': 'Desenvolvimento e Documentação', 'description': DESCRICAO_DESENVOLVIMENTO, 'type_id': 3},
            {'subject': 'Homologação', 'description': DESCRICAO_HOMOLOGACAO, 'type_id': 3},
            {'subject': 'Termo de Encerramento do Projeto', 'description': DESCRICAO_ENCERRAMENTO, 'type_id': 2},
        ]

        for pacote in pacotes_padrao:
            create_work_package(
                project_id, 
                subject=pacote['subject'], 
                priority=7, 
                description=pacote['description'], 
                type_id=pacote['type_id'], 
                notify=False, 
                file_paths=None
            )

        return data, project_id

    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição: {e}")
        if e.response is not None and e.response.text:
            print(f"Detalhes do erro do servidor: {e.response.text}")
        
        return None, None


def extrair_dados_de_tabela_html(html_content: str) -> dict:
    """
    Analisa um conteúdo HTML para extrair dados de uma tabela específica.

    A função espera uma tabela onde cada linha contém duas células principais:
    - A primeira célula (com colspan="2") contém a pergunta/chave.
    - A segunda célula contém a resposta/valor.

    Args:
        html_content: Uma string contendo o código HTML da tabela.

    Returns:
        Um dicionário com os dados extraídos (chave: valor).
    """
    # Cria um objeto BeautifulSoup para analisar o HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Dicionário para armazenar os dados
    dados_extraidos = {}

    # Encontra todas as linhas <tr> dentro do corpo da tabela <tbody>
    linhas = soup.find('tbody').find_all('tr')

    # Itera sobre cada linha
    for linha in linhas:
        # Encontra todas as células <td> na linha
        celulas = linha.find_all('td')
        
        # Verifica se a linha tem o formato esperado (2 células)
        if len(celulas) == 2:
            # A primeira célula é a chave (pergunta)
            # .get_text(strip=True) extrai o texto e remove espaços em branco
            chave = celulas[0].get_text(strip=True)
            
            # A segunda célula é o valor (resposta)
            valor = celulas[1].get_text(strip=True)
            
            # Adiciona ao dicionário apenas se a chave não estiver vazia
            if chave:
                dados_extraidos[chave] = valor
                
    return dados_extraidos

def create_work_package(project_id, subject, priority, description="", type_id=None, notify=False, file_paths=None):
    """
    Cria um novo Work Package (Pacote de Trabalho) em um projeto específico do OpenProject e (opcionalmente) envia um anexo.
    
    Parâmetros:
    - project_id (int/str): O ID do projeto onde a tarefa será criada.
    - subject (str): O título/assunto do work package.
    - priority: (Ajuste o uso conforme sua necessidade, não está no payload atual).
    - description (str): A descrição detalhada (suporta formatação Markdown).
    - type_id (int): (Opcional) O ID do tipo da tarefa.
    - notify (bool): Se deve notificar os usuários sobre a criação (padrão: False).
    - file_path (str): (Opcional) Caminho absoluto ou relativo do arquivo a ser anexado.
    """
    
    # Assegure-se de que essas variáveis globais estão definidas
    if not API_KEY or not OPENPROJECT_URL:
        print("Erro: OPENPROJECT_URL ou APIKEY_OPEN não encontradas no arquivo .env")
        return None

    # 1. Endpoint para criação de work packages
    url = f"{OPENPROJECT_URL}/api/v3/projects/{project_id}/work_packages"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    params = {
        "notify": str(notify).lower()
    }

    payload = {
        "subject": subject,
        "description": {
            "format": "markdown",
            "raw": description
        }
    }

    _links = {}

    if type_id:
        _links["type"] = {
            "href": f"/api/v3/types/{type_id}"
        }

    
    USERS_MAP = {
        "gabriel_brito": 4,
        "pedro_coutinho": 6
    }
    
    # Fila do rodízio FIFO: Pedro (6), Gabriel (4)
    fila_tecnicos = [6, 4]
    assignee_id = fila_tecnicos[0]
    
    # Conectar ao banco para descobrir o último técnico atribuído
    try:
        conexao = pymysql.connect(
            host=os.getenv('HOST_MYSQL', 'localhost'),
            user=os.getenv('USER_MYSQL', 'root'),
            password=os.getenv('PASS_MYSQL', ''),
            database=os.getenv('SCHEMA_MYSQL', 'glpi_op'),
            port=int(os.getenv('PORT_MYSQL', 3306)),
            cursorclass=pymysql.cursors.DictCursor
        )
        
        with conexao.cursor() as cursor:
            # Busca o último técnico a receber um chamado com sucesso
            sql = "SELECT atribuido_op FROM integracao_chamados WHERE atribuido_op IS NOT NULL ORDER BY id DESC LIMIT 1"
            cursor.execute(sql)
            resultado = cursor.fetchone()
            
            if resultado and resultado['atribuido_op'] in fila_tecnicos:
                ultimo_atribuido = resultado['atribuido_op']
                # Descobre quem é o próximo da fila (volta pro começo se chegar no final)
                indice_atual = fila_tecnicos.index(ultimo_atribuido)
                proximo_indice = (indice_atual + 1) % len(fila_tecnicos)
                assignee_id = fila_tecnicos[proximo_indice]
            else:
                # Se não tiver registro válido ou não achar, pega o primeiro da fila
                assignee_id = fila_tecnicos[0]
                
    except Exception as e:
        print(f"Erro ao consultar a tabela integracao_chamados para o FIFO: {e}")
        print(f"Usando técnico padrão ({assignee_id}).")
    finally:
        if 'conexao' in locals() and conexao.open:
            conexao.close()
            
    responsible_id = assignee_id

    # Adicionando o Atribuído (Assignee) no OpenProject

    if int(type_id) not in (2, 3):
        # nãp inserir atribuido quando for apenas um pacote de trabalho padrão vindo da criação de um projeto 
        if assignee_id:
            _links["assignee"] = {
                "href": f"/api/v3/users/{assignee_id}"
            }

        # Adicionando o Responsável (Responsible) no OpenProject
        if responsible_id:
            _links["responsible"] = {
                "href": f"/api/v3/users/{responsible_id}"
            }

    if priority:
        
        prioridade = 8 # Normal por padrão
        if priority == 7:
            prioridade = 'Baixa'
        elif priority == 8:
            prioridade = 'Normal'
        elif priority == 9:
            prioridade = 'Alta'
        elif priority == 10:
            prioridade = 'Imediata'
        
        _links["priority"] = {
            "href": f"/api/v3/priorities/{priority}",
            # "title": f"{prioridade}"
        }

    if _links:
        payload["_links"] = _links

    print(f"Criando Work Package no projeto {project_id}...")
    
    try:
        # ETAPA 1: Criar o Pacote de Trabalho
        response = requests.post(
            url,
            headers=headers,
            params=params,
            json=payload,
            auth=('apikey', API_KEY) 
        )
        
        response.raise_for_status()
        data = response.json()
        wp_id = data.get('id')
        
        print(f"Sucesso! Work Package criado com ID: {wp_id}")
        print(f"Link: {OPENPROJECT_URL}/work_packages/{wp_id}")
        
        # ETAPA 2: Enviar o Anexo (Se um caminho de arquivo for fornecido)
        if file_paths:
            for fpath in file_paths:
                if os.path.exists(fpath):
                    print(f"Enviando anexo: {fpath}...")
                    attach_url = f"{OPENPROJECT_URL}/api/v3/work_packages/{wp_id}/attachments"
                    
                    file_name = os.path.basename(fpath)
                    metadata = {"fileName": file_name}
                    
                    with open(fpath, 'rb') as file_data:
                        # Monta o multipart/form-data
                        files = {
                            'metadata': (None, json.dumps(metadata), 'application/json'),
                            'file': (file_name, file_data, 'application/octet-stream')
                        }
                        
                        # Ao usar o parâmetro 'files', a biblioteca requests configura o 
                        # Content-Type para multipart/form-data automaticamente.
                        attach_response = requests.post(
                            attach_url,
                            files=files,
                            auth=('apikey', API_KEY)
                        )
                        
                        attach_response.raise_for_status()
                        print(f"Anexo {file_name} enviado com sucesso!")
                else:
                    print(f"Aviso: O arquivo '{fpath}' não foi encontrado.")
        
        return data, responsible_id

    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição: {e}")
        if e.response is not None and e.response.text:
            print(f"Detalhes do erro do servidor: {e.response.text}")
        return None

def kill_glpi_api_session(session_token):
   headers = {
      "Session-Token": f"{session_token}",
      "App-Token": f"{os.getenv('GLPI_APP_TOKEN')}",
      "Content-Type": "application/json"
   }

   url = f"{os.getenv('GLPI_API_BASE_URL')}/killSession"

   response = requests.request("GET", url, headers=headers)
   
   return response.status_code    

def initSession():
    """Recebe username/password, valida na API GLPI via HTTP Basic Auth e retorna a sessão GLPI."""

    auth_string = f"{user_glpi}:{pass_glpi}"
    auth_bytes = auth_string.encode("utf-8")
    auth_base64 = base64.b64encode(auth_bytes).decode("utf-8")

    headers = {
        "Authorization": f"Basic {auth_base64}"
    }

    try:
        
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{GLPI_API_URL}/apirest.php/initSession/",
                headers=headers,
            )
        # print(response.json())

        # Verifica se deu erro 4xx/5xx
        response.raise_for_status()
        
        # Retorna o JSON da sessão GLPI
        glpi_session_data = response.json()
        
        session_token = glpi_session_data.get("session_token")

        return session_token

    except httpx.HTTPStatusError as exc:
        
        if exc.response.status_code == 400:
            print("Usuário ou senha incorretos no Login do GLPI.")
        elif exc.response.status_code == 401:
            print('Desautorizado Login')
        else:
            print(f"Erro da API do GLPI: {exc.response.text}")
        raise

    except httpx.RequestError as exc:
        print(f"Erro ao conectar ao GLPI: {exc}")
        raise

    except Exception as e:
        print(f"Erro ao gerar session token: {e}")

@app.api_route('/webhook', methods=['POST'])
async def webhook(request: Request):
    try:
        data = await request.json()
        print(f'webhook {data}')
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON or no JSON received"})

    if data is None:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON or no JSON received"})

    ticket = data.get('ticket', {})
    
    # Tratamento caso ticket venha como outro tipo que não dict
    if not isinstance(ticket, dict):
        ticket = {}

    action = ticket.get('action')
    ticket_id = ticket.get('id')
    url_chamado = f"{GLPI_API_URL}/index.php?redirect=ticket_{ticket_id}"
    title = ticket.get('title', '')
    category = ticket.get('category', '')
    author = data.get('author', {})
    id_autor = author.get('id')
    nome_autor = author.get('name')

    log_msg = f"/\taction: {action}\tticket_id: {ticket_id}"
    logger.info(log_msg)

    # Verifica se é uma rejeição de solução
    solucao = ticket.get('solution', {})
    if isinstance(solucao, dict):
        approval = solucao.get('approval', {})
        if isinstance(approval, dict):
            desc_aprovacao = approval.get('description', '')
            if action == 'Solução rejeitada' or (desc_aprovacao and desc_aprovacao != 'Solução aprovada'):
                print(f'id do chamado rejeitado {ticket_id}')
                descricao_rejeicao = desc_aprovacao if desc_aprovacao else "Solução rejeitada pelo usuário."

                               
                try:
                    conn = pymysql.connect(
                        host=HOST_MYSQL,
                        port=PORT_MYSQL,
                        user=USER_MYSQL,
                        password=PASS_MYSQL,
                        database=SCHEMA_MYSQL,
                        cursorclass=pymysql.cursors.DictCursor
                    )
                    with conn.cursor() as cursor:
                        sql = "SELECT id_op, tipo_op FROM integracao_chamados WHERE id_glpi = %s ORDER BY id DESC LIMIT 1"
                        cursor.execute(sql, (ticket_id,))
                        registro = cursor.fetchone()
                        
                        if registro and registro['id_op']:
                            id_op = registro['id_op']
                            tipo_op = registro['tipo_op']
                            
                            if tipo_op == 'work_package':
                                
                                rejeitado, text = rejeitar_pacote_de_trabalho(id_op, 15)
                                if rejeitado == 200:
                                    print(f"Pacote de trabalho {id_op} reaberto com sucesso.")
                                else:
                                    print(f"Erro ao reabrir pacote de trabalho {id_op}.")
                                    salvar_erro_banco(ticket_id, f"Erro ao reabrir rejeitar chamado: {text}")
                                
                except Exception as e:
                    logger.error(f"Erro ao reabrir chamado {ticket_id} no OpenProject: {e}")
                    print(f"Erro ao reabrir chamado {ticket_id} no OpenProject: {e}")
                    salvar_erro_banco(ticket_id, f"Erro ao reabrir chamado no OpenProject: {e}")
                finally:
                    if 'conn' in locals() and conn.open:
                        conn.close()

                return {"status": "OK"}
    
    session_token = initSession()

    headers = {
        'Content-Type': 'application/json',
        'Session-Token': f'{session_token}',
        'App-Token': f'{APP_TOKEN}'  
    }

    endpoint = f"{GLPI_API_URL}/apirest.php/Ticket/{ticket_id}/Document_Item"
    arquivos_baixados = []

    try:
        # 🔹 Faz a requisição GET para buscar os anexos do ticket
        response = requests.get(endpoint, headers=headers)

        try:
            anexos = response.json()
            print(f'Anexos: {anexos}')
        except json.JSONDecodeError as e:
            print(f"❌ Erro ao decodificar JSON para o ticket {ticket_id}")
            print(response.text)
            salvar_erro_banco(ticket_id, f"Erro ao decodificar JSON dos anexos: {e}")
            return

        print(f"📋 Chamado {ticket_id} - {len(anexos)} anexo(s) encontrado(s)")



        if anexos and len(anexos) > 0:
            pasta_anexos = os.path.join(BASE_DIR, "anexos", str(ticket_id))
            os.makedirs(pasta_anexos, exist_ok=True)
            
            for item in anexos:
                doc_id = item.get("documents_id")
                if doc_id:
                    # Primeiro: Buscar o NOME do arquivo na API REST
                    meta_url = f"{GLPI_API_URL}/apirest.php/Document/{doc_id}"
                    meta_resp = requests.get(meta_url, headers=headers)
                    
                    filename = f"anexo_{doc_id}" # Nome padrão caso falhe
                    
                    if meta_resp.status_code == 200:
                        try:
                            doc_info = meta_resp.json()
                            filename = doc_info.get("filename", filename)
                        except json.JSONDecodeError as e:
                            print(f"⚠️ Aviso: Não foi possível ler o JSON de metadados do doc {doc_id}")
                            salvar_erro_banco(ticket_id, f"Erro JSON metadados doc {doc_id}: {e}")
                    
    
                    download_url = f"{GLPI_API_URL}/front/document.send.php?docid={doc_id}&tickets_id={ticket_id}"
                    
                    # Usa stream=True direto na chamada de download
                    file_resp = requests.get(download_url, headers=headers, stream=True)
                    
                    if file_resp.status_code == 200:
                        filepath = os.path.join(pasta_anexos, filename)
                        with open(filepath, 'wb') as f:
                            for chunk in file_resp.iter_content(chunk_size=8192):
                                if chunk: # Filtra os keep-alive (chunks vazios)
                                    f.write(chunk)
                        arquivos_baixados.append(filepath)
                        print(f"✅ Anexo baixado: {filename}")
                    else:
                        erro_msg = (f"❌ Erro HTTP {file_resp.status_code} ao tentar baixar o documento {doc_id}.\n"
                                    f"   URL Tentada: {download_url}")
                        print(erro_msg)
                        salvar_erro_banco(ticket_id, erro_msg)
                        
                        try:
                            logger.error(erro_msg)
                        except NameError:
                            pass 

    except Exception as e:
        print(f"❌ Erro ao processar anexos: {e}")
        salvar_erro_banco(ticket_id, f"Erro ao processar anexos: {e}")
        try:
            logger.error(f"Erro ao processar anexos: {e}")
        except NameError:
            pass

    if action == "Novo chamado" and str(title).startswith("Projeto") and category == 'IA - Integração e Automação de Sistemas > Automação':

        colunas = extrair_dados_de_tabela_html(ticket.get('content', ''))

        # Printa os resultados formatados
        print("\nDADOS EXTRAÍDOS:\n")
        print(f"Autor: {nome_autor} (ID: {id_autor})")
        for chave, valor in colunas.items():
            print(f"{chave}: {valor}")
        
        nome_sistema = "N/A"
        for k, v in colunas.items():
            if "Nome do Projeto" in k or "Sistema" in k:
                nome_sistema = v
                break

        # Extrair dados para o segundo arquivo de log e para processamento
        tipo_projeto = colunas.get("Tipo de Projeto", "N/A")
        impacto_solicitante = colunas.get("Impacto no setor solicitante", "N/A")
        impacto_outros = colunas.get("Impacto em outros setores?", colunas.get("Impacto em outros setores", "N/A"))
        urgencia = colunas.get("Urgência", "N/A")
        tipo_demanda = colunas.get("Tipo de Demanda", "N/A")
        categoria_demanda = colunas.get("Categoria", colunas.get("Categoria", "N/A"))
        descricao_projeto = colunas.get("Descrição do Projeto", colunas.get("Descrição do Projeto", "N/A"))

        db_id = None
        try:
            conn = pymysql.connect(
                host=HOST_MYSQL,
                port=PORT_MYSQL,
                user=USER_MYSQL,
                password=PASS_MYSQL,
                database=SCHEMA_MYSQL,
                cursorclass=pymysql.cursors.DictCursor
            )
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO integracao_chamados 
                    (id_glpi, solicitante_id, solicitante_nome, tipo_demanda, urgencia, status_integracao) 
                    VALUES (%s, %s, %s, %s, %s, 'pendente')
                """
                cursor.execute(sql, (ticket_id, id_autor, nome_autor, tipo_demanda, urgencia))
                db_id = cursor.lastrowid
            conn.commit()
            conn.close()
            logger.info(f"Chamado {ticket_id} inserido com status pendente no BD (ID: {db_id}).")
        except Exception as e:
            logger.error(f"Erro ao inserir chamado {ticket_id} no BD: {e}")
            salvar_erro_banco(ticket_id, f"Erro ao inserir chamado no BD: {e}")

        # Grava os dados capturados em chamados_dados.log
        dados_logger.info(f"ID: {ticket_id} | Projeto: {tipo_projeto} | Sistema: {nome_sistema} | Urgência: {urgencia} | Categoria: {categoria_demanda}")

        # LÓGICA DE TOMADA DE DECISÃO
        vira_projeto = False
        
        # 1. Definição Explícita
        if tipo_projeto == "Novo Projeto":
            vira_projeto = True
            
        # 2. Desenvolvimento de Soluções
        if categoria_demanda in ["Novo sistema", "Nova automação", "Novo bot"]:
            vira_projeto = True
            
        # 3. Demandas Estratégicas
        if tipo_demanda == "Demandas Estratégicas" or categoria_demanda in ["Projetos internos", "Solicitações da diretoria", "Inovação"]:
            vira_projeto = True

        # 4. Condições Especiais (Impacto e Urgência Elevados)
        impacto_alto = "alto" in impacto_solicitante.lower()
        urgencia_alta = urgencia.lower() in ["alta", "imediata", "muito alta"]
        
        if tipo_demanda in ["Melhoria de Sistemas", "Melhoria de Sistema"]:
            if impacto_alto and urgencia_alta:
                vira_projeto = True
                
        if categoria_demanda == "Integração entre sistemas":
            if impacto_alto and urgencia_alta:
                vira_projeto = True

        # Mapeamento de prioridade
        urgencia_lower = urgencia.lower()
        prioridade = 8 # Normal por padrão
        if "baixa" in urgencia_lower or "muito baixa" in urgencia_lower:
            prioridade = 7
        elif "alta" in urgencia_lower:
            prioridade = 9
        elif "imediata" in urgencia_lower or "muito alta" in urgencia_lower:
            prioridade = 10

        print(f"\n--- DECISÃO DE INTEGRAÇÃO GLPI -> OPENPROJECT ---")
        print(f"Chamado ID: {ticket_id} | Solicitante: {nome_autor}")

        if vira_projeto:
            print("Decisão: CRIAR NOVO PROJETO")
            print(f"Título/Nome do Projeto: {nome_sistema}")
            
            description = f"**Solicitante:** {nome_autor} (ID: {id_autor})\n\n"
            description += f"**Descrição:**\n{descricao_projeto}\n\n"
            description += f"**Tipo de Demanda:** {tipo_demanda}\n"
            description += f"**Categoria:** {categoria_demanda}\n"
            description += f"**Urgência:** {urgencia}\n"
            description += f"**Impacto no setor solicitante:** {impacto_solicitante}\n"
            description += f"**Impacto em outros setores:** {impacto_outros}\n"
            description += f"**Chamado GLPI:** {url_chamado}\n"
            if anexos and len(anexos) > 0:
                description += f"**Anexos:** {len(anexos)} anexo(s) no pacote de Trabalho\n"
            
            print(f"Prioridade: {prioridade}")
            print(f"Descrição que será enviada:\n{description}")
            logger.info(f"Decisão: Criar Novo Projeto. Sistema: {nome_sistema}")
            meu_identificador = criar_identificador_valido(f'{nome_sistema}_{ticket_id}')
            
            project_response, project_id = create_project(name=nome_sistema, identifier=meu_identificador, description=description, public=False, active=True, parent_id=None, file_paths=arquivos_baixados)
            
            if project_id is None:
                salvar_erro_banco(ticket_id, f'{project_response}')
                logger.error(f"Erro ao criar projeto: {project_response}")

            if db_id:
                try:
                    conn = pymysql.connect(
                        host=HOST_MYSQL, port=PORT_MYSQL, user=USER_MYSQL,
                        password=PASS_MYSQL, database=SCHEMA_MYSQL
                    )
                    with conn.cursor() as cursor:
    
                        cursor.execute("""
                            UPDATE integracao_chamados 
                            SET eh_novo_projeto = TRUE, tipo_op = 'project', prioridade_op = %s, status_integracao = 'sucesso', id_op = %s
                            WHERE id = %s
                        """, (prioridade, project_id, db_id))
                    conn.commit()
                    conn.close()
                except Exception as e:
                    logger.error(f"Erro ao atualizar BD para novo projeto: {e}")
                    salvar_erro_banco(ticket_id, f"Erro ao atualizar BD para novo projeto: {e}")
            
        else:
            print("Decisão: CRIAR PACOTE DE TRABALHO EM PROJETO EXISTENTE")
            
            tipo_wp_id = 1 # 1 = Tarefa (padrão)
            tipo_wp_nome = "Tarefa"
            
            # Regras de tipo de WP por categoria
            if categoria_demanda in ["Erro em sistema", "Falha em automação", "Problema em integração", "Sistema fora do ar"]:
                tipo_wp_id = 7 # Bug
                tipo_wp_nome = "Bug"
            elif categoria_demanda in ["Evolução de funcionalidade", "Ajuste de interface", "Integração entre sistemas"]:
                tipo_wp_id = 4 # Funcionalidade
                tipo_wp_nome = "Funcionalidade"
            elif categoria_demanda in ["Otimização de performance", "Refatoração"]:
                tipo_wp_id = 1 # Tarefa
                tipo_wp_nome = "Tarefa"
            
            try:
                # Tenta extrair ID do projeto do nome "12 - Sistema X"
                project_id_str = nome_sistema.split('-')[0].strip()
                if project_id_str.isdigit():
                    project_id = int(project_id_str)
                    subject = f"[{tipo_wp_nome}] {categoria_demanda}" if categoria_demanda != "N/A" else f"[{tipo_wp_nome}] Nova Solicitação"
                    
                    description = f"**Solicitante:** {nome_autor} (ID: {id_autor})\n\n"
                    description += f"**Descrição:**\n{descricao_projeto}\n\n"
                    description += f"**Impacto no setor solicitante:** {impacto_solicitante}\n"
                    description += f"**Impacto em outros setores:** {impacto_outros}\n"
                    description += f"**Chamado GLPI:** {url_chamado}\n"
                    if anexos and len(anexos) > 0:
                        description += f"**Anexos:** {len(anexos)} anexo(s) na aba de arquivos\n"
                    
                    
                    print(f"Projeto Pai (ID): {project_id}")
                    print(f"Tipo de WP: {tipo_wp_nome} (ID: {tipo_wp_id})")
                    print(f"Título: {subject}")
                    print(f"Prioridade: {prioridade}")
                    print(f"Descrição que será enviada:\n{description}")
                    
                    logger.info(f"Decisão: Criar Work Package ({tipo_wp_nome}) no projeto {project_id}")
                    
                    # TODO: Descomentar quando quiser realizar as criações na API
                    wp_response, atribuido_op = create_work_package(
                        project_id=project_id,
                        subject=subject,
                        priority=prioridade,
                        description=description,
                        type_id=tipo_wp_id,
                        notify=False,
                        file_paths=arquivos_baixados
                    )
                    
                    
                    if db_id:
                        try:
                            conn = pymysql.connect(
                                host=HOST_MYSQL, port=PORT_MYSQL, user=USER_MYSQL,
                                password=PASS_MYSQL, database=SCHEMA_MYSQL
                            )
                            with conn.cursor() as cursor:
                                if wp_response and wp_response.get('id'):
                                    cursor.execute("""
                                        UPDATE integracao_chamados 
                                        SET eh_novo_projeto = FALSE, tipo_op = 'work_package', categoria_op = %s, prioridade_op = %s, status_integracao = 'sucesso', id_op = %s, atribuido_op = %s
                                        WHERE id = %s
                                    """, (tipo_wp_nome, prioridade, wp_response.get('id'), atribuido_op, db_id))
                                else:
                                    cursor.execute("""
                                        UPDATE integracao_chamados 
                                        SET eh_novo_projeto = FALSE, tipo_op = 'work_package', categoria_op = %s, prioridade_op = %s, status_integracao = 'erro', mensagem_erro = 'Erro ao criar Work Package', atribuido_op = %s
                                        WHERE id = %s
                                    """, (tipo_wp_nome, prioridade, atribuido_op, db_id))
                            conn.commit()
                            conn.close()
                        except Exception as e:
                            logger.error(f"Erro ao atualizar chamado {ticket_id} no BD: {e}")
                            salvar_erro_banco(ticket_id, f"Erro ao atualizar chamado no BD: {e}")
                else:
                    msg_erro = f"Não foi possível extrair o ID do projeto do sistema: '{nome_sistema}'"
                    print(f"ERRO: {msg_erro}")
                    logger.error(f"ERRO: {msg_erro}")
                    salvar_erro_banco(ticket_id, msg_erro)
            except Exception as e:
                print(f"Erro no processamento do Work Package: {e}")
                logger.error(f"Erro ao processar criação de Work Package: {e}")
                salvar_erro_banco(ticket_id, f"Erro ao processar criação de Work Package: {e}")

        print("--------------------------------------------------\n")

    kill_glpi_api_session(session_token)
    return {"status": "OK"}


### Parte do COigo do Gabriel em que Recebe Post do Open project de priridade mudada e adiciona a nova prioridade no banco de dados e atualiza o GLPI

def membership_tem_grupo(membership_data: dict, grupo_alvo: str) -> bool:
    if membership_data is None:
        return False

    def busca_recursiva(valor) -> bool:
        if isinstance(valor, dict):
            return any(busca_recursiva(v) for v in valor.values())
        if isinstance(valor, list):
            return any(busca_recursiva(item) for item in valor)
        if isinstance(valor, str):
            return grupo_alvo in valor
        return False

    return busca_recursiva(membership_data)

@app.api_route('/api/', methods=['GET', 'POST'])
async def processar_atualizacao_de_pacote_de_trabalho(request: Request):
    """Endpoint que recebe o webhook de atualização de pacote de trabalho do OpenProject. Avalia a prioridade no OpenProject e compara com o GLPI, se for diferente, atualiza no banco de dados e na API do GLPI.

    Returns:
        400: O tipo (work_package, project, ...) não é suportado.
        200: OK.
    """    
    try:
        data = await request.json()
    except Exception:
        data = None

    print(data)
    if data is None:
        return JSONResponse(content={"error": "Invalid JSON or no JSON received"}, status_code=400)
    
    tipo_op = data.get("action").split(":")[0].strip()
    
    membership_href = data.get("work_package").get("_embedded").get("project").get("_links").get("memberships").get("href")
    url = f"{OPENPROJECT_URL}{membership_href}"

    membership = requests.get(url, auth=('apikey', API_KEY))
    membership_data = membership.json() if membership.ok else None

    possui_inteligencia_artificial = membership_tem_grupo(membership_data, "Inteligência Artificial")
    print(f"Membership possui Inteligência Artificial: {possui_inteligencia_artificial}")
    if not possui_inteligencia_artificial:
        return JSONResponse(content="OK", status_code=200)
    
        
    match tipo_op:
        case "work_package":    
            priority__id = data.get("work_package").get("_embedded").get("priority").get("id")
            
            work_package_id = data.get("work_package").get("id")
                        
            query = "SELECT " \
                    "prioridade_op " \
                "FROM " \
                    "integracao_chamados " \
                "WHERE " \
                    "id_op = %s " \
                    f"AND tipo_op = '{tipo_op}' "
            
            insert_query = """
                INSERT INTO integracao_chamados (id_op, tipo_op, prioridade_op)
                VALUES (%s, 'work_package', %s)
            """
            
            update_query = """
                UPDATE integracao_chamados
                SET prioridade_op = %s
                WHERE id_op = %s AND tipo_op = 'work_package'
            """
            
            chamado_id_query = "select id_glpi from integracao_chamados where id_op = %s and tipo_op = 'work_package'"
            
            with pymysql.connect(
                host=HOST_MYSQL,
                port=int(PORT_MYSQL),
                user=USER_MYSQL,
                password=PASS_MYSQL,
                database=SCHEMA_MYSQL
            ) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (work_package_id,))
                    result = cursor.fetchone()
                    print(result)
                    if result:
                        prioridade_op = result[0]
                        print(f"Prioridade OP: {prioridade_op}")
                        if prioridade_op != priority__id:
                            cursor.execute(update_query, (priority__id, work_package_id))
                            conn.commit()
                            # Atualizar o chamado na API do GLPI

                            # [ 1 - Muito Baixa, 2 - Baixa, 3 - Média, 4 - Alta, 5 - Muito Alta, 6 - Crítica ] -- IDS Prioridade GLPI
                            # [ 16 - Muito Baixa, 7 - Baixa, 8 - Média, 9 - Alta, 15 - Muito Alta, 10 - Crítica ] -- IDS Prioridade OpenProject
                            priority_map_op_to_glpi = {
                                16: 1,  # Muito Baixa
                                7: 2,   # Baixa
                                8: 3,   # Média
                                9: 4,   # Alta
                                15: 5,  # Muito Alta
                                10: 6,  # Crítica
                            }

                            id_chamado = cursor.execute(chamado_id_query, (work_package_id,))
                            id_chamado = cursor.fetchone()[0]
                            print(f"ID do chamado no GLPI: {id_chamado}")

                            prioridade_glpi = priority_map_op_to_glpi.get(priority__id)
                            if prioridade_glpi is None:
                                print(f"Prioridade OP sem mapeamento: {priority__id}")
                            else:
                                response = glpi.update_ticket_priority(id_chamado, prioridade_glpi)
                            
                            print(f"Prioridade OP atualizada: {priority__id}")
                        else:
                            print("Prioridade OP não alterada")
                    # else:
                    #     cursor.execute(insert_query, (work_package_id, priority__id))
                    #     conn.commit()
                    #     print(f"Prioridade OP inserida: {priority__id}")  
                        
        case _:
            return JSONResponse(content={"error": "Tipo não suportado"}, status_code=400)
        
    return JSONResponse(content="OK", status_code=200)

if __name__ == '__main__':
    uvicorn.run("novo_chamado:app", host='0.0.0.0', port=30112, reload=True)
