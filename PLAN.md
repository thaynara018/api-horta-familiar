# PLAN.md — Plano de Implementação Técnico (API Horta Familiar)

**Metodologia:** Spec-Driven Development (SDD)  
**Fonte Única da Verdade:** `horta_api.Apidog.json`  
**Diretrizes Técnicas:** `STYLEGUIDE.md`  
**Governança:** `AGENTS.md`  

---

## Visão Geral da Arquitetura
Implementação da **API Horta Familiar** utilizando Python 3.12+, FastAPI, Pydantic v2 para validação e serialização estrita de dados, SQLAlchemy 2.0 declarativo para mapeamento objeto-relacional (ORM) com SQLite, autenticação Stateless via JWT (`HS256`) e autorização RBAC com os perfis `ADMIN` e `OPERACIONAL`, respostas de erro padronizadas sob a **RFC 9457 (Problem Details)** e cobertura de testes automatizados com `pytest`.

---

## Matriz de RBAC (Controle de Acesso)
- **ADMIN:** Acesso irrestrito a todos os recursos (CRUD de Usuários, Culturas, Canteiros, Insumos, Plantios, Tarefas e visualização do Dashboard).
- **OPERACIONAL:** Gestão operacional diária (listar/consultar recursos, criar/atualizar Plantios e Tarefas, vincular/desvincular insumos, visualizar Dashboard; sem permissão para exclusão de canteiros/culturas ou gestão de usuários).

---

## Checklist Granular de Tarefas

### Fase 1: Estrutura de Diretórios e Dependências
- [x] 1.1 Criar a árvore de diretórios oficial em `src/api/` e `src/api/routers/` e `src/api/tests/`
- [x] 1.2 Criar os arquivos de inicialização de pacote `__init__.py` nos diretórios correspondentes
- [x] 1.3 Criar o arquivo `src/api/requirements.txt` com as dependências fixadas:
  - `fastapi>=0.115.0`
  - `uvicorn[standard]>=0.30.0`
  - `pydantic>=2.9.0`
  - `pydantic-settings>=2.5.0`
  - `sqlalchemy>=2.0.35`
  - `pyjwt>=2.9.0`
  - `pwdlib[argon2]>=0.2.0` ou `passlib[bcrypt]>=1.7.4`
  - `pytest>=8.3.0`
  - `httpx>=0.27.0`

---

### Fase 2: Schemas Pydantic v2 (Apidog + DTOs de Auth e RFC 9457)
- [x] 2.1 Criar `src/api/schemas.py` com `model_config = ConfigDict(from_attributes=True, populate_by_name=True)`
- [x] 2.2 Implementar Enums de domínio espelhando o Apidog:
  - `PerfilUsuarioEnum`: `ADMIN`, `OPERACIONAL`
  - `TipoInsumoEnum`: `SEMENTE`, `FERTILIZANTE`, `FERRAMENTA`
  - `StatusPlantioEnum`: `CRESCIMENTO`, `COLHIDO`, `PERDIDO`
  - `StatusTarefaEnum`: `PENDENTE`, `CONCLUIDA`, `CANCELADA`
- [x] 2.3 Implementar Schemas RFC 9457 (`ApiError` e `InvalidParam`):
  - `type`: URI da falha
  - `title`: Resumo do erro
  - `status`: Código HTTP
  - `detail`: Descrição detalhada
  - `instance`: URI requisitada
  - `invalidParams`: Opcional/Lista de parâmetros inválidos
- [x] 2.4 Implementar DTOs de Autenticação:
  - `LoginRequestDTO` (`email: EmailStr`, `senha: str`)
  - `TokenResponseDTO` (`access_token: str`, `token_type: str = "bearer"`)
  - `UserResponse` / `Usuario` (`id_usuario`, `nome`, `email`, `perfil`)
  - `TokenPayload` (`sub: str`, `email: str`, `perfil: str`, `exp: int`, `iat: int`)
- [x] 2.5 Implementar Schemas de Entidade e Inputs conforme `horta_api.Apidog.json`:
  - `Usuario`, `UsuarioInput` (com validações de tamanho e email)
  - `Cultura`, `CulturaInput` (`tempo_maturacao_dias >= 1`, `espacamento_ideal > 0`)
  - `Canteiro`, `CanteiroInput` (`area_m2 > 0`)
  - `Insumo`, `InsumoInput` (`quantidade_estoque >= 0`, `estoque_minimo >= 0`)
  - `Plantio`, `PlantioInput` (`peso_colhido >= 0`, nullable na saída)
  - `PlantioInsumo`, `InsumoUsoInput` (`quantidade_utilizada > 0`)
  - `Tarefa`, `TarefaInput` (`data_tarefa`, `hora_inicio`, `hora_fim`, `status`)
  - `TarefaInsumo`
  - `DashboardProducaoItem` (`cultura`, `canteiro`, `total_plantios`, `produtividade_total_kg`)

