# SPEC.md — Especificação Técnica e Funcional (API Horta Familiar)

**Versão da API:** 1.0.0  
**Metodologia:** Spec-Driven Development (SDD)  
**Fonte da Verdade:** `horta_api.Apidog.json`  
**Padrão de Código:** `STYLEGUIDE.md`  
**Governança:** `AGENTS.md`  

---

## 1. Visão Geral e Propósito

A **API Horta Familiar** é um sistema backend desenvolvido para apoiar a gestão operacional, técnica e logística de hortas comunitárias, familiares e institucionais. 

A solução centraliza o ciclo completo da produção agrícola urbana:
1. **Governança de Acessos:** Controle de usuários operacionais e administradores com autenticação segura baseada em tokens JWT.
2. **Catálogo de Culturas:** Cadastro técnico de variedades agrícolas com tempo de maturação e espaçamento ideal entre mudas.
3. **Gestão de Canteiros:** Mapeamento físico das áreas cultiváveis em metros quadrados.
4. **Controle de Estoque de Insumos:** Rastreabilidade de sementes, fertilizantes e ferramentas, com controle de estoque mínimo.
5. **Rastreabilidade de Plantios:** Ciclo de vida do plantio (`CRESCIMENTO`, `COLHIDO`, `PERDIDO`), pesagem de colheitas e consumo de sementes.
6. **Agendamento de Tarefas:** Planejamento de atividades de manejo agrícola com prevenção de sobreposição de horários no mesmo canteiro.
7. **Painel de Produção (Dashboard):** Relatório consolidado agrupando total de plantios colhidos e produtividade total em kg por cultura e canteiro.

---

## 2. Entidades de Domínio e Data Schemas Desacoplados

Todos os contratos de entrada e saída são estritamente desacoplados e tipados no Pydantic v2.

### 2.1. Usuário (`Usuario` / `UsuarioInput`)
- **`id_usuario`**: `int` (Chave primária, somente leitura na saída).
- **`nome`**: `string` (Obrigatório, máx 100 caracteres).
- **`email`**: `string` (Formato e-mail válido, máx 150 caracteres, índice único).
- **`senha`**: `string` (Obrigatório na criação/atualização, mín 4 e máx 255 caracteres, armazenada com hash PBKDF2/SHA-256).
- **`perfil`**: `enum` (`ADMIN` | `OPERACIONAL`).

### 2.2. Cultura (`Cultura` / `CulturaInput`)
- **`id_cultura`**: `int` (Chave primária).
- **`nome`**: `string` (Obrigatório, máx 100 caracteres, valor único).
- **`tempo_maturacao_dias`**: `int` (Obrigatório, valor mínimo: 1).
- **`espacamento_ideal`**: `float` (Obrigatório, valor estritamente maior que 0.0 metros).

### 2.3. Canteiro (`Canteiro` / `CanteiroInput`)
- **`id_canteiro`**: `int` (Chave primária).
- **`identificacao`**: `string` (Obrigatório, máx 50 caracteres, valor único).
- **`area_m2`**: `float` (Obrigatório, valor estritamente maior que 0.0 m²).

### 2.4. Insumo (`Insumo` / `InsumoInput` / `InsumoUsoInput`)
- **`id_insumo`**: `int` (Chave primária).
- **`nome`**: `string` (Obrigatório, máx 100 caracteres).
- **`tipo`**: `enum` (`SEMENTE` | `FERTILIZANTE` | `FERRAMENTA`).
- **`quantidade_estoque`**: `float` (Obrigatório, valor mínimo: 0.0).
- **`estoque_minimo`**: `float` (Obrigatório, valor mínimo: 0.0).
- **`quantidade_utilizada`** (em `InsumoUsoInput`): `float` (Obrigatório, valor maior que 0.0).

### 2.5. Plantio (`Plantio` / `PlantioInput` / `PlantioInsumo`)
- **`id_plantio`**: `int` (Chave primária).
- **`id_cultura`**: `int` (Chave estrangeira referenciando `culturas.id_cultura`).
- **`id_canteiro`**: `int` (Chave estrangeira referenciando `canteiros.id_canteiro`).
- **`data_plantio`**: `date` (Formato ISO-8601 `YYYY-MM-DD`).
- **`status`**: `enum` (`CRESCIMENTO` | `COLHIDO` | `PERDIDO`).
- **`peso_colhido`**: `float` (Opcional/Nullable, valor mínimo: 0.0 kg).

