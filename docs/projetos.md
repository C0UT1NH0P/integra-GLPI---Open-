# Documentação de Projetos

## Integração GLPI → OpenProject

- **ID do Projeto**: 77
- **Criado em**: 28/04/2026 13:30:21

### Descrição
Desenvolvimento de integração entre GLPI e OpenProject para automatizar a transformação de chamados em projetos, pacotes de trabalho e tarefas.

A solução irá capturar chamados do GLPI, aplicar regras de negócio e direcionar automaticamente para a estrutura correta no OpenProject:

*   Novo desenvolvimento → criação de projeto
    
*   Melhoria → criação de pacote de trabalho dentro de projeto existente
    
*   Correção → criação de tarefa dentro de projeto existente ou projeto padrão de correções
    
*   Chamados GLPI → centralização em projeto anual por usuário
    

O objetivo é garantir organização, rastreabilidade e escalabilidade do setor de IA.

### Links Importantes (Criação de Pacotes de Trabalho)
- **Via Formulário**: `/api/v3/projects/77/work_packages/form`
- **Imediatamente**: `/api/v3/projects/77/work_packages`

---

## Sistema de Atendimento RH

- **ID do Projeto**: 68
- **Criado em**: 14/04/2026 14:39:57

### Descrição
Este projeto visa a estruturação e profissionalização dos canais de atendimento do departamento de Recursos Humanos. O objetivo central é migrar de um modelo de atendimento informal e descentralizado (WhatsApp pessoal e interrupções presenciais) para um sistema de gestão de chamados robusto, focado em rastreabilidade, eficiência e extração de métricas de desempenho.

### Links Importantes (Criação de Pacotes de Trabalho)
- **Via Formulário**: `/api/v3/projects/68/work_packages/form`
- **Imediatamente**: `/api/v3/projects/68/work_packages`

---

## Sistema de Abertura e Gestão de Chamados de RH via WhatsApp integrado ao GLPI

- **ID do Projeto**: 63
- **Criado em**: 26/03/2026 17:04:16

### Descrição
O projeto consiste na criação de um canal inteligente de atendimento de RH via WhatsApp, totalmente integrado ao GLPI, permitindo que colaboradores abram e acompanhem chamados sem precisar acessar o sistema interno.

O colaborador envia uma mensagem pelo WhatsApp descrevendo sua necessidade (ex: dúvidas sobre folha, benefícios, férias, etc.). Um mecanismo de triagem automática analisa o conteúdo da mensagem e identifica o setor responsável dentro do RH (como Departamento Pessoal, Benefícios ou Recrutamento), criando automaticamente o chamado no GLPI já atribuído ao técnico responsável.

O time de RH gerencia todos os atendimentos diretamente pelo GLPI, podendo responder, atualizar status e acompanhar o andamento dos chamados. Todas as interações realizadas no GLPI são automaticamente sincronizadas com o WhatsApp, garantindo que o colaborador receba as respostas em tempo real no mesmo canal onde iniciou o contato.

Com isso, elimina-se a necessidade de atendimento direto via WhatsApp pelos analistas de RH, centralizando toda a operação no GLPI e permitindo rastreabilidade completa, padronização do atendimento e geração de métricas precisas (tempo de resposta, SLA, volume por categoria, etc.).

O sistema melhora a experiência do colaborador, reduz a informalidade no atendimento e fornece ao RH dados estruturados para tomada de decisão e melhoria contínua.

*   WhatsApp - entrada do colaborador
    
*   IA / regra - classifica setor
    
*   GLPI - cria chamado já atribuído
    
*   Técnico responde no GLPI
    
*   Integração - envia resposta para WhatsApp

### Links Importantes (Criação de Pacotes de Trabalho)
- **Via Formulário**: `/api/v3/projects/63/work_packages/form`
- **Imediatamente**: `/api/v3/projects/63/work_packages`

---

## Troca de servidor

- **ID do Projeto**: 62
- **Criado em**: 26/03/2026 17:00:13

### Descrição
Sem descrição.

### Links Importantes (Criação de Pacotes de Trabalho)
- **Via Formulário**: `/api/v3/projects/62/work_packages/form`
- **Imediatamente**: `/api/v3/projects/62/work_packages`

---

## Sistema OS disparar Kit reparo

- **ID do Projeto**: 54
- **Criado em**: 09/03/2026 13:43:25

### Descrição
Sem descrição.

### Links Importantes (Criação de Pacotes de Trabalho)
- **Via Formulário**: `/api/v3/projects/54/work_packages/form`
- **Imediatamente**: `/api/v3/projects/54/work_packages`

