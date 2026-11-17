## Visão Geral
**Nome:** API Horta Familiar

**Contexto e propósito:** 
Manter uma horta familiar ou comunitária produtiva exige planejamento e acompanhamento constante. Frequentemente, os cuidadores perdem o controle sobre quais sementes foram plantadas em quais canteiros, esquecem o tempo de maturação das culturas, sobrepõem tarefas (como regar ou adubar o mesmo local) ou ficam sem insumos básicos por falta de controle de estoque. 

A API Horta Familiar resolve esses problemas centralizando a gestão agronômica em uma única plataforma digital.

**Público-Alvo:** 
Famílias entusiastas da agricultura urbana, pequenos produtores independentes e gestores de hortas comunitárias que precisam de uma ferramenta simples, porém robusta, para dividir tarefas e acompanhar a produção.

**Principais Funcionalidades do Domínio:**
*   **Gestão de Estoque:** Controle automatizado de insumos (sementes, fertilizantes), com baixa automática no estoque quando utilizados em plantios ou tarefas.
*   **Controle de Cultivo:** Mapeamento de culturas e ciclo de vida dos plantios (do crescimento à colheita ou perda).
*   **Organização Espacial:** Administração de canteiros e suas áreas físicas.
*   **Agendamento Sem Conflitos:** Atribuição de tarefas aos usuários com proteção contra sobreposição de horários para o mesmo canteiro.
*   **Relatórios (Dashboard):** Visualização consolidada da produtividade (peso colhido) agrupada por cultura e canteiro.

---

## Arquitetura de Recursos

A arquitetura da API é baseada em recursos bem definidos (RESTful) que interagem de forma relacional para manter a integridade das regras de negócio do campo.

1.  **Usuários (`Usuario`)**
    *   **Papel:** Atores do sistema (perfis ADMIN ou OPERACIONAL).
    *   **Relação:** Executam as **Tarefas** agendadas.

2.  **Culturas (`Cultura`)**
    *   **Papel:** Catálogo botânico com regras de negócio (tempo de maturação e espaçamento ideal).
    *   **Relação:** Servem de base para a criação de **Plantios**. Uma cultura pode estar em vários plantios.

3.  **Canteiros (`Canteiro`)**
    *   **Papel:** Representação do espaço físico (área em m²).
    *   **Relação:** Recebem **Plantios** e são alvo de **Tarefas**. A API garante que não haja tarefas simultâneas conflitantes no mesmo canteiro.

4.  **Insumos (`Insumo`)**
    *   **Papel:** Inventário de materiais (sementes, ferramentas, fertilizantes).
    *   **Relação:** Relacionamento "Muitos-para-Muitos" com **Plantios** e **Tarefas**. Quando vinculados a essas entidades, reduzem o estoque atual. Se desvinculados, o estoque é estornado.

5.  **Plantios (`Plantio`)**
    *   **Papel:** Entidade transacional que une uma **Cultura** a um **Canteiro** em uma data específica.
    *   **Relação:** Possui um ciclo de status (CRESCIMENTO -> COLHIDO/PERDIDO) e consome **Insumos** durante sua vigência.

6.  **Tarefas (`Tarefa`)**
    *   **Papel:** Eventos agendados com horários de início e fim.
    *   **Relação:** Vinculam um **Usuário** a um **Canteiro** (opcional) para realizar uma ação, podendo também consumir **Insumos** específicos para sua execução.

7. **Dashboard / Relatórios (`Dashboard`)**

   * **Papel:** Recurso analítico de leitura consolidada (representando a view `vw_dashboard_producao`).
   
   * **Relação:** Em vez de ser uma tabela isolada, ele lê e cruza os dados transacionais de **Plantios**, **Culturas** e **Canteiros**. Ele filtra os plantios concluídos (status COLHIDO) para fornecer a contagem total de safras e a soma de produtividade (em kg) agrupadas por tipo de planta e local de cultivo.

## Equipe
|Nome|RA|
|---|---|
Pedro Henrique Alves Villela | 2840482423009
Thaynara Franco Coelho | 2840482423001