### 2.6. Tarefa (`Tarefa` / `TarefaInput` / `TarefaInsumo`)
- **`id_tarefa`**: `int` (Chave primária).
- **`id_usuario`**: `int` (Chave estrangeira referenciando `usuarios.id_usuario`).
- **`id_canteiro`**: `int` (Opcional/Nullable, chave estrangeira para `canteiros.id_canteiro`).
- **`descricao`**: `string` (Obrigatório, máx 255 caracteres).
- **`data_tarefa`**: `date` (Formato ISO-8601 `YYYY-MM-DD`).
- **`hora_inicio`**: `time` (Formato `HH:MM:SS`).
- **`hora_fim`**: `time` (Formato `HH:MM:SS`, deve ser estritamente posterior a `hora_inicio`).
- **`status`**: `enum` (`PENDENTE` | `CONCLUIDA` | `CANCELADA`).

### 2.7. Autenticação e Segurança
- **`LoginRequestDTO`**: `email` (e-mail válido) e `senha` (`str`).
- **`TokenResponseDTO`**: `access_token` (`str`) e `token_type` (`"bearer"`).
- **`TokenPayload`**: `sub` (ID do usuário), `email`, `perfil`, `role`, `iat`, `exp`.

### 2.8. Resposta de Erro Semântica (RFC 9457 — Problem Details)
Todas as falhas de execução retornam `application/problem+json` contendo:
- **`type`**: URI única do tipo de erro (ex.: `https://api.hortafamiliar.dev/errors/forbidden`).
- **`title`**: Resumo textual curto da condição de erro.
- **`status`**: Código HTTP numérico (`400`, `401`, `403`, `404`, `409`, `422`, `500`).
- **`detail`**: Descrição contextualizada da ocorrência.
- **`instance`**: Caminho da URI requisitada.
- **`invalidParams`**: Lista opcional de objetos `{"name": "<campo>", "reason": "<motivo>"}` obrigatória para status 422 e 400.

---

## 3. Matriz de Endpoints e Controle de Acesso (RBAC)

| Método | Endpoint | Descrição | Permissão (RBAC) | Sucesso | Erros Possíveis |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **POST** | `/auth/login` | Autenticação por e-mail e senha gerando JWT | Aberto | `200 OK` | `401`, `422` |
| **GET** | `/auth/me` | Retorna o perfil do usuário logado | Autenticado | `200 OK` | `401` |
| **GET** | `/usuarios` | Lista todos os usuários cadastrados | `ADMIN` | `200 OK` | `401`, `403` |
| **POST** | `/usuarios` | Cadastra novo usuário com senha criptografada | `ADMIN` | `201 Created` | `401`, `403`, `409`, `422` |
| **GET** | `/usuarios/{id}` | Busca usuário por ID | `ADMIN` | `200 OK` | `401`, `403`, `404` |
| **PUT** | `/usuarios/{id}` | Atualiza dados cadastrais de usuário | `ADMIN` | `200 OK` | `401`, `403`, `404`, `409`, `422` |
| **DELETE**| `/usuarios/{id}` | Remove permanentemente um usuário | `ADMIN` | `204 No Content` | `401`, `403`, `404` |
| **GET** | `/culturas` | Lista todas as culturas agrícolas | Aberto / Geral | `200 OK` | - |
| **POST** | `/culturas` | Cadastra nova variedade de cultura | `ADMIN` | `201 Created` | `401`, `403`, `409`, `422` |
| **GET** | `/culturas/{id}` | Busca dados técnicos de uma cultura | Aberto / Geral | `200 OK` | `404` |
| **PUT** | `/culturas/{id}` | Atualiza dados da cultura | `ADMIN` | `200 OK` | `401`, `403`, `404`, `409`, `422` |
| **DELETE**| `/culturas/{id}` | Remove cultura (bloqueia se houver plantios) | `ADMIN` | `204 No Content` | `401`, `403`, `404`, `409` |
| **GET** | `/canteiros` | Lista todos os canteiros da horta | Aberto / Geral | `200 OK` | - |
| **POST** | `/canteiros` | Cria novo canteiro com área em m² | `ADMIN` | `201 Created` | `401`, `403`, `409`, `422` |
| **GET** | `/canteiros/{id}` | Busca detalhes do canteiro | Aberto / Geral | `200 OK` | `404` |
| **GET** | `/canteiros/{id}/tarefas` | Tarefas do canteiro (**Eager Loading / selectinload**)| Aberto / Geral | `200 OK` | `404` |
| **PUT** | `/canteiros/{id}` | Atualiza dados do canteiro | `ADMIN` | `200 OK` | `401`, `403`, `404`, `409`, `422` |
| **DELETE**| `/canteiros/{id}` | Remove canteiro (bloqueia se houver vínculos) | `ADMIN` | `204 No Content` | `401`, `403`, `404`, `409` |
| **GET** | `/insumos` | Lista insumos com saldo em estoque | Aberto / Geral | `200 OK` | - |
| **POST** | `/insumos` | Cadastra novo insumo | `ADMIN` | `201 Created` | `401`, `403`, `422` |
| **GET** | `/insumos/{id}` | Consulta detalhes de estoque do insumo | Aberto / Geral | `200 OK` | `404` |
| **PUT** | `/insumos/{id}` | Atualiza cadastro e estoque do insumo | `ADMIN` | `200 OK` | `401`, `403`, `404`, `422` |
| **DELETE**| `/insumos/{id}` | Deleta insumo (bloqueia se já utilizado) | `ADMIN` | `204 No Content` | `401`, `403`, `404`, `409` |
| **GET** | `/plantios` | Lista histórico e plantios em andamento | Aberto / Geral | `200 OK` | - |
| **POST** | `/plantios` | Inicia novo plantio em canteiro | Autenticado | `201 Created` | `401`, `404`, `422` |
| **GET** | `/plantios/{id}` | Busca plantio por ID | Aberto / Geral | `200 OK` | `404` |
| **PUT** | `/plantios/{id}` | Altera status e peso colhido do plantio | Autenticado | `200 OK` | `401`, `404`, `422` |
| **DELETE**| `/plantios/{id}` | Remove registro de plantio | `ADMIN` | `204 No Content` | `401`, `403`, `404` |
| **GET** | `/plantios/{id}/insumos` | Lista insumos gastos no plantio | Aberto / Geral | `200 OK` | `404` |
| **POST** | `/plantios/{id}/insumos` | Vincula insumo (**desconta do estoque**) | Autenticado | `201 Created` | `400`, `401`, `404`, `422` |
| **DELETE**| `/plantios/{id}/insumos/{id_insumo}` | Remove insumo (**estorna ao estoque**) | Autenticado | `204 No Content` | `401`, `404` |
| **GET** | `/tarefas` | Lista tarefas agendadas e concluídas | Aberto / Geral | `200 OK` | - |
| **POST** | `/tarefas` | Agenda tarefa (**valida choque de horário**) | Autenticado | `201 Created` | `400`, `401`, `404`, `409`, `422` |
| **GET** | `/tarefas/{id}` | Busca tarefa por ID | Aberto / Geral | `200 OK` | `404` |
| **PUT** | `/tarefas/{id}` | Edita horários, responsável ou status | Autenticado | `200 OK` | `400`, `401`, `404`, `409`, `422` |
| **DELETE**| `/tarefas/{id}` | Exclui tarefa permanentemente | `ADMIN` | `204 No Content` | `401`, `403`, `404` |
| **GET** | `/tarefas/{id}/insumos` | Lista insumos gastos na tarefa | Aberto / Geral | `200 OK` | `404` |
| **POST** | `/tarefas/{id}/insumos` | Vincula insumo (**desconta do estoque**) | Autenticado | `201 Created` | `400`, `401`, `404`, `422` |
| **DELETE**| `/tarefas/{id}/insumos/{id_insumo}` | Desvincula insumo (**estorna ao estoque**) | Autenticado | `204 No Content` | `401`, `404` |
| **GET** | `/dashboard/producao` | Relatório agrupado de produtividade por cultura | Aberto / Geral | `200 OK` | - |

*(Nota: Os roteadores `/api/v1/projects` e `/api/v1/tasks` também estão ativos e operam em conformidade total com o modelo de segurança e eager loading acima).*

---

## 4. Regras de Negócio e Integridade Transacional

### 4.1. Lógica Atômica de Consumo e Estorno de Insumos
- Ao executar `POST /plantios/{id}/insumos` ou `POST /tarefas/{id}/insumos`:
  1. A API verifica se o insumo existe.
  2. Verifica se `insumo.quantidade_estoque >= payload.quantidade_utilizada`. Caso insuficiente, dispara erro `400 Bad Request`.
  3. Desconta atomicamente `insumo.quantidade_estoque -= payload.quantidade_utilizada`.
  4. Registra ou incrementa na tabela associativa correspondente.
- Ao executar `DELETE /plantios/{id}/insumos/{id_insumo}` ou `DELETE /tarefas/{id}/insumos/{id_insumo}`:
  1. A API recupera a quantidade registrada no vínculo.
  2. Estorna atomicamente `insumo.quantidade_estoque += vinculo.quantidade_utilizada`.
  3. Remove o registro associativo e confirma a transação (`db.commit()`).

### 4.2. Prevenção de Conflitos de Agendamento em Tarefas
- Não é permitido agendar duas tarefas ativas (status diferente de `CANCELADA`) no mesmo canteiro e mesma data caso haja sobreposição de horários:
  $$\text{Tarefa}_A.\text{hora\_inicio} < \text{Tarefa}_B.\text{hora\_fim} \quad \text{e} \quad \text{Tarefa}_A.\text{hora\_fim} > \text{Tarefa}_B.\text{hora\_inicio}$$
