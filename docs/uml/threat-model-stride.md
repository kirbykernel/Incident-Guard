# Threat model — STRIDE
```mermaid
| Componente | Categoria | Ameaça |
|---|---|---|
| POST /auth/login | S — Spoofing | Brute force de credenciais |
| POST /auth/login | T — Tampering | SQL injection no campo email |
| POST /auth/login | I — Information Disclosure | Senha exposta em logs de erro |
| POST /auth/login | D — Denial of Service | Sem rate limiting no endpoint |
| POST /auth/login | E — Elevation of Privilege | Bypass de validacao para acesso admin |
| JWT token | S — Spoofing | Forjamento com secret fraco ou vazado |
| JWT token | T — Tampering | Alteracao de payload sem reverificacao |
| JWT token | R — Repudiation | Sem mecanismo de revogacao de tokens |
| JWT token | I — Information Disclosure | Token armazenado em localStorage |
| JWT token | E — Elevation of Privilege | Elevacao de role diretamente no payload |
| POST /webhooks/* | S — Spoofing | Spoofing de fonte de alerta |
| POST /webhooks/* | T — Tampering | Payload injection via campos nao sanitizados |
| POST /webhooks/* | I — Information Disclosure | API Key exposta em logs ou respostas |
| POST /webhooks/* | D — Denial of Service | Flood de requisicoes sem throttling |
| POST /webhooks/* | E — Elevation of Privilege | API Key unica com acesso a todos os recursos |
| PostgreSQL | T — Tampering | SQL injection via parametros de query |
| PostgreSQL | I — Information Disclosure | Porta 5432 acessivel fora da rede interna |
| PostgreSQL | D — Denial of Service | Queries longas sem timeout configurado |
| PostgreSQL | E — Elevation of Privilege | Usuario DB com privilegios de superuser |
| Imagem Docker | S — Spoofing | Imagem base comprometida no registry |
| Imagem Docker | T — Tampering | Dependencia maliciosa no requirements.txt |
| Imagem Docker | I — Information Disclosure | Secrets ou credenciais hardcoded na imagem |
| Imagem Docker | E — Elevation of Privilege | Container executando como root (uid 0) |
| CI/CD pipeline | S — Spoofing | Commit malicioso sem code review |
| CI/CD pipeline | T — Tampering | Alteracao de artifact entre build e deploy |
| CI/CD pipeline | I — Information Disclosure | Secrets em variaveis de ambiente plaintext |
| CI/CD pipeline | E — Elevation of Privilege | Job de pipeline com acesso irrestrito ao cluster |
| Kubernetes cluster | S — Spoofing | Acesso indevido ao kubeconfig |
| Kubernetes cluster | T — Tampering | Pod sem securityContext definido |
| Kubernetes cluster | I — Information Disclosure | Secrets nao criptografados no etcd |
| Kubernetes cluster | D — Denial of Service | Pod sem resource limits (CPU/memory) |
| Kubernetes cluster | E — Elevation of Privilege | ServiceAccount com permissoes excessivas |
```