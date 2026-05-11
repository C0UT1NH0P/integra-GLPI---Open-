from flask import Flask, request, jsonify, Response, make_response
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import os, re
import mysql.connector
from datetime import datetime
import json
from threading import Thread
import mysql.connector
import queue
import logging
from logging.handlers import RotatingFileHandler
# from api_cnpj import receita_api

# 1. Obtenha o logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG) # Defina o nível de log no logger principal

# 2. Crie um formatador para padronizar a aparência dos logs
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# 3. Crie o handler para salvar em arquivo com rotação (RotatingFileHandler)
file_handler = RotatingFileHandler(
    "api.log", 
    maxBytes=1024*1024, # 1 MB
    backupCount=5
)
file_handler.setFormatter(formatter) # Aplique o formatador ao handler

# 4. Crie o handler para exibir no console (StreamHandler)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter) # Aplique o mesmo formatador

# 5. Adicione os handlers ao logger
# Evita adicionar handlers duplicados se o script for importado várias vezes
if not logger.handlers:
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

import mysql.connector

load_dotenv(override=True) 

AUTOMACOES_DB=os.environ.get("AUTOMACOES_DB")
AUTOMACOES_HOST=os.environ.get("AUTOMACOES_HOST")
AUTOMACOES_PORT=os.environ.get("AUTOMACOES_PORT")
AUTOMACOES_USER=os.environ.get("AUTOMACOES_USER")
AUTOMACOES_PASS=os.environ.get("AUTOMACOES_PASS")

API_PRECO_VENDA_URL=os.environ.get("API_PRECO_VENDA_URL")

if not AUTOMACOES_DB or not AUTOMACOES_HOST \
    or not AUTOMACOES_PORT or not AUTOMACOES_USER \
    or not AUTOMACOES_PASS:
    raise EnvironmentError("Variáveis de ambiente relativas ao banco de dados de automações ausentes no .env")


pool = mysql.connector.pooling.MySQLConnectionPool(
    pool_name="botGLPI",
    pool_size=10,
    user=os.getenv('GLPI_MYSQL_USER'),
    password=os.getenv('GLPI_MYSQL_PASSWORD'),
    host=os.getenv('GLPI_MYSQL_HOST'),
    port=os.getenv('GLPI_MYSQL_PORT'),
    database=os.getenv('GLPI_MYSQL_DATABASE'),
    collation='utf8mb4_general_ci' # especificando o collation para evitar erro de codificação
)

app = Flask(__name__)

def send_update_protheus_async(data):
    try:
        send_update_protheus(data)
    except Exception as e:
        print(f"Erro ao processar send_update_protheus: {e}")
        logger.error(f"{datetime.now()} - send_update_protheus_async - Erro: {e}", exc_info=True)

def send_ticket_solution_async(data):
    try:
        send_ticket_solution(data)
    except Exception as e:
        print(f"Erro ao processar send_ticket_solution: {e}")
        logger.error(f"{datetime.now()} - send_ticket_solution - Erro: {e}", exc_info=True)

from bs4 import BeautifulSoup

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

def extrair_dados_multiplas_tabelas_html(html_content: str) -> dict:
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
    
    dados_extraidos = {}

    # Encontra todas as linhas <tr> em todas as tabelas (suporta múltiplas tabelas no HTML)
    linhas = soup.find_all('tr')

    # Itera sobre cada linha
    for linha in linhas:
        # Encontra todas as células <td> na linha
        celulas = linha.find_all('td')

        # Verifica se a linha tem pelo menos 2 células (chave e valor)
        if len(celulas) >= 2:
            # Extrai o texto da primeira célula como chave
            # Usa get_text(" ", strip=True) para preservar espaços internos quando necessário
            chave = celulas[0].get_text(" ", strip=True)
            # Normaliza/remova dois-pontos finais e espaços
            chave = chave.rstrip(':').strip()

            # Extrai o texto da segunda célula como valor
            valor = celulas[1].get_text(" ", strip=True)

            # Adiciona ao dicionário apenas se a chave não estiver vazia
            if chave:
                dados_extraidos[chave] = valor
                
    return dados_extraidos

