# Funções para interagir com a API do GLPI

import os
import json
import requests
from dotenv import load_dotenv
import base64
import httpx

load_dotenv(override=True)

GLPI_API_BASE_URL = os.getenv("GLPI_API_BASE_URL")
GLPI_APP_TOKEN = os.getenv("GLPI_APP_TOKEN")
GLPI_AUTH = os.getenv("GLPI_AUTH")

APP_TOKEN = os.getenv("GLPI_APP_TOKEN_TESTES")
GLPI_API_URL = os.getenv("GLPI_API_URL_TESTES")
user_glpi = os.getenv('USER_GLPI')
pass_glpi = os.getenv('PASS_GLPI')

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

def kill_glpi_api_session(session_token):
   headers = {
      "Session-Token": f"{session_token}",
      "App-Token": f"{os.getenv('GLPI_APP_TOKEN')}",
      "Content-Type": "application/json"
   }

   url = f"{os.getenv('GLPI_API_BASE_URL')}/killSession"

   response = requests.request("GET", url, headers=headers)
   
   return response.status_code      
       
def get_ticket(session_token, ticket_id):
   headers = {
      "Session-Token": f"{session_token}",
      "App-Token": f"{GLPI_APP_TOKEN}",
      "Content-Type": "application/json"
   }

   url = f"{GLPI_API_BASE_URL}/Ticket/{ticket_id}"
   
   response = requests.request("GET", url, headers=headers)
   response.raise_for_status()
   try:
       print(response.json())
   except:
       print(response.status_code)


def update_ticket_priority(ticket_id, prioridade_id):
    """Atualiza a prioridade de um chamado no GLPI

    Args:
        ticket_id (int): ID do chamado no GLPI
        prioridade_id (int): ID da prioridade de acordo com a lista: [ 1 - Muito Baixa, 2 - Baixa, 3 - Média, 4 - Alta, 5 - Muito Alta, 6 - Crítica ]
        
    Returns:
        200 (OK) with update status for each item.
        207 (Multi-Status) with id of added items and errors.
        400 (Bad Request) with a message indicating an error in input parameter.
        401 (UNAUTHORIZED).
    """    
    try:
        session_token = initSession()
        headers = {
            "Session-Token": f"{session_token}",
            "App-Token": f"{os.getenv('GLPI_APP_TOKEN')}",
            "Content-Type": "application/json"
        }
        
        url = f"{GLPI_API_BASE_URL}/Ticket/{ticket_id}"
        
        input_data = {
            "input": {
                "priority": prioridade_id
            }
        }
        
        response = requests.patch(url, headers=headers, json=input_data)
        
        response.raise_for_status()
                
        return response.status_code
    
    finally:
        # Kill the session when done
        kill_glpi_api_session(session_token)