---

### Fase 3: Modelos ORM SQLAlchemy 2.0 e database.py
- [x] 3.1 Criar `src/api/database.py`:
  - Configuração da engine SQLite (`sqlite:///./horta.db` com `check_same_thread=False`)
  - `SessionLocal` com sessão gerenciada
  - Dependência `get_db()` com contexto assíncrono/gerador para injeção no FastAPI
  - Função `init_db()` e `seed_database()` com criação de usuário inicial `ADMIN` para bootstrap
- [x] 3.2 Criar `src/api/models.py` herdando de `DeclarativeBase`:
  - `UsuarioModel` (`usuarios`): `id_usuario`, `nome`, `email` (único), `senha_hash`, `perfil`
  - `CulturaModel` (`culturas`): `id_cultura`, `nome` (único), `tempo_maturacao_dias`, `espacamento_ideal`
  - `CanteiroModel` (`canteiros`): `id_canteiro`, `identificacao` (único), `area_m2`
  - `InsumoModel` (`insumos`): `id_insumo`, `nome`, `tipo`, `quantidade_estoque`, `estoque_minimo`
  - `PlantioModel` (`plantios`): `id_plantio`, `id_cultura` (FK), `id_canteiro` (FK), `data_plantio`, `status`, `peso_colhido`
    - Relações: `cultura = relationship()`, `canteiro = relationship()`, `insumos_utilizados = relationship()`
  - `PlantioInsumoModel` (`plantios_insumos`): chave composta (`id_plantio`, `id_insumo`), `quantidade_utilizada`
  - `TarefaModel` (`tarefas`): `id_tarefa`, `id_usuario` (FK), `id_canteiro` (FK, nullable), `descricao`, `data_tarefa`, `hora_inicio`, `hora_fim`, `status`
    - Relações: `usuario = relationship()`, `canteiro = relationship()`, `insumos_utilizados = relationship()`
  - `TarefaInsumoModel` (`tarefas_insumos`): chave composta (`id_tarefa`, `id_insumo`), `quantidade_utilizada`

---

### Fase 4: Exceções RFC 9457 e Camada de Segurança (JWT + RBAC)
- [x] 4.1 Criar `src/api/exceptions.py`:
  - Hierarquia de exceções de domínio: `AppException`, `NotFoundException`, `ConflictException`, `BadRequestException`, `UnauthorizedException`, `ForbiddenException`
  - Handlers globais de exceção para registrar no FastAPI:
    - Handler para `AppException` e subclasses
    - Handler para `RequestValidationError` do Pydantic (formatando `invalidParams` com nomes dos campos e motivos)
    - Handler para `HTTPException` genérico
    - Handler fallback para `Exception` interna (500)
- [x] 4.2 Criar `src/api/security.py`:
  - Configurações de segurança (`SECRET_KEY`, `ALGORITHM = "HS256"`, `ACCESS_TOKEN_EXPIRE_MINUTES`)
  - Funções utilitárias: `get_password_hash(password: str) -> str`, `verify_password(plain_password: str, hashed_password: str) -> bool`
  - Função `create_access_token(data: dict) -> str`
  - Função `decode_access_token(token: str) -> dict` (com validação estrita de expiração e integridade)
  - Instância do `HTTPBearer(auto_error=False)`
  - Dependência `get_current_user(token, db)` retornando a entidade `UsuarioModel` autenticada ou disparando `401 Unauthorized` RFC 9457
  - Dependência fábrica `require_role(required_roles: list[str])` validando o perfil do usuário ou disparando `403 Forbidden` RFC 9457

---

### Fase 5: Implementação dos Routers e main.py
- [x] 5.1 Criar `src/api/routers/auth.py`:
  - `POST /auth/login`: Autentica com email e senha, retorna JWT token
  - `GET /auth/me`: Retorna os dados do usuário conectado
- [x] 5.2 Criar `src/api/routers/usuarios.py`:
  - `GET /usuarios`: Lista todos os usuários (Requer ADMIN)
  - `POST /usuarios`: Cadastra usuário com validação de unicidade de email e hash de senha (Requer ADMIN)
  - `GET /usuarios/{id}`: Busca por ID (Requer ADMIN)
  - `PUT /usuarios/{id}`: Atualiza dados do usuário (Requer ADMIN)
  - `DELETE /usuarios/{id}`: Remove usuário (Requer ADMIN)
- [x] 5.3 Criar `src/api/routers/culturas.py`:
  - `GET /culturas`: Lista culturas
  - `POST /culturas`: Cadastra cultura (Requer ADMIN)
  - `GET /culturas/{id}`: Busca cultura por ID
  - `PUT /culturas/{id}`: Atualiza cultura (Requer ADMIN)
  - `DELETE /culturas/{id}`: Deleta cultura com validação de plantios associados (Requer ADMIN)