def grava_chamado_cadastro_fornecedor(id):
    """Registra no banco de dados de automações um novo chamado de cadastro de fornecedor."""
    # dados = extrair_dados_de_tabela_html(data.get("ticket", []).get("content", "Conteúdo"))
        
    # dados["Chamado"] = data.get("ticket", []).get("id", [])

    try:
        query = f"INSERT INTO `automacoes`.`chamados_cadastro_fornecedor` (chamado, analisado) " \
                f"VALUES (%s, 0);"
        
        values = [id]

        cnx = mysql.connector.connect(
            database=AUTOMACOES_DB, 
            host=AUTOMACOES_HOST, 
            port=AUTOMACOES_PORT, 
            user=AUTOMACOES_USER, 
            password=AUTOMACOES_PASS
        )
    
        with cnx.cursor() as cursor:
            cursor.execute(query, values)
            cnx.commit()
    except Exception as e:
        cnx.rollback()
        print(e)
        logger.error(e)
    finally:
        cnx.close()


@app.route('/', methods=['GET', 'POST'])
def tudo():
    data = request.get_json()
    print(data)

    if data is None:
        return jsonify({"error": "Invalid JSON or no JSON received"}), 400
        
    return jsonify("OK"), 200

@app.route('/webhook', methods=['POST'])
def handle_glpi_webhook():
    # print('entrou em /webhook')
    data = request.get_json()
    # print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "\tWEBHOOK RECEBIDO\t", data)
    if data is None:
       return jsonify({"error": "Invalid JSON or no JSON received"}), 400

    print(f"{datetime.now()}\t/webhook\taction: {data.get('ticket').get('action')}\tticket_id: {data.get('ticket').get('id')}")
    

    if str(data.get("ticket", []).get("title")).startswith("Cadastro de Cliente") and data.get('ticket', []).get('action', '') == "Novo chamado":
        dados_html = extrair_dados_multiplas_tabelas_html(data.get("ticket", []).get("content", []))
        print(dados_html)
        cnpj = re.sub(r'\D', '', dados_html['CNPJ'])

        # mensagem_glpi = receita_api(cnpj, '0101', data.get("ticket", []).get("id"))
        
        session_token = init_glpi_api_session()
        
        # Passe o id diretamente (antes estava sendo passado como set `{id}` o que causa erro de serialização)
        adicionar_comentario_chamado_glpi(session_token, data.get('ticket').get('id'), mensagem_glpi)

        kill_glpi_api_session(session_token)
        
    elif str(data.get("ticket", []).get("title")).startswith("Cadastro Fornecedor") and data.get('ticket', []).get('action', '') == "Novo chamado":
        dados_html = extrair_dados_de_tabela_html(data.get("ticket", []).get("content", []))
            
        if isinstance(dados_html, list) and len(dados_html) > 0:
            dados_html = dados_html[0]

        novo_cadastro = dados_html['Novo Cadastro ou Alteração de algum já existente?']
        if novo_cadastro != 'ALTERAÇÃO': 
            id = data.get("ticket", []).get("id")
            grava_chamado_cadastro_fornecedor(id)
            
    elif str(data.get("ticket", []).get("title")).startswith("Solicitação de Preço de Venda"):
        
        if str(data.get('ticket', []).get('action', '')) == "Resposta de pedido de validação" \
            and str(data.get("validations", []).get("status")) == "Concedida":
                
            # descricao = data.get("ticket", []).get("solution", []).get("approval", []).get("description", "ERRO AO OBTER DESCRIÇÂO")
            descricao = data.get("validations", []).get("commentsubmission", "ERRO AO OBTER DESCRIÇÂO")
            id_chamado = data.get("ticket", []).get("id")
            
            body = {
                "id_chamado": f"{id_chamado}",
                "descricao": f"{descricao}"
            }
            
            response = requests.post(f"{API_PRECO_VENDA_URL}/validation_teste", json=body)
            
            response.raise_for_status()
            
            try:
                print(response.json())
            except:
                print(response.text)
                
            
        elif str(data.get('ticket', []).get('action', '')) == "Novo chamado":
            id_chamado = data.get("ticket", []).get("id")
            body = {
                "id_chamado": id_chamado
            }
            response = requests.post(f"{API_PRECO_VENDA_URL}/ticket_teste", json=body)
            
            response.raise_for_status()
            
            try:
                print(response.json())
            except:
                print(response.text)

        elif str(data.get('ticket', []).get('action', '')) == "Novo acompanhamento" and str(data.get('ticket', []).get('lastupdater', '')) == 'Gabriel Brito' or str(data.get('ticket', []).get('lastupdater', '')) == 'Pedro Coutinho':
            
            id_chamado = data.get("ticket", []).get("id")
            ticket = data.get("ticket", {})
            solution = ticket.get("solution", {})
            descricao = (
                solution.get("approval", {}).get("description")
                or solution.get("description")
                or "ERRO AO OBTER DESCRIÇÃO"
            )
            body = {
                "id_chamado": id_chamado,
                "descricao": descricao
            }
            
            response = requests.post(f"{API_PRECO_VENDA_URL}/resposta/cotacao", json=body)
            
            response.raise_for_status()
            
            try:
                print(response.json())
            except:
                print(response.text)
        


    try:
        if data.get('ticket').get('observergroups') == "notificacao_protheus" and (data.get('ticket').get('action') == "Novo chamado" or data.get('ticket').get('action') == "Chamado solucionado") and data.get('author').get('id') in ['2', '183', '233', '329', '137']:       
            # Inicia a thread e responde imediatamente
            thread = Thread(target=send_update_protheus_async, args=(data,))
            thread.start()

            return jsonify("Request received"), 200

        elif data.get('ticket').get('lastupdater') != data.get('author').get('name') or data.get('ticket').get('action') == "Novo chamado" or data.get('ticket').get('action') == 'Pesquisa de satisfação':
        
            # if data.get('author').get('mobile') == '556281321017' or data.get('author').get('mobile') == '556286342844':
            send_message(data)
        elif data.get('ticket').get('lastupdater') == data.get('author').get('name'): # Mensagem do autor Enviar para o técnico
            # print(f"------ {data.get('author').get('name')} ------\n")
        
            # print(f"{data}\n")
            id_chamado = data.get('ticket').get('id')
            nome_tecnico, telefone_tecnico = busca_dados_tecnico(id_chamado)
            mensagem_do_autor(nome_tecnico, telefone_tecnico, data)

            # return jsonify("No message sent, last updater is the same as author."), 200


    except KeyError as e:
        logger.error(f"{datetime.now()} - handle_glpi_webhook - Erro: {e}", exc_info=True)
        return jsonify({"error": f"Missing key: {e}"}), 400
    

    return jsonify("received_data"), 200

