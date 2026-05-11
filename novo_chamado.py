import logging
from datetime import datetime
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import base64
import httpx
import requests

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

# Handler para gravar o log da API em arquivo
api_handler = logging.FileHandler(os.path.join(LOGS_DIR, 'api.log'), encoding='utf-8')
# antes verificar se api.log e chamaados_dados.log existem, se não existir criar os dois arquivos e colocar dentro de LOGS_DIR

if not os.path.exists(os.path.join(LOGS_DIR, 'api.log')):
    with open(os.path.join(LOGS_DIR, 'api.log'), 'w') as f:
        f.write('')
if not os.path.exists(os.path.join(LOGS_DIR, 'chamados_dados.log')):
    with open(os.path.join(LOGS_DIR, 'chamados_dados.log'), 'w') as f:
        f.write('')
        
    print(f'criado os arquivos {os.path.join(LOGS_DIR, "api.log")} e {os.path.join(LOGS_DIR, "chamados_dados.log")}')

api_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
logger.addHandler(api_handler)

# Logger específico para os dados dos chamados
dados_logger = logging.getLogger('dados_chamado')
dados_logger.setLevel(logging.INFO)
dados_handler = logging.FileHandler(os.path.join(LOGS_DIR, 'chamados_dados.log'), encoding='utf-8')
dados_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
dados_logger.addHandler(dados_handler)
dados_logger.propagate = False

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
    - file_paths (list): (Opcional) Lista de caminhos absolutos ou relativos dos arquivos a serem anexados.
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

    if type_id:
        payload["_links"] = {
            "type": {
                "href": f"/api/v3/types/{type_id}"
            }
        }

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


@app.api_route('/teste', methods=['GET', 'POST'])
async def tudo(request: Request):
    data = await request.json()
    print(data)
    
    if data is None:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON or no JSON received"})
        
    return jsonify("OK"), 200

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
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON or no JSON received"})

    if data is None:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON or no JSON received"})

    if data.get('ticket').get('solution').get('approval').get('description') != 'Solução aprovada':
        # solução rejeitada devera buscar o numero do chamado no glpi e buscar no mysql qual o projeto ou pacote de trabalho para reabrir

        ticket_id = data.get('ticket').get('id')
        
    

    ticket = data.get('ticket', {})
    
    # Tratamento caso ticket venha como outro tipo que não dict
    if not isinstance(ticket, dict):
        ticket = {}

    action = ticket.get('action')
    ticket_id = ticket.get('id')
    title = ticket.get('title', '')
    category = ticket.get('category', '')
    author = data.get('author', {})
    id_autor = author.get('id')
    nome_autor = author.get('name')

    log_msg = f"/\taction: {action}\tticket_id: {ticket_id}"
    logger.info(log_msg)
    
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
        except json.JSONDecodeError:
            print(f"❌ Erro ao decodificar JSON para o ticket {ticket_id}")
            print(response.text)
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
                        except json.JSONDecodeError:
                            print(f"⚠️ Aviso: Não foi possível ler o JSON de metadados do doc {doc_id}")
                    
    
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
                        
                        try:
                            logger.error(erro_msg)
                        except NameError:
                            pass 

    except Exception as e:
        print(f"❌ Erro ao processar anexos: {e}")
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

        # depois de extrair os dados do chamado, precisa inserir no banco de dados na tabela integracao_op_glpi.
        # o ddl da tabela esta em schema.sql
        

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
            
            print(f"Prioridade: {prioridade}")
            print(f"Descrição que será enviada:\n{description}")
            logger.info(f"Decisão: Criar Novo Projeto. Sistema: {nome_sistema}")
            
            # TODO: Descomentar e implementar quando a função create_project estiver pronta
            # create_project(name=nome_sistema, priority=prioridade, description=description)
            
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
                    url_chamado = f"https://glpi.brggeradores.com.br/index.php?redirect=ticket_{ticket_id}"
                    subject = f"[{tipo_wp_nome}] {categoria_demanda}" if categoria_demanda != "N/A" else f"[{tipo_wp_nome}] Nova Solicitação"
                    
                    description = f"**Solicitante:** {nome_autor} (ID: {id_autor})\n\n"
                    description += f"**Descrição:**\n{descricao_projeto}\n\n"
                    description += f"**Impacto no setor solicitante:** {impacto_solicitante}\n"
                    description += f"**Impacto em outros setores:** {impacto_outros}\n"
                    description += f"**Chamado GLPI:** {url_chamado}\n"
                    
                    print(f"Projeto Pai (ID): {project_id}")
                    print(f"Tipo de WP: {tipo_wp_nome} (ID: {tipo_wp_id})")
                    print(f"Título: {subject}")
                    print(f"Prioridade: {prioridade}")
                    print(f"Descrição que será enviada:\n{description}")
                    
                    logger.info(f"Decisão: Criar Work Package ({tipo_wp_nome}) no projeto {project_id}")
                    
                    # TODO: Descomentar quando quiser realizar as criações na API
                    create_work_package(
                        project_id=project_id,
                        subject=subject,
                        priority=prioridade,
                        description=description,
                        type_id=tipo_wp_id,
                        notify=False,
                        file_paths=arquivos_baixados
                    )
                else:
                    print(f"ERRO: Não foi possível extrair o ID do projeto do sistema: '{nome_sistema}'")
                    logger.error(f"ERRO: Não foi possível extrair o ID do projeto a partir de: {nome_sistema}")
            except Exception as e:
                print(f"Erro no processamento do Work Package: {e}")
                logger.error(f"Erro ao processar criação de Work Package: {e}")

        print("--------------------------------------------------\n")

    return {"status": "OK"}

if __name__ == '__main__':
    uvicorn.run("novo_chamado:app", host='0.0.0.0', port=7047, reload=True)