---

## Unificar sistemas

- **ID do Projeto**: 53
- **Criado em**: 03/02/2026 11:00:00

### Descrição
Sem descrição.

### Links Importantes (Criação de Pacotes de Trabalho)
- **Via Formulário**: `/api/v3/projects/53/work_packages/form`
- **Imediatamente**: `/api/v3/projects/53/work_packages`

---

## Melhorias OpenProject

- **ID do Projeto**: 30
- **Criado em**: 26/02/2026 14:26:11

### Descrição
# Melhorias OpenProject

Este projeto foi criado para centralizar todas as demandas e fluxos de trabalho relacionados ao software de gestão de projetos.

Qualquer membro da equipe pode registrar subtarefas no [**Backlog do Produto**](https://openproject.brggeradores.com.br/projects/melhorias-openproject/work_packages/205/activity), propondo sugestões de aprimoramento ou funcionalidades para otimizar o uso do sistema.  
As solicitações serão submetidas a uma avaliação técnica e, após a aprovação, implementadas gradualmente conforme o cronograma de prioridades.

### Links Importantes (Criação de Pacotes de Trabalho)
- **Via Formulário**: `/api/v3/projects/30/work_packages/form`
- **Imediatamente**: `/api/v3/projects/30/work_packages`

---

## Sistema cobranças

- **ID do Projeto**: 25
- **Criado em**: 23/02/2026 18:32:45

### Descrição
Sem descrição.

### Links Importantes (Criação de Pacotes de Trabalho)
- **Via Formulário**: `/api/v3/projects/25/work_packages/form`
- **Imediatamente**: `/api/v3/projects/25/work_packages`

---

## Multas veiculares

- **ID do Projeto**: 24
- **Criado em**: 23/02/2026 18:28:22

### Descrição
Sem descrição.

### Links Importantes (Criação de Pacotes de Trabalho)
- **Via Formulário**: `/api/v3/projects/24/work_packages/form`
- **Imediatamente**: `/api/v3/projects/24/work_packages`

---

## Agente IA

- **ID do Projeto**: 23
- **Criado em**: 23/02/2026 17:57:38

### Descrição
Instalar o agente de IA para controle e automacao.

### Links Importantes (Criação de Pacotes de Trabalho)
- **Via Formulário**: `/api/v3/projects/23/work_packages/form`
- **Imediatamente**: `/api/v3/projects/23/work_packages`

---

## Automação VExpenses

- **ID do Projeto**: 21
- **Criado em**: 12/02/2026 19:20:33

### Descrição
automatizar processo VExpenses para o financeiro

### Links Importantes (Criação de Pacotes de Trabalho)
- **Via Formulário**: `/api/v3/projects/21/work_packages/form`
- **Imediatamente**: `/api/v3/projects/21/work_packages`

---

## Sistema de Proposta BRG para o comercial

- **ID do Projeto**: 20
- **Criado em**: 10/02/2026 11:38:29

### Descrição
Este projeto moderniza o sistema de propostas da empresa, substituindo o sistema de 2021 que era totalmente independente e sem comunicacao com os dados da empresa: nao havia acesso ao Protheus, nao existia interface HTML (tudo era feito no admin do Django), cadastros de produtos eram manuais, lancamentos de propostas precisavam ser levados ao Protheus e nao havia visibilidade se uma proposta tinha sido ganha ou nao. A nova solucao integra o Protheus, oferece interface web amigavel, automatiza cadastros e sincronizacoes, centraliza o fluxo de propostas e permite acompanhar o status de cada proposta de ponta a ponta, tornando o processo mais rapido, confiavel e escalavel.

### Links Importantes (Criação de Pacotes de Trabalho)
- **Via Formulário**: `/api/v3/projects/20/work_packages/form`
- **Imediatamente**: `/api/v3/projects/20/work_packages`

---

## Análise de Margem

- **ID do Projeto**: 12
- **Criado em**: 18/11/2025 13:33:19

### Descrição
Digitalização do fluxo manual de análise de margem.

### Links Importantes (Criação de Pacotes de Trabalho)
- **Via Formulário**: `/api/v3/projects/12/work_packages/form`
- **Imediatamente**: `/api/v3/projects/12/work_packages`

---

## Projeto Modelo

- **ID do Projeto**: 4
- **Criado em**: 04/11/2025 17:48:07

### Descrição
Adicione aqui a descrição do projeto

### Links Importantes (Criação de Pacotes de Trabalho)
- **Via Formulário**: `/api/v3/projects/4/work_packages/form`
- **Imediatamente**: `/api/v3/projects/4/work_packages`

---

