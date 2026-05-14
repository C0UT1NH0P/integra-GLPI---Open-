# Funções para interagir com a API do GLPI

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

GLPI_API_BASE_URL = os.getenv("GLPI_API_BASE_URL")
GLPI_APP_TOKEN = os.getenv("GLPI_APP_TOKEN")
GLPI_AUTH = os.getenv("GLPI_AUTH")

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


def update_ticket_priority(session_token, ticket_id, prioridade_id):
    """Atualiza a prioridade de um chamado no GLPI

    Args:
        session_token (str): token de sessão para autenticação na API do GLPI  
        ticket_id (int): ID do chamado no GLPI
        prioridade_id (int): ID da prioridade de acordo com a lista: [ 1 - Muito Baixa, 2 - Baixa, 3 - Média, 4 - Alta, 5 - Muito Alta, 6 - Crítica ]
        
    Returns:
        200 (OK) with update status for each item.
        207 (Multi-Status) with id of added items and errors.
        400 (Bad Request) with a message indicating an error in input parameter.
        401 (UNAUTHORIZED).
    """    
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
    
    try:
        print(response.json())
    except:
        print(response.status_code)


def main():
    try:
        session_token = init_glpi_api_session()
        
        update_ticket_priority(session_token, 12518, 1)
        
    finally:
        # Kill the session when done
        kill_glpi_api_session(session_token)

if __name__ == '__main__':
    main()