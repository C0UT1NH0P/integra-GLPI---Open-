# Funções para interagir com a API do GLPI

import os
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

def searchOptions(session_token):
   headers = {
      "Session-Token": f"{session_token}",
      "App-Token": f"{GLPI_APP_TOKEN}",
      "Content-Type": "application/json"
   }

   url = f"{GLPI_API_BASE_URL}/listSearchOptions/Ticket"
   
   response = requests.request("GET", url, headers=headers)
   
   response.raise_for_status()
   
   print(response.json())

def searchItems(session_token):
   headers = {
      "Session-Token": f"{session_token}",
      "App-Token": f"{GLPI_APP_TOKEN}",
      "Content-Type": "application/json"
   }

   url = f"{GLPI_API_BASE_URL}/search/AllAssets"
   
   response = requests.request("GET", url, headers=headers)
   print(response.json())
   
def main():
    try:
        session_token = init_glpi_api_session()
        
        # Use the session token for subsequent API calls
        searchOptions(session_token)
        # searchItems(session_token)
        
    except Exception as e:
        print(f"Error initializing GLPI API session: {e}")
        return
    finally:
        # Kill the session when done
        kill_glpi_api_session(session_token)

if __name__ == '__main__':
    main()