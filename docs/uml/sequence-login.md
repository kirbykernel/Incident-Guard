sequenceDiagram
  actor U as Usuario
  participant FE as Frontend React
  participant API as API FastAPI
  participant DB as PostgreSQL

  U->>FE: informa email e senha
  FE->>API: POST /auth/login
  API->>DB: SELECT user WHERE email = ?
  DB-->>API: registro do usuario
  API->>API: verifica bcrypt hash
  API->>API: gera JWT (exp 8h)
  API-->>FE: access_token + expires_in
  FE->>FE: armazena token em memoria
  FE-->>U: redireciona ao dashboard

  Note over FE,API: requisicoes autenticadas subsequentes
  FE->>API: GET /incidents com Bearer token
  API->>API: valida assinatura JWT
  API->>DB: SELECT incidents
  DB-->>API: lista de incidentes
  API-->>FE: incidents[]
