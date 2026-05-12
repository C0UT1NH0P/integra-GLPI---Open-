# Funções de atualização dos campos personalizados de status para projetos
# e pacotes de trabalho, e prioridade para pacotes de trabalho na API do Openproject.

# Futuramente, expandir para todas as funções que manipulam o OpenProject

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = os.getenv("OPENPROJECT_API_BASE_URL")
TOKEN = os.getenv("OPENPROJECT_TOKEN")

def obter_lockversion_pacote_de_trabalho(id__pacote_de_trabalho):
    """Obtém o último LockVersion de um pacote de trabalho para fazer PATCH em suas propriedades evitando problemas de concorrência

    Args:
        id__pacote_de_trabalho (int): ID do pacote de trabalho
        
    Returns:
        int: O último LockVersion do pacote de trabalho
    """
    url = f"{API_BASE_URL}/api/v3/work_packages/{id__pacote_de_trabalho}"
    
    response = requests.get(url, auth=('apikey', TOKEN))
    response.raise_for_status()
    
    return response.json().get("lockVersion")

def atualizar_status_projeto(id__projeto, id__status):
    """Atualiza o status de um projeto de acordo com as opções do GLPI

    Args:
        id__projeto (int): ID do projeto no OpenProject
        id__status (int): ID do status de acordo com a lista: [ 7 - Novo, 8 - Em Atendimento (atribuído), 9 - Em Atendimento (planejado), 10 - Pendente, 17 - Solucionado, 18 - Fechado ]
        
    Returns:
        int: Status code da resposta da API do OpenProject
    """    
    url = f"{API_BASE_URL}/api/v3/projects/{id__projeto}"
    
    data = {
        "_links": {
            "customField6": {
                "href": f"/api/v3/custom_options/{id__status}"
            }
        }
    }
    
    response = requests.patch(url, json=data, auth=('apikey', TOKEN))
    
    response.raise_for_status()
    
    return response.status_code

def atualizar_status_pacote_de_trabalho(id__pacote_de_trabalho, id__status):
    """Atualiza o status de um pacote de trabalho de acordo com as opções do GLPI

    Args:
        id__pacote_de_trabalho (int): ID do pacote de trabalho no OpenProject
        id__status (int): ID do status de acordo com a lista: [ 11 - Novo, 12 - Em Atendimento (atribuído), 13 - Em Atendimento (planejado), 14 - Pendente, 15 - Solucionado, 16 - Fechado ]
        
    Returns:
        int: Status code da resposta da API do OpenProject
    """    
    url = f"{API_BASE_URL}/api/v3/work_packages/{id__pacote_de_trabalho}"
    
    lockVersion = obter_lockversion_pacote_de_trabalho(id__pacote_de_trabalho)
    
    data = {
            "lockVersion": lockVersion,
            "_links": {
                "customField7": {
                        "href": f"/api/v3/custom_options/{id__status}"
                }
            }
    }
    
    response = requests.patch(url, json=data, auth=('apikey', TOKEN))
    
    response.raise_for_status()
    
    return response.status_code
    
def atualizar_prioridade_pacote_de_trabalho(id__pacote_de_trabalho, id__prioridade):
    """Atualiza a prioridade de um pacote de trabalho de acordo com as opções da API do OpenProject

    Args:
        id__pacote_de_trabalho (int): ID do pacote de trabalho
        id__prioridade (int): ID da prioridade de acordo com a lista:[ 16 - Muito Baixa, 7 - Baixa, 8 - Média, 9 - Alta, 15 - Muito Alta, 10 - Crítica ] 
        
    Returns:
        int: Status code da resposta da API do OpenProject
    """    
    url = f"{API_BASE_URL}/api/v3/work_packages/{id__pacote_de_trabalho}"
    
    lockVersion = obter_lockversion_pacote_de_trabalho(id__pacote_de_trabalho)
    
    data = {
        'lockVersion': lockVersion,
        '_links': {
            "priority": {
                "href": f"/api/v3/priorities/{id__prioridade}"
            }
        }
    }
    
    response = requests.patch(url, json=data, auth=('apikey', TOKEN))
    
    response.raise_for_status()
    
    return response.status_code