@app.route('/answers', methods=['POST'])
def handle_user_list_response():
    print("handle_user_list_response\n")
    try:
        data = request.get_json()
        print(f'data: {data}\n')
        # action = data.get('data').get('message').get('listResponseMessage').get('contextInfo')['quotedMessage']['listMessage'].get('title').replace("*", "").replace("_","").lower()
        print(f"{datetime.now()}\t/answers\taction: {data.get('ticket').get('action')}\tticket_id: {data.get('data').get('message').get('listResponseMessage').get('singleSelectReply').get('selectedRowId')}")
        # print(data)
        
        if data is None:
            print("Data is None")
            return jsonify({"error": "Invalid JSON or no JSON received"}), 400

        if data.get('data').get('messageType') != 'listResponseMessage':
            print("Message Type <> listResponseMessage")
            return jsonify("received_data"), 200

        id_mensagem = data.get('data').get('message').get('listResponseMessage').get('contextInfo').get('stanzaId')
        # print(f"id_mensagem: {id_mensagem}")

        sql = f"""SELECT id_mensagem FROM respostas WHERE id_mensagem = '{id_mensagem}'"""
        with pool.get_connection() as con:
            with con.cursor() as cursor:
                cursor.execute(sql)
                result = cursor.fetchone()
                
                if not result:
                    send_users_ticket_validation(data)
                    values = [str(data.get('data').get('key').get('id')), str(id_mensagem), '', str(datetime.now()), str(data.get('data').get('message').get('listResponseMessage').get('title'))]
                    sql = f"""INSERT INTO u629942907_glpi.respostas (`id_resposta`, `id_mensagem`, `conteudo`, `data_hora`, `tipo`)
                    VALUES (%s, %s, %s, %s, %s)"""

                    try:
                        cursor.execute(sql, values)
                        con.commit()
                        
                    except mysql.connector.Error as e:
                        print(f"{datetime.now()}\terro de conexao MySQL: {e}")
                    except Exception as e:
                        print(f"{datetime.now()}\terro: {e}")
                    # finally:
                    #     exit()
    except Exception as e:
        logger.error(f"{datetime.now()} - handle_user_list_response - Erro: {e}", exc_info=True)
        raise e
    
        
    
    return jsonify("received_data"), 200

