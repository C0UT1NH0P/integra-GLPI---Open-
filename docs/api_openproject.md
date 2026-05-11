# Documentação da API do OpenProject

Esta documentação descreve o funcionamento de três endpoints principais da API v3 do OpenProject para criação de projetos, criação de pacotes de trabalho (tarefas) e listagem de projetos.

Todas as requisições devem incluir o cabeçalho de autorização com o seu Bearer Token:
`Authorization: Bearer <SEU_TOKEN>`

---

## 1. Criar Projeto (Create Project)

Cria um novo projeto aplicando os atributos fornecidos no corpo da requisição.

- **Método HTTP:** `POST`
- **Endpoint:** `/api/v3/projects`
- **Content-Type:** `application/json`

### Parâmetros

Este endpoint não recebe parâmetros na URL (query parameters). Todos os dados devem ser enviados no corpo da requisição (JSON).

### Corpo da Requisição (Schema)

Abaixo está a estrutura base do JSON para criação de um projeto:

```json
{
  "name": "Nome do Projeto",
  "identifier": "identificador-unico",
  "description": {
    "format": "markdown",
    "raw": "Descrição do seu projeto aqui."
  },
  "active": true,
  "public": false,
  "statusExplanation": {
    "format": "markdown",
    "raw": "Justificativa do status atual do projeto"
  }
}
```
*(Nota: O payload real suporta campos adicionais (_type, custom fields, parent_id, etc), conforme links e schemas do OpenProject).*

---

## 2. Criar Pacote de Trabalho ou Tarefa (Create Work Package)

Cria uma nova tarefa/pacote de trabalho. Quando estiver definindo data de início (startDate), data de conclusão (dueDate) e duração (duration) simultaneamente, a correção será checada e retornará erro 422 se não baterem. Você pode enviar apenas duas delas e o servidor calculará a terceira.

- **Método HTTP:** `POST`
- **Endpoint:** `/api/v3/work_packages`
- **Content-Type:** `application/json`

### Parâmetros de URL (Query Parameters)

| Parâmetro | Tipo | Opcional | Padrão | Descrição |
| :--- | :--- | :--- | :--- | :--- |
| `notify` | boolean | Sim | `true` | Indica se notificações de alteração (ex: E-Mail) devem ser enviadas aos usuários interessados (observadores, autor, responsável). |

### Corpo da Requisição (Schema de Exemplo)

O payload requer links como `project`, `type`, `status` e `priority` para classificar o Work Package.

```json
{
  "subject": "Desenvolver a API",
  "description": {
    "format": "markdown",
    "raw": "Desenvolver integração incrível com a API do OpenProject."
  },
  "percentageDone": 0,
  "estimatedTime": "PT10H",
  "_links": {
    "project": {
      "href": "/api/v3/projects/1"
    },
    "type": {
      "href": "/api/v3/types/1"
    },
    "priority": {
      "href": "/api/v3/priorities/2"
    }
  }
}
```

---

## 3. Listar Projetos (List Projects)

Retorna uma coleção de projetos. A coleção pode ser filtrada, ordenada e ter campos específicos selecionados através dos parâmetros da URL. Apenas os projetos que o usuário tem permissão para visualizar serão retornados.

- **Método HTTP:** `GET`
- **Endpoint:** `/api/v3/projects`

### Parâmetros de URL (Query Parameters)

#### 3.1. `filters` (Opcional)
String JSON que especifica condições de filtro. Formato é uma lista de dicionários.
- **Exemplo:** `[{"active": {"operator": "=", "values": ["t"]}}]`
- **Filtros suportados comuns:**
  - `active`: baseado na propriedade de ativo do projeto (t ou f).
  - `ancestor`: filtra por ID do projeto pai ancestral.
  - `created_at`: tempo que o projeto foi criado.
  - `favorited`: se foi favoritado pelo usuário atual.
  - `id`: baseado no ID do projeto.
  - `name_and_identifier`: baseado no nome ou identificador.
  - `parent_id`: filtra por projetos cujo projeto pai direto é o informado.
  - `type_id`: baseado nos tipos de work package ativos no projeto.
  - `visible`: útil para administradores saberem quais projetos são visíveis para um ID de usuário específico.

#### 3.2. `sortBy` (Opcional)
String JSON especificando o critério de ordenação.
- **Exemplo:** `[["id", "asc"], ["name", "desc"]]`
- **Campos suportados comuns:** `id`, `name`, `created_at`, `public`, `latest_activity_at`.

#### 3.3. `select` (Opcional)
Lista de propriedades separadas por vírgula para incluir na resposta (limita os dados retornados para economizar banda).
- **Exemplo:** `total,elements/identifier,elements/name`