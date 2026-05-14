import os
import requests
from dotenv import load_dotenv
import json
import pymysql

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# URL base da API do OpenProject (adicione OPENPROJECT_URL no seu .env ou substitua aqui)
OPENPROJECT_URL = os.getenv('OPENPROJECT_URL')
API_URL = f"{OPENPROJECT_URL}/api/v3/projects"

# Token de acesso (Bearer Token) pegando do .env
API_KEY = os.getenv('APIKEY_OPEN')

def get_work_package_types():
    """
    Busca todos os Tipos de Pacotes de Trabalho (Types) globais disponíveis no OpenProject.
    Útil para descobrir o 'type_id' .
    """
    if not API_KEY or not OPENPROJECT_URL:
        print("Erro: OPENPROJECT_URL ou APIKEY_OPEN não encontradas.")
        return None

    url = f"{OPENPROJECT_URL}/api/v3/types"
    headers = {"Content-Type": "application/json"}

    print(f"Buscando Tipos de Pacote de Trabalho em: {url}")
    
    try:
        response = requests.get(url, headers=headers, auth=('apikey', API_KEY))
        response.raise_for_status()
        data = response.json()
        
        print("\n--- Tipos de Pacote de Trabalho Encontrados ---")
        # print(data)
        return data

    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição: {e}")
        return None


import requests
import os
import json

# Certifique-se de que as variáveis de ambiente ou globais estejam definidas
OPENPROJECT_URL = os.getenv('OPENPROJECT_URL')
API_KEY = os.getenv('APIKEY_OPEN')

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

def create_project(name, identifier, description="", public=False, active=True, parent_id=None):
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
            add_project_member(project_id, user_id, 3) # adiciona como membro do projeto 

        user_adm = [11]
        for user_id in user_adm:
            add_project_member(project_id, user_id, 5) # adiciona como administrador do projeto
        
        print(f"Sucesso! Projeto criado com ID: {project_id}")
        print(f"Link: {OPENPROJECT_URL}/projects/{identifier}")
        
        return data

    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição: {e}")
        if e.response is not None and e.response.text:
            print(f"Detalhes do erro do servidor: {e.response.text}")
        return None

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
        
        return data

    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição: {e}")
        if e.response is not None and e.response.text:
            print(f"Detalhes do erro do servidor: {e.response.text}")
        return None

def get_active_projects():
    """
    Faz um GET na API do OpenProject para listar os projetos ativos.
    """
    if not API_KEY:
        print("Erro: APIKEY_OPEN não encontrada no arquivo .env")
        return

    headers = {
        # "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # Filtro para trazer apenas projetos ativos, baseado na documentação do OpenProject
    filters = '[{"active": {"operator": "=", "values": ["t"]}}]'
    
    print(f"Fazendo requisição para: {API_URL}")
    response = None
    try:
        response = requests.get(API_URL, headers=headers, auth=('apikey', API_KEY),allow_redirects=False)
        response.raise_for_status() # Lança exceção para erros HTTP
        
        data = response.json()

        print("Projetos encontrados com sucesso!\n")
        # print(data)
        # para cada projeto, trazer o id, nome e descrição 
        
        elements = data.get('_embedded', {}).get('elements')
        if elements is not None:
            for project in elements:
                desc = project.get('description', {}).get('raw', 'Sem descrição')
                print(f"ID: {project.get('id')} | Nome: {project.get('name')} | Descrição: {desc}")

                # if project.get('id') == 21:
                #     # print(project)
                #     create_work_package(project.get('id'), "Erro de chamada de api", "Erro de chamada de api durante execuções", type_id=7, notify=False)
        else:
            print("Nenhum projeto encontrado ou formato de resposta inesperado.")
            
    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição: {e}")
        if response is not None and response.text:
            print(f"Detalhes do erro: {response.text}")

if __name__ == "__main__":
    # get_active_projects()
    # get_work_package_types()
    # create_work_package(12, "Erro de chamada de api 2", 10, "Erro de chamada de api durante execuções 2", type_id=7, notify=False, file_paths=["/DESENVOLVEDORES/pedro/glpi_open/docs/api_openproject.md"])
    # create_project(name='novo projeto 4', identifier='novo-projeto4', description="Teste de criação de projeto via api openproject.", public=False, active=True, parent_id=None)
    # inserir anexos na criação do projeto  