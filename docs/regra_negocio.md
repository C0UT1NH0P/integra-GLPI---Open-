# Documentação de Regras de Negócio: Integração GLPI e OpenProject

## 1. Objetivo
Este documento define as regras de negócio para a integração entre os chamados originados no formulário do GLPI e as ações correspondentes no sistema OpenProject. O objetivo é mapear todas as opções possíveis vindas do formulário e determinar qual entidade será criada ou atualizada no OpenProject.

## 2. Entidades no OpenProject
Dependendo dos dados recebidos do GLPI, a integração poderá criar no OpenProject:
- **Um Novo Projeto**
- **Um Pacote de Trabalho** (Work Package), que pode ser dos seguintes tipos:
  1. Tarefa
  2. Marco
  3. Tarefa Resumo
  4. Funcionalidade
  5. Épico
  6. História de Usuário
  7. Bug

## 3. Origem dos Dados (Formulário GLPI)
Todos os novos chamados chegarão através do "Formulário IA" no GLPI. Abaixo estão os campos do formulário que serão recebidos e processados:

1. **Tipo de Projeto:** 
   - Novo Projeto
   - Mudança em um projeto existente 
2. **Nome do Projeto:** 
   - Se for um novo projeto: Descrever um nome.
   - Se for uma mudança: Escolher sobre qual projeto existente a mudança será realizada.
3. **Impacto no Setor Solicitante:**
   - Baixo | Médio | Alto
4. **Descrição do Impacto no Setor Solicitante:**
   - (Texto descritivo)
5. **Impacto em Outros Setores:** 
   - Baixo | Médio | Alto
6. **Descrição do Impacto em Outros Setores:**
   - (Texto descritivo)
7. **Urgência:**
   - Muito Alta | Alta | Média | Baixa | Muito Baixa
8. **Tipo de Demanda:**
   - Correção e Manutenção | Melhoria de Sistemas | Desenvolvimento de Soluções | Demandas Estratégicas
9. **Categoria da Demanda:**
   - (A lista de opções depende do "Tipo de Demanda" escolhido)
10. **Descrição Detalhada do Projeto/Alteração:**
   - (Texto descritivo)

## 4. Mapeamento e Regras de Negócio

A decisão central da integração é definir se o chamado será transformado em um **Novo Projeto** ou em um **Pacote de Trabalho (Work Package)** associado a um projeto existente. 

### 4.1. Regras para Criação de Novo Projeto

Um chamado será convertido em um **Novo Projeto** caso preencha **alguma** das situações abaixo:

1. **Definição Explícita:** 
   - O campo "Tipo de Projeto" for igual a "Novo Projeto".
2. **Desenvolvimento de Soluções:** 
   - Categoria for "Novo sistema", "Nova automação" ou "Novo bot".
3. **Demandas Estratégicas:** 
   - Qualquer categoria deste tipo ("Projetos internos", "Solicitações da diretoria", "Inovação").
4. **Condições Especiais (Impacto e Urgência Elevados):**
   - **Melhoria de Sistemas:** Se o impacto no setor solicitante for **Alto** E a urgência for **Alta ou Imediata** (ou o esforço estimado for > 8h).
   - **Integração entre sistemas:** Se o impacto e a urgência forem **Altos**.

**Mapeamento de Campos para Novo Projeto:**
- **Nome do Projeto:** Preenchido com o "Nome do Projeto" (ou título do chamado) recebido do GLPI.
- **Prioridade:** Baseada na opção de "Urgência" do GLPI.
- **Descrição do Projeto:** Concatenação estruturada dos campos:
  - Descrição Detalhada da Alteração
  - Tipo de Demanda e Categoria
  - Urgência
  - Descrição do Impacto no Setor Solicitante
  - Descrição do Impacto em Outros Setores

---

### 4.2. Regras para Criação de Pacote de Trabalho (Work Package)

Quando o chamado **não** atende às regras de "Novo Projeto" (ex: correção simples, ou melhorias de baixo impacto), ele será criado como um Work Package dentro de um projeto existente.