def send_update_protheus(data):
    sql = f"SELECT CONCAT(u.firstname, ' ', u.realname) AS nome, u.mobile FROM glpi_groups_users AS gu LEFT JOIN glpi_users AS u ON u.id = gu.users_id WHERE gu.groups_id = '{os.getenv('GLPI_USER_GROUP_ID')}';"
    with pool.get_connection() as con:
        with con.cursor() as cursor:
            cursor.execute(sql)
            usuarios = cursor.fetchall()

    for usuario in usuarios:
        if data.get('ticket').get('action') == "Novo chamado":
            payload = {
                "number": f"{usuario[1]}",
                "text":f"""Olá, {usuario[0]}!\n\n{clean_html(data.get('ticket').get('content'))}""",
                "delay": 2000,
                "linkPreview": True,
                "mentionsEveryOne": False,
                "quoted": {
                    "key": {
                        "fromMe": True,
                        "type":'Atualização no Protheus',
                        "id": ""
                    }
                }
            }
        else:
            # data.get('ticket').get('action') == "Chamado solucionado"
            payload = {
                "number": f"{usuario[1]}",
                "text":f"""Olá, {usuario[0]}!\n\n{clean_html(data.get('ticket').get('solution').get('description'))}""",
                "delay": 2000,
                "linkPreview": True,
                "mentionsEveryOne": False,
                "quoted": {
                    "key": {
                        "fromMe": True,
                        "type":'Atualização no Protheus',
                        "id": ""
                    }
                }
            }

        enqueue_chat(payload)

def init_glpi_api_session():
   glpiApiHeaders = {
        "Authorization": f"{os.getenv('GLPI_AUTH')}",
        "App-Token": f"{os.getenv('GLPI_APP_TOKEN')}",
        "Content-Type": "application/json"
    }

   url = f"{os.getenv('GLPI_API_BASE_URL')}/initSession/"

   response = requests.request("GET", url, headers=glpiApiHeaders)
   return response.json().get('session_token')

def kill_glpi_api_session(session_token):
   headers = {
      "Session-Token": f"{session_token}",
      "App-Token": f"{os.getenv('GLPI_APP_TOKEN')}",
      "Content-Type": "application/json"
   }

   url = f"{os.getenv('GLPI_API_BASE_URL')}/killSession"

   response = requests.request("GET", url, headers=headers)