- [x] 5.4 Criar `src/api/routers/canteiros.py`:
  - `GET /canteiros`: Lista canteiros
  - `POST /canteiros`: Cadastra canteiro com unicidade de identificação (Requer ADMIN)
  - `GET /canteiros/{id}`: Busca canteiro por ID
  - `PUT /canteiros/{id}`: Atualiza canteiro (Requer ADMIN)
  - `DELETE /canteiros/{id}`: Deleta canteiro com validação de dependências (Requer ADMIN)
- [x] 5.5 Criar `src/api/routers/insumos.py`:
  - `GET /insumos`: Lista insumos e seus estoques
  - `POST /insumos`: Cadastra insumo (Requer ADMIN)
  - `GET /insumos/{id}`: Busca insumo por ID
  - `PUT /insumos/{id}`: Atualiza dados cadastrais e estoque (Requer ADMIN)
  - `DELETE /insumos/{id}`: Deleta insumo se não houver vínculos (Requer ADMIN)
- [x] 5.6 Criar `src/api/routers/plantios.py`:
  - `GET /plantios`: Lista plantios com carregamento otimizado de cultura e canteiro (`selectinload`)
  - `POST /plantios`: Cria novo plantio
  - `GET /plantios/{id}`: Busca plantio por ID
  - `PUT /plantios/{id}`: Atualiza plantio (status, peso colhido)
  - `DELETE /plantios/{id}`: Deleta plantio
  - `GET /plantios/{id}/insumos`: Lista insumos utilizados no plantio
  - `POST /plantios/{id}/insumos`: Vincula insumo ao plantio e desconta atomicamente do estoque de `insumos`
  - `DELETE /plantios/{id}/insumos/{id_insumo}`: Remove insumo do plantio e estorna atomicamente a quantidade no estoque
- [x] 5.7 Criar `src/api/routers/tarefas.py`:
  - `GET /tarefas`: Lista tarefas com carregamento otimizado de usuário e canteiro
  - `POST /tarefas`: Cria tarefa (com validação de sobreposição de horários para o mesmo canteiro e data)
  - `GET /tarefas/{id}`: Busca tarefa por ID
  - `PUT /tarefas/{id}`: Atualiza tarefa
  - `DELETE /tarefas/{id}`: Deleta tarefa
  - `GET /tarefas/{id}/insumos`: Lista insumos usados na tarefa
  - `POST /tarefas/{id}/insumos`: Vincula insumo e desconta atomicamente do estoque
  - `DELETE /tarefas/{id}/insumos/{id_insumo}`: Remove insumo e estorna atomicamente o estoque
- [x] 5.8 Criar `src/api/routers/dashboard.py`:
  - `GET /dashboard/producao`: Consulta agregada consolidando total de plantios concluídos e produtividade total agrupada por cultura e canteiro
- [x] 5.9 Criar `src/api/main.py`:
  - Instanciação do FastAPI com lifespan para inicialização de tabelas e seed
  - Configuração de CORS e middlewares
  - Registro de todos os exception handlers da RFC 9457
  - Inclusão dos routers com tags organizadas

---

### Fase 6: Suíte Completa de Testes Automatizados (pytest)
- [x] 6.1 Criar `src/api/tests/conftest.py`:
  - Fixture de banco de dados SQLite isolado em memória com recriação por sessão/teste
  - Override da dependência `get_db`
  - Fixtures de client de teste (`TestClient`)
  - Fixtures de headers de autenticação (`admin_headers`, `member_headers`)
- [x] 6.2 Criar `src/api/tests/test_auth.py`:
  - Testes de login com credenciais válidas e inválidas
  - Testes de acesso a endpoints protegidos sem token (`401`)
  - Testes de RBAC: usuário `OPERACIONAL` / `MEMBER` tentando executar ações restritas a `ADMIN` (`403`)
- [x] 6.3 Criar `src/api/tests/test_tasks.py`:
  - Testes de contrato, persistência ORM da coleção Tasks / Tarefas
  - Proteção de rotas, verificação de conflitos de horários e consumo/estorno atômico de insumos
- [x] 6.4 Criar `src/api/tests/test_projects.py`:
  - Testes de contrato e relacionamento 1:N com eager loading (`selectinload`) da coleção Projects / Canteiros
- [x] 6.5 Criar `src/api/tests/test_errors.py`:
  - Verificação de conformidade estrita com RFC 9457 para status 400, 401, 403, 404 e 422
- [x] 6.6 Execução e aprovação de 100% dos testes com pytest comprovada no terminal