**Identificação do Projeto Alvo:**
- O formulário enviará a informação do sistema (ex: `12 - Analise de Margem`).
- A integração extrairá o ID do projeto a partir dessa string (ex: ID `12`) para saber em qual projeto do OpenProject o Work Package será criado.

O **Tipo de Work Package** gerado dependerá da Categoria selecionada no GLPI:

#### A. Correções e Manutenção
*Todas as demandas deste tipo geram um pacote do tipo **Bug**.*
- Erro em sistema ➔ **Bug**
- Falha em automação ➔ **Bug**
- Problema em integração ➔ **Bug**
- Sistema fora do ar ➔ **Bug**

#### B. Melhoria de Sistemas
*(Que não atingiram o critério de alto impacto/urgência para virar Novo Projeto)*
- Evolução de funcionalidade ➔ **Funcionalidade**
- Otimização de performance ➔ **Tarefa**
- Ajuste de interface ➔ **Funcionalidade**
- Refatoração ➔ **Tarefa**

#### C. Desenvolvimento de Soluções
- Integração entre sistemas ➔ (Se o impacto não for alto o suficiente para virar projeto, vira **Funcionalidade** no projeto alvo).

**Mapeamento de Campos para Work Package:**
- **Tipo (Type):** Definido pelas regras de Categoria detalhadas acima.
- **Prioridade (Priority):** Preenchida com a "Urgência" informada pelo usuário no GLPI.
- **Descrição do Work Package:** Concatenação estruturada dos campos:
  - Descrição Detalhada da Alteração
  - Descrição do Impacto no Setor Solicitante
  - Descrição do Impacto em Outros Setores 

## 5 Regras
- Sempre puscar o nome da pessoa que abriu o chamado e inserir na descrição do workpackage ou do projeto 

## 6. Cálculo Automático de Prazos (Início e Fim)

Quando um chamado validado entra como projeto/pacote de trabalho, a aplicação não define prazos arbitrários. Existe uma lógica dinâmica na API para agendar o trabalho (`startDate` e `dueDate`) baseada no volume de tarefas do técnico e na prioridade do chamado.

### Fluxo de Cálculo:

1. **Análise da Fila (Contador de Projetos):**
   A aplicação realiza uma consulta (GET) no OpenProject para buscar todos os pacotes de trabalho ativos (excluindo os de status "fechado" ou "rejeitado") atribuídos ao técnico que receberá o chamado. O script extrai a maior data de conclusão (`dueDate`) atual na fila.

2. **Agendamento da Data de Início (`startDate`):**
   - **Fluxo Normal**: O novo projeto tem início agendado para o **dia subsequente** ao término da última demanda pendente do técnico.
   - **Fila Vazia ou Atrasada**: Se o técnico estiver sem projetos pendentes, ou a maior data final for menor que o dia atual, o projeto se inicia **hoje**.

3. **Gerenciamento de Carga (Gargalo de Projetos):**
   - Para evitar sobrecarga técnica, se o técnico estiver com um excesso de chamados pendentes (neste caso, **mais de 10 projetos**), a aplicação automaticamente joga a data de início **2 dias** mais para o futuro. Isso provém uma folga para desafogar a fila (não aplicável à prioridade *Imediata*).

4. **Regras baseadas em Prioridade (Duração da Tarefa):**
   A prioridade do pacote de trabalho define o prazo em dias para o desenvolvimento:

   - **Prioridade Imediata (10)**:
     - **Duração**: 1 dia.
     - **Regra Exceção**: Fura completamente a fila; a data de início recebe *override* para ser **hoje**, forçando prioridade máxima.
   - **Prioridade Alta (9)**:
     - **Duração**: 3 dias.
   - **Prioridade Normal (8) (Padrão)**:
     - **Duração**: 7 dias.
   - **Prioridade Baixa (7)**:
     - **Duração**: 15 dias.

### Resultado:
O número de dias definidos pela prioridade é somado à data de início (`startDate`) estabelecida pela fila, o que resulta na data de finalização (`dueDate`). Ambas são preenchidas nos parâmetros do Work Package gerado no OpenProject.