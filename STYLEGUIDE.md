# STYLEGUIDE.md — Constituição Técnica (Horta API: ORM & Auth Edition)

> **Nota de Precedência:** A especificação do Apidog (`horta_api.Apidog.json`) é a fonte única da verdade. Nomes de entidades, atributos (`snake_case` nos schemas da Horta), endpoints e papéis (`ADMIN` e `OPERACIONAL`) do Apidog prevalecem sobre quaisquer referências genéricas.

## 1. Stack Tecnológica e Versões Obrigatórias
- **Linguagem:** Python 3.12+ com anotações estáticas de tipo (`typing`, `datetime`, `Enum`, `Annotated`).
- **Framework Web:** FastAPI.
- **Validação e Serialização:** Pydantic v2 (`BaseModel`, `ConfigDict(populate_by_name=True, from_attributes=True)`, `Field`, `@field_validator`).
- **Persistência e ORM:** SQLAlchemy 2.0+ utilizando sintaxe declarativa moderna (`DeclarativeBase`, `Mapped`, `mapped_column`, `relationship`, `ForeignKey`) com banco SQLite (`sqlite:///./horta.db` em execução normal e banco isolado em memória/arquivo temporário nos testes).
- **Segurança, Autenticação e Autorização:** Autenticação Stateless via **JWT (`PyJWT`)** no padrão `Bearer Token` (`HTTPBearer`) e controle de acesso baseado em papéis (**RBAC**: `ADMIN` e `OPERACIONAL`).
- **Suíte de Testes:** `pytest` + `fastapi.testclient.TestClient`.

---

## 2. Arquitetura de Diretórios e Separação de Camadas
Todo o código da API deve respeitar rigorosamente a estrutura abaixo:

```text
src/api/
├── __init__.py
├── main.py          # Instância FastAPI, lifespan (init_db + seed), CORS, middleware e rotas
├── schemas.py       # Contratos Pydantic v2 espelhando fielmente os Data Schemas do Apidog + DTOs de Auth
├── models.py        # Entidades ORM SQLAlchemy 2.0 (Usuario, Cultura, Canteiro, Insumo, Plantio, Tarefa, etc.)
├── database.py      # Engine SQLAlchemy, SessionLocal, get_db (Dependency Injection) e seed inicial
├── security.py      # Geração/validação de JWT, hash de senha e dependências RBAC (get_current_user, require_role)
├── exceptions.py    # Exceções de domínio e handlers globais no padrão RFC 9457 (400, 401, 403, 404, 422)
├── requirements.txt # Dependências estritas do projeto (fastapi, uvicorn, pydantic, sqlalchemy, pyjwt, pwdlib/passlib/bcrypt, pytest, httpx)
├── routers/
│   ├── __init__.py
│   ├── auth.py      # Endpoints de autenticação (/auth/login e /auth/me)
│   ├── usuarios.py  # Endpoints /usuarios
│   ├── culturas.py  # Endpoints /culturas
│   ├── canteiros.py # Endpoints /canteiros
│   ├── insumos.py   # Endpoints /insumos
│   ├── plantios.py  # Endpoints /plantios e sub-rotas de insumos
│   ├── tarefas.py   # Endpoints /tarefas e sub-rotas de insumos
│   └── dashboard.py # Endpoint /dashboard/producao
└── tests/
    ├── __init__.py
    ├── conftest.py      # Override de get_db para banco SQLite isolado de teste e fixtures de tokens JWT
    ├── test_auth.py     # Testes de login, token inválido/ausente (401) e RBAC (403 Forbidden)
    ├── test_usuarios.py # Testes de CRUD de usuários
    ├── test_culturas.py # Testes de CRUD de culturas
    ├── test_canteiros.py# Testes de CRUD de canteiros
    ├── test_insumos.py  # Testes de CRUD de insumos
    ├── test_plantios.py # Testes de plantios e consumo de estoque
    ├── test_tarefas.py  # Testes de tarefas e consumo de estoque
    ├── test_dashboard.py# Testes do dashboard consolidado
    └── test_errors.py   # Testes de conformidade RFC 9457 (400, 401, 403, 404, 422)
```

---

## 3. Regras Inegociáveis de Implementação

### 3.1. Tratamento de Erros Semântico (RFC 9457 / Problem Details)
- É **PROIBIDO** retornar erros no formato padrão do FastAPI (`{"detail": "..."}`).
- Qualquer erro HTTP (`400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`, `409 Conflict`, `422 Unprocessable Entity`) DEVE retornar um JSON compatível com o schema `ApiError`:
  - `type`: URI identificadora do erro:
    - `https://api.hortafamiliar.dev/errors/bad-request` (`400`)
    - `https://api.hortafamiliar.dev/errors/unauthorized` (`401`)
    - `https://api.hortafamiliar.dev/errors/forbidden` (`403`)
    - `https://api.hortafamiliar.dev/errors/not-found` (`404`)
    - `https://api.hortafamiliar.dev/errors/validation-error` (`422`)
    - `https://api.hortafamiliar.dev/errors/conflict` (`409`)
  - `title`: Resumo curto e legível do tipo de erro.
  - `status`: Código HTTP numérico.
  - `detail`: Explicação clara sobre a ocorrência específica.
  - `instance`: Caminho da URI requisitada (`request.url.path`).
  - `invalidParams`: Lista de objetos `{"name": "<campo>", "reason": "<motivo>"}` obrigatória em falhas de validação (`400`/`422`).

### 3.2. Regras de ORM e Prevenção do Problema N+1
- Use exclusivamente **SQLAlchemy 2.0** (`select()`, `Session.scalars()`, `Mapped[...]`, `mapped_column(...)`).
- Relações e chaves estrangeiras explicitamente declaradas.
- Utilização de `selectinload` / `joinedload` onde houver consultas com relacionamentos para evitar queries N+1.
- Toda operação de escrita (`POST`, `PUT`, `DELETE`) deve gerenciar a transação explicitamente (`db.commit()`, `db.refresh()` ou `db.rollback()` em caso de falha).
- Lógica de estoque (consumo e estorno de insumos em plantios e tarefas) implementada via regras de serviço/ORM ou triggers de banco compatíveis com SQLite.

### 3.3. Regras de Autenticação JWT e Autorização RBAC
- Tokens JWT assinados com `HS256` contendo no payload: `sub` (ID do usuário), `email`, `role` (`ADMIN` ou `OPERACIONAL`), `iat` e `exp`.
- Ausência de cabeçalho `Authorization: Bearer <token>`, token malformado ou expirado deve retornar **`401 Unauthorized`** no formato **RFC 9457 (`ApiError`)**.
- Tentativa de acessar recurso restrito sem o papel (`role`) exigido deve retornar **`403 Forbidden`** no formato **RFC 9457 (`ApiError`)**.

### 3.4. Nomenclatura e Fidelidade ao Apidog
- A nomenclatura dos campos de entrada e saída nos schemas DEVE refletir com 100% de fidelidade a especificação do Apidog (`horta_api.Apidog.json`), preservando os identificadores (`id_usuario`, `tempo_maturacao_dias`, `area_m2`, `quantidade_estoque`, `estoque_minimo`, `data_plantio`, `peso_colhido`, `data_tarefa`, `hora_inicio`, `hora_fim`, `quantidade_utilizada`, etc.).