def send_users_ticket_validation(data):
    print("entrou em send_users_ticket_validation\n")
    session_token = init_glpi_api_session()
    # print(f"Sessão GLPI iniciada. session_token: {session_token}\n")
    ticket_id = data.get('data').get('message').get('listResponseMessage').get('singleSelectReply').get('selectedRowId')
    resposta_chamado = data.get('data').get('message').get('listResponseMessage').get('title')

    if resposta_chamado == 'Sim':
        # print("resposta_chamado == 'Sim'")
        payload = {
            "input":{
                "id":f"{ticket_id}",
                "status":6
            }
        }
    if resposta_chamado == "Não":
        payload = {
            "input":{
                "id":f"{ticket_id}",
                "status":2
            }
        }


    headers = {
      "Session-Token": f"{session_token}",
      "App-Token": f"{os.getenv('GLPI_APP_TOKEN')}",
      "Content-Type": "application/json"
   }

    url = f"{os.getenv('GLPI_API_BASE_URL')}/Ticket/{ticket_id}"
    
    # response = requests.request("PUT", url, headers=headers, json=payload)
    try:
        response = requests.request("PUT", url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()  # levanta erro para códigos 4xx/5xx
    except requests.Timeout:
        print("Erro: timeout ao tentar acessar a API.")
        logger.error(f"{datetime.now()} - send_users_ticket_validation - Erro: timeout ao tentar acessar a API.", exc_info=True)
    except requests.RequestException as e:
        print(f"Erro de requisição: {e}")
        logger.error(f"{datetime.now()} - send_users_ticket_validation - Erro: {e}", exc_info=True)
    

    kill_glpi_api_session(session_token)

def clean_html(texto):
    texto = texto.replace("<br>", "\n").replace("<li>", "   * ")
    clean = BeautifulSoup(texto, "html.parser")
    return clean.get_text()

def mensagem_do_autor(nome_tecnico, telefone_tecnico, data):
    payload = {
                "number": f"{telefone_tecnico}",
                "text":f"""*_RESPOSTA DO AUTOR_*\n\nOlá, {nome_tecnico}!\n\n{data.get('author').get('name')}, autor do chamado nº {data.get('ticket').get('id')} - {data.get('ticket').get('title')} enviou uma nova mensagem. Acesse o GLPI para visualizar: {data.get('ticket').get('url')}""",
                "delay": 2000,
                "linkPreview": True,
                "mentionsEveryOne": False,
                "quoted": {
                    "key": {
                        "fromMe": True,
                        "type":'Mensagem do autor',
                        "id": ""
                    }
                }
            }
    enqueue_chat(payload)

def send_message(data):
    # print("Entrou em send_message")
    match data.get('ticket').get('action'):
        
        case 'Novo chamado':
            payload = {
                "number": f"{data.get('author').get('mobile')}",
                "text":f"""*_NOVO CHAMADO_*\n\nOlá, {data.get('author').get('name')}!\n\nRecebemos seu chamado nº {data.get('ticket').get('id')} - {data.get('ticket').get('title')}:\n\n\tAs atualizações em seu chamado serão enviadas em seu Whatsapp.\n\nPara acompanhar acesse o link: {data.get('ticket').get('url')}""",
                "delay": 2000,
                "linkPreview": True,
                "mentionsEveryOne": False,
                "quoted": {
                    "key": {
                        "fromMe": True,
                        "type":'Novo chamado',
                        "id": ""
                    }
                }
            }

            enqueue_chat(payload)

        case 'Novo acompanhamento':
            if clean_html(data.get('ticket').get('solution').get('approval').get('description')) != 'Solução aprovada':
                if data.get('documents') != '':
                    text = f"""*_NOVO ACOMPANHAMENTO_*\n\nOlá, {data.get('author').get('name')}!\n\n{data.get('ticket').get('action')} em seu chamado nº {data.get('ticket').get('id')} - {data.get('ticket').get('title')}:\n\n\t*{data.get('ticket').get('solution').get('approval').get('author')}:* {clean_html(data.get('ticket').get('solution').get('approval').get('description'))}\n\nHá um documento associado a essa atualização, para acompanhar acesse o link: {data.get('ticket').get('url')}"""
                else:
                    text = f"""*_NOVO ACOMPANHAMENTO_*\n\nOlá, {data.get('author').get('name')}!\n\n{data.get('ticket').get('action')} em seu chamado nº {data.get('ticket').get('id')} - {data.get('ticket').get('title')}:\n\n\t*{data.get('ticket').get('solution').get('approval').get('author')}:* {clean_html(data.get('ticket').get('solution').get('approval').get('description'))}\n\nPara acompanhar acesse o link: {data.get('ticket').get('url')}"""
                payload = {
                    "number": f"{data.get('author').get('mobile')}",
                    "text":f"{text}",
                    "delay": 2000,
                    "linkPreview": True,
                    "mentionsEveryOne": False,
                    "quoted": {
                        "key": {
                            "fromMe": True,
                            "type":'Novo acompanhamento',
                            "id": ""
                        }
                    }
                }

                enqueue_chat(payload)
        
        case 'Pesquisa de satisfação':
            print(f"Pesquisa de satisfação")
            print(f"data: {data}")
            text = f"""*_PESQUISA DE SATISFAÇÃO_*\n\nOlá, {data.get('author').get('name')}!\n\nSeu chamado nº {data.get('ticket').get('id')} - {data.get('ticket').get('title')}, foi fechado e a pesquisa de satisfação já pode ser respondida.\n\nPara responder acesse o link: {data.get('ticket').get('satisfaction').get('url')}"""
            payload = {
                "number": f"{data.get('author').get('mobile')}",
                "text":f"{text}",
                "delay": 2000,
                "linkPreview": True,
                "mentionsEveryOne": False,
                "quoted": {
                    "key": {
                        "fromMe": True,
                        "type":'Pesquisa de satisfação',
                        "id": ""
                    }
                }
            }

            try:
                enqueue_chat(payload)
                register_ticket_satisfaction(data.get('ticket').get('id'))
            except Exception as e:
                print(f"{datetime.now()}\terro ao enviar mensagem de pesquisa de satisfação: {e}")
                logger.error(f"{datetime.now()} - send_message - Erro: {e}", exc_info=True)
            
        case "Chamado solucionado":
            text = f"""*_CHAMADO SOLUCIONADO_*\n\nOlá, {data.get('author').get('name')}!\n\nSeu chamado nº {data.get('ticket').get('id')} - {data.get('ticket').get('title')}, foi foi solucionado!\n\n\t*{data.get('ticket').get('solution').get('author')}:* {clean_html(data.get('ticket').get('solution').get('description'))}\n\nPara aceitar ou negar a solução acesse o link:\n{data.get('ticket').get('url')}"""
            payload = {
                "number": f"{data.get('author').get('mobile')}",
                "text":f"{text}",
                "delay": 2000,
                "linkPreview": True,
                "mentionsEveryOne": False,
                "quoted": {
                    "key": {
                        "fromMe": True,
                        "type":'Chamado solucionado',
                        "id": ""
                    }
                }
            }
            # thread = Thread(target=send_ticket_solution_async, args=(payload,))
            # thread.start()
            # send_ticket_solution(payload)
            enqueue_chat(payload)
            return jsonify("Request received"), 200

        case _:
            
            payload = {
                "number": f"{data.get('author').get('mobile')}",
                "text":f"""*_ATUALIZAÇÃO DE UM CHAMADO_*\n\nOlá, {data.get('author').get('name')}!\n\n{data.get('ticket').get('lastupdater')} atualizou seu chamado nº {data.get('ticket').get('id')} - {data.get('ticket').get('title')}\n\n\t*status:* {data.get('ticket').get('status')}\n\nPara acompanhar acesse o link: {data.get('ticket').get('url')}""",
                "delay": 2000,
                "linkPreview": True,
                "mentionsEveryOne": False,
                "quoted": {
                    "key": {
                        "fromMe": True,
                        "type":"Caso geral",
                        "id": ""
                    }
                }
            }
    
            enqueue_chat(payload)
    # print(response.text)

def chat_worker():
    # print("chat_worker iniciado!")
    while True:
        payload = chat_queue.get()
        # print(f"Processando payload na fila: {payload}")
        try:
            start_chat(payload)
        except Exception as e:
            print(f"Erro no chat_worker: {e}")
            logger.error(f"{datetime.now()} - chat_worker - Erro: {e}", exc_info=True)
        finally:
            chat_queue.task_done()

def enqueue_chat(payload):
    # print(f"Enfileirando payload: {payload}")
    chat_queue.put(payload)

import json

def start_chat(payload):
    # print("Entrou em start_chat")
    url = f"{os.getenv('EVOLUTION_API_BASE_URL')}/message/sendText/{os.getenv('EVOLUTION_INSTANCE')}"

    response = requests.request(
        "POST", 
        url, 
        json=payload, 
        headers={
            "apikey": f"{os.getenv('EVOLUTION_API_KEY')}",
            "Content-Type": "application/json"
        }
    )
    
    data = response.json()
    # print(f"response post evolution: {data}\n")

    if response.status_code == 201:
        values = [str(data.get('key').get('id')), str(payload.get('number')), str(datetime.now()), str(payload.get('quoted').get('key').get('type')), str(payload.get('text'))]
        with pool.get_connection() as con:
            # print("conectado na pool")
            with con.cursor() as cursor:
                # print("conectado no cursor")
                sql=f"""INSERT INTO `u629942907_glpi`.`mensagens` (`id_mensagem`, `destinatario`, `data_hora`, `tipo`, `conteudo`)
                VALUES (%s, %s, %s, %s, %s);"""
                try:
                    cursor.execute(sql, values)
                    con.commit()
                    
                except mysql.connector.Error as e:
                    print(f"{datetime.now()}\terro de conexao MySQL: {e}")
                    logger.error(f"{datetime.now()} - start_chat - Erro: {e}", exc_info=True)
                except Exception as e:
                    print(f"{datetime.now()}\terro: {e}")

def send_ticket_solution(payload):
    # print("Entrou em send_ticket_solution")
    # print(payload)
    url = f"{os.getenv('EVOLUTION_API_BASE_URL')}/message/sendList/{os.getenv('EVOLUTION_INSTANCE')}"

    response = requests.request(
        "POST", 
        url, 
        json=payload, 
        headers={
            "apikey": f"{os.getenv('EVOLUTION_API_KEY')}",
            "Content-Type": "application/json"
        }
    )
    data = response.json()
    # print(data)
    if response.status_code == 201:
        values = [str(data.get('key').get('id')), str(payload.get('number')), str(datetime.now()), str(payload.get('quoted').get('key').get('type')), json.dumps(payload.get('sections'), ensure_ascii=False)]
        with pool.get_connection() as con:
            with con.cursor() as cursor:
                sql=f"""INSERT INTO `u629942907_glpi`.`mensagens` (`id_mensagem`, `destinatario`, `data_hora`, `tipo`, `conteudo`) 
                VALUES (%s, %s, %s, %s, %s);"""
                try:
                    cursor.execute(sql, values)
                    con.commit()
                    
                except mysql.connector.Error as e:
                    print(f"{datetime.now()}\terro de conexao MySQL: {e}\n")
                    logger.error(f"{datetime.now()} - send_ticket_solution - Erro: {e}", exc_info=True)
                except Exception as e:
                    print(f"{datetime.now()}\terro: {e}\n")

def register_ticket_satisfaction(ticketId):
    print(f"entrou em register_ticket_satisfaction com ticketId: {ticketId}")
    with pool.get_connection() as con:
        with con.cursor() as cursor:
            sql="""
            INSERT INTO `u629942907_glpi`.`glpi_itilsolutions` (itemtype, items_id, solutiontypes_id, content,`date_creation`, users_id) 
            VALUES ('Ticket', %s, 0, 'Pesquisa de satisfação enviada!', now(), 265);
            """
            try:
                cursor.execute(sql, (ticketId,))
                con.commit()
                
            except mysql.connector.Error as e:
                print(f"{datetime.now()}\terro de conexao MySQL: {e}")
                logger.error(f"{datetime.now()} - register_ticket_satisfaction - Erro de conexao MySQL: {e}", exc_info=True)
            except Exception as e:
                print(f"{datetime.now()}\terro: {e}")
                logger.error(f"{datetime.now()} - register_ticket_satisfaction - Erro: {e}", exc_info=True)

def busca_dados_tecnico(ticketId):
    query = f"""
    SELECT 
        CONCAT(TRIM(tec.firstname), ' ', TRIM(tec.realname)) AS atribuido,
        TRIM(tec.mobile) as telefone
    FROM
        glpi_tickets AS t
            LEFT JOIN
        glpi_tickets_users AS gtu ON t.id = gtu.tickets_id AND gtu.type = '2'
            LEFT JOIN
        glpi_users AS tec ON gtu.users_id = tec.id
    WHERE
        t.id = %s
    """
    with pool.get_connection() as con:
        with con.cursor() as cursor:
            cursor.execute(query, (ticketId,))
            result = cursor.fetchone()
            if result:
                return result

def adicionar_comentario_chamado_glpi(session_token, ticket_id, conteudo):
    """
    Adiciona um acompanhamento (followup) a um chamado no GLPI pelo seu Ticket ID.

    Args:
        session_token (str): token de sessão para uso da API Rest obtido no endpoint initSession.
        ticket_id (int): id do chamado.
        conteudo (str): comentário a ser inserido no chamado

    Returns:
        201 (OK) com o id dos itens adicionados.
        400 (Bad Request) com uma mensagem indicando o erro no parâmetro de entrada.
        401 (UNAUTHORIZED).
        
    """
    headers = {
        "Session-Token": f"{session_token}",
        "App-Token": f"{os.getenv('GLPI_APP_TOKEN')}",
        "Content-Type": "application/json"
    }

    url = f"{os.getenv('GLPI_API_BASE_URL')}/ITILFollowup/"

    # Se ticket_id for um container (set/list/tuple) pegar o primeiro elemento.
    # Isso previne erros caso alguém passe acidentalmente um set/list com o id.
    if isinstance(ticket_id, (set, list, tuple)):
        try:
            ticket_val = next(iter(ticket_id))
        except StopIteration:
            raise ValueError("ticket_id fornecido está vazio")
    else:
        ticket_val = ticket_id

    payload = {
        "input":{
            "itemtype": "Ticket",
            "items_id": ticket_val,
            "content": f"{conteudo}",
            "users_id": 360, # Usuário IA
            "requesttypes_id": 1, # HelpDesk
            "date": f"{datetime.now()}",
            "date_mod": f"{datetime.now()}",
            "date_creation": f"{datetime.now()}",
            "timeline_position": 4,
        }
    }

    # Passe o payload como objeto Python para que requests faça a serialização.
    # Assim evitamos chamar json.dumps() manualmente e permitimos que o requests
    # adicione os headers apropriados.
    response = requests.request("POST", url, headers=headers, json=payload, timeout=10)
    return response

chat_queue = queue.Queue()

worker_thread = Thread(target=chat_worker, daemon=True)
worker_thread.start()

if __name__ == '__main__':
    
    app.run(host='0.0.0.0', port=7047, debug=True)