- Se o conflito for detectado, a API rejeita a requisição retornando **`409 Conflict` (RFC 9457)**.

### 4.3. Prevenção do Problema N+1 com Eager Loading
- Na consulta de tarefas por canteiro (`GET /canteiros/{id}/tarefas` ou `GET /api/v1/projects/{projectId}/tasks`), utiliza-se explicitamente:
  ```python
  query = db.query(CanteiroModel).options(selectinload(CanteiroModel.tarefas))
  ```
- Garante o carregamento dos relacionamentos em apenas duas queries SQL otimizadas pelo SQLAlchemy 2.0.

### 4.4. Autenticação JWT e RBAC (Role-Based Access Control)
- **Token JWT:** Gerado no endpoint de login, assinado com algoritmo `HS256`, tempo de expiração padrão de 24 horas.
- **`ADMIN`:** Permissão total de leitura e escrita em todos os endpoints, incluindo a exclusão física (`DELETE`) de tarefas, usuários, canteiros e culturas.
- **`OPERACIONAL`:** Acesso a operações de dia a dia (consulta, registro de tarefas e plantios, controle de insumos). Tentativa de executar `DELETE` em rotas restritas dispara **`403 Forbidden`**.
- Ausência de token em endpoints protegidos dispara **`401 Unauthorized`**.

---

## 5. Modelo Relacional do Banco de Dados (SQLite)

```text
       +---------------+             +----------------+
       |   usuarios    |             |    culturas    |
       +---------------+             +----------------+
       | id_usuario PK |             | id_cultura PK  |
       | nome          |             | nome (UNIQUE)  |
       | email (UNIQUE)|             | tempo_maturacao|
       | senha_hash    |             | espacamento    |
       | perfil        |             +-------+--------+
       +-------+-------+                     |
               |                             | 1:N
               | 1:N                         |
               v                             v
       +---------------+             +----------------+
       |    tarefas    |             |    plantios    |
       +---------------+             +----------------+
       | id_tarefa PK  |             | id_plantio PK  |
       | id_usuario FK |             | id_cultura FK  |
       | id_canteiro FK+---+     +---+ id_canteiro FK |
       | descricao     |   |     |   | data_plantio   |
       | data_tarefa   |   |     |   | status         |
       | hora_inicio   |   |     |   | peso_colhido   |
       | hora_fim      |   |     |   +-------+--------+
       | status        |   |     |           |
       +-------+-------+   |     |           | 1:N
               |           |     |           v
               | 1:N       |     |   +-----------------------+
               v           |     |   |   plantios_insumos    |
       +---------------+   |     |   +-----------------------+
       |tarefas_insumos|   |     |   | id_plantio PK, FK     |
       +---------------+   |     |   | id_insumo  PK, FK     |
       | id_tarefa PK  |   |     |   | quantidade_utilizada  |
       | id_insumo PK  |   |     |   +-----------+-----------+
       | quantidade    |   |     |               |
       +-------+-------+   |     |               |
               |           v     v               |
               |         +---------------+       |
               |         |   canteiros   |       |
               |         +---------------+       |
               |         | id_canteiro PK|       |
               |         | identificacao |       |
               |         | area_m2       |       |
               |         +---------------+       |
               |                                 |
               +----------------+   +------------+
                                |   |
                                v   v
                         +---------------+
                         |    insumos    |
                         +---------------+
                         | id_insumo PK  |
                         | nome          |
                         | tipo          |
                         | qtd_estoque   |
                         | estoque_min   |
                         +---------------+
```

---

## 6. Dados Iniciais de Bootstrap (Seed)

Ao inicializar a API pela primeira vez, a rotina `seed_database()` cria automaticamente:

1. **Usuários:**
   - `admin@fatec.sp.gov.br` (Senha: `admin123` | Perfil: `ADMIN`)
   - `aluno@fatec.sp.gov.br` (Senha: `aluno123` | Perfil: `OPERACIONAL`)
2. **Culturas:**
   - *Alface Crespa* (45 dias, 0.25 m)
   - *Tomate Cereja* (90 dias, 0.50 m)
3. **Canteiros:**
   - *Canteiro Central A1* (12.5 m²)
   - *Canteiro Estufa B2* (20.0 m²)
4. **Insumos:**
   - *Semente de Alface* (100.0 unidades, mínimo: 15.0)
   - *Fertilizante Orgânico NPK* (80.0 kg, mínimo: 10.0)
5. **Plantio e Tarefa Inicial:**
   - Plantio de Alface no Canteiro A1 com 5 sementes consumidas.
   - Tarefa matinal atribuída a `aluno@fatec.sp.gov.br` no Canteiro A1 com 2.5 kg de fertilizante consumido.
