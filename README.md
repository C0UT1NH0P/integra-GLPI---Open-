# Documentação Técnica: Integração GLPI e OpenProject

Esta documentação fornece as instruções necessárias para entender, configurar e executar a aplicação de integração entre o sistema de chamados GLPI e o gerenciador de projetos OpenProject.

---

## 1. Visão Geral

O arquivo principal da aplicação é o `novo_chamado.py`. Ele consiste em uma API construída com o framework **FastAPI** que atua como um *webhook* para o GLPI. 

**Fluxo Principal de Funcionamento (`novo_chamado.py`):**
1. O GLPI envia um payload (JSON) para a rota `/webhook` da aplicação toda vez que um chamado é criado ou atualizado (dependendo da configuração do webhook no GLPI).
2. A aplicação processa esses dados e verifica regras de negócio para decidir se:
   - Cria um **Novo Projeto** no OpenProject (com pacotes de trabalho padrão, como "Termo de Abertura", "Levantamento de Requisitos", etc.).
   - Cria um **Pacote de Trabalho (Work Package)** associado a um projeto já existente.
3. Se houver anexos no chamado do GLPI, a aplicação faz o download desses arquivos para a pasta `/anexos` e, em seguida, os envia para o OpenProject.
4. O resultado da operação e eventuais erros são gravados no banco de dados MySQL (`integracao_chamados`) e em arquivos de log na pasta `/logs`.
5. Há também uma lógica FIFO (First In, First Out) no banco de dados para realizar um revezamento na atribuição de técnicos para os pacotes de trabalho.

### Estrutura de Diretórios Importantes
* **`/logs`**: Pasta gerada automaticamente onde ficam os registros de execução.
  * `api.log`: Registra o histórico completo de ações bem-sucedidas e informações gerais da API.
  * `error.log`: Registra apenas os erros que ocorrem durante o funcionamento (ex: falha de conexão, erro no payload).
  * `chamados_dados.log`: Registra especificamente os dados extraídos dos chamados do GLPI.
* **`/anexos`**: Diretório temporário utilizado para salvar os arquivos baixados dos chamados do GLPI antes de anexá-los aos pacotes de trabalho/projetos no OpenProject.

---

## 2. Requisitos e Configuração do Ambiente

### 2.1. Variáveis de Ambiente (`.env`)

A aplicação requer diversas configurações para se conectar ao GLPI, OpenProject e ao Banco de Dados. Foi criado um arquivo `.env.example` no repositório. Para rodar a aplicação, crie um arquivo `.env` na raiz do projeto contendo as seguintes variáveis:

#### Configurações do GLPI
* `GLPI_API_BASE_URL`: URL base da API REST do GLPI de produção.
* `GLPI_APP_TOKEN`: Token da aplicação gerado no GLPI.
* `GLPI_AUTH`: Token de usuário do GLPI (formato `user_token <seu_token>`).
* `GLPI_API_URL_TESTES`: URL do ambiente de testes do GLPI.
* `GLPI_APP_TOKEN_TESTES`: Token da aplicação do ambiente de testes.
* `USER_GLPI` e `PASS_GLPI`: Credenciais de usuário (geralmente usado para endpoints de inicialização de sessão).
* `GLPI_USER_GROUP_ID`: ID do grupo do usuário no GLPI.

#### Configurações do Banco de Dados MySQL
Responsável por gerenciar o status da integração e a fila de técnicos (FIFO).
* `HOST_MYSQL`: Endereço do banco de dados (ex: `localhost`).
* `PORT_MYSQL`: Porta do banco de dados (padrão: `3306`).
* `USER_MYSQL`: Usuário do banco de dados (ex: `categorizador`).
* `PASS_MYSQL`: Senha do banco de dados.
* `SCHEMA_MYSQL`: Nome da base de dados (ex: `integracao_op_glpi`).

#### Configurações do OpenProject
* `APIKEY_OPEN`: Token de autenticação da API do OpenProject. Deve ser gerado por um usuário administrador ou de sistema no OpenProject.
* `OPENPROJECT_URL`: URL base de acesso ao OpenProject.

#### Configurações Extras (Evolution API)
* `EVOLUTION_API_BASE_URL`, `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCE`: Parâmetros para envio de mensagens caso a integração com WhatsApp/Mensageria seja ativada.

---

## 3. Como Executar a Aplicação

A aplicação utiliza o **FastAPI** e é servida utilizando o servidor ASGI **Uvicorn**.

### Instalação das Dependências

Certifique-se de que o Python 3.8+ esteja instalado. Recomenda-se o uso de um ambiente virtual (`venv`).

```bash
# Crie e ative o ambiente virtual
python -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate

# Instale os pacotes necessários
pip install -r requirements.txt
```

*(Caso não possua o `requirements.txt`, as principais dependências são: `fastapi`, `uvicorn`, `requests`, `httpx`, `pymysql`, `beautifulsoup4`, `python-dotenv`).*

### Subindo o Servidor

O código `novo_chamado.py` já está configurado para subir a aplicação na **porta 30112**.
Para iniciar a API em modo de desenvolvimento (com *hot-reload*), basta rodar o próprio arquivo com o Python:

```bash
python novo_chamado.py
```

Você verá no console a indicação de que o servidor iniciou:
`INFO: Uvicorn running on http://0.0.0.0:30112 (Press CTRL+C to quit)`

**Rotas Principais:**
* `POST /webhook`: Endpoint que o GLPI deve chamar para enviar os dados dos chamados.
* `GET /teste` ou `POST /teste`: Rota genérica para validação rápida se a API está online.

---

## 4. Dicas para Manutenção

1. **Testando o Webhook Localmente**: Se for testar a integração localmente, recomenda-se utilizar o Ngrok (`ngrok http 30112`) para expor a aplicação local à internet para que o GLPI consiga enviar os webhooks.
2. **Banco de Dados**: Verifique se a tabela `integracao_chamados` foi criada corretamente no seu banco MySQL, caso contrário, erros de `UPDATE/INSERT` ocorrerão (veja os arquivos de schema se disponíveis ou o método `salvar_erro_banco`).
3. **Mapeamento de Usuários**: No arquivo `novo_chamado.py`, existe um dicionário fixo mapeando usuários (`USERS_MAP`), bem como as filas estáticas (`fila_tecnicos`). Caso um novo colaborador entre na equipe, esse trecho no código precisa ser atualizado com o ID correspondente do usuário no OpenProject.
4. **Exportar para PDF**: Este arquivo está formatado com Markdown amigável a exportadores de PDF. Use plugins do VS Code (como o *Markdown PDF*) ou extensões do Chrome para salvar este README com um design limpo e estruturado.
