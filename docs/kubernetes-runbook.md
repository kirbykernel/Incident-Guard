# Kubernetes Runbook — IncidentGuard

Full deployment sequence for a local minikube cluster, from an empty machine to a
working, hardened deployment. This doubles as the **disaster-recovery procedure**:
every step below is reproducible from this repository, except the credentials.

---

## Prerequisites

| Tool | Notes |
|---|---|
| Docker Desktop | must be running — minikube uses it as the driver |
| minikube | ≥ v1.33 |
| kubectl | ≥ v1.30 |
| helm | v3 — used to install Gatekeeper |

---

## 1. Create the cluster

```bash
minikube start --driver=docker --cni=calico
```

⚠️ **`--cni=calico` is not optional.** minikube's default CNI does not enforce
NetworkPolicies — it accepts them, stores them, and lists them, while every packet
flows through unfiltered. Without an enforcing CNI the network policies in
`k8s/*/networkpolicy.yaml` are documentation, not controls.

Verify enforcement is available:

```bash
kubectl get pods -n kube-system | grep calico    # expect calico-node + calico-kube-controllers
```

## 2. Enable the ingress controller

```bash
minikube addons enable ingress
kubectl wait --for=condition=ready pod -l app.kubernetes.io/component=controller \
  -n ingress-nginx --timeout=180s
```

## 3. Install Gatekeeper (policy-as-code)

```bash
helm repo add gatekeeper https://open-policy-agent.github.io/gatekeeper/charts
helm repo update
helm install gatekeeper/gatekeeper --name-template=gatekeeper \
  --namespace gatekeeper-system --create-namespace
```

Verified against chart **v3.23.0**.

## 4. Build and load the application images

minikube's container runtime has its own image store, separate from the host's
Docker. Locally-built images must be explicitly loaded into the node.

```bash
docker build -t incidentguard-backend:v2 ./backend
docker build --build-arg VITE_API_BASE_URL="" -t incidentguard-frontend:v4 ./frontend

minikube image load incidentguard-backend:v2
minikube image load incidentguard-frontend:v4
```

**Image tags are versioned deliberately** (`:v2`, `:v4`) — never rebuild an existing
tag in place. With `imagePullPolicy: IfNotPresent`, the node keeps serving the stale
copy and the change silently never lands. If manifests reference newer tags than
those above, build and load those instead.

`VITE_API_BASE_URL=""` produces relative `/api` URLs — the frontend and API are
served from the same origin through the Ingress (no CORS).

Postgres is pulled from the registry by digest; no load required.

## 5. Namespace

```bash
kubectl apply -f k8s/namespace.yaml
```

## 6. Bootstrap secrets

```bash
./scripts/k8s-bootstrap-secrets.sh
```

Creates `postgres-credentials`, `app-db-credentials`, and `backend-secrets` with
freshly generated random values.

## 7. Deploy PostgreSQL

```bash
kubectl apply -f k8s/postgres/
kubectl wait --for=condition=ready pod postgres-0 -n incidentguard --timeout=180s
```

## 8. Create the least-privilege database role

```bash
./scripts/k8s-bootstrap-db-roles.sh
```

Must run **after** Postgres is ready — it executes `CREATE ROLE` inside the running
database. Reads the password back from `app-db-credentials` so both sides of the
credential match.

Creates `incidentguard_app`: DML only (SELECT/INSERT/UPDATE/DELETE), no DDL. The
application connects as this role; **migrations** connect as the owner. A leaked
application credential cannot drop or alter the schema.

## 9. Deploy the backend

```bash
kubectl apply -f k8s/backend/
kubectl wait --for=condition=complete job/backend-migrate -n incidentguard --timeout=300s
kubectl wait --for=condition=available deployment/backend -n incidentguard --timeout=180s
```

The migration Job runs `alembic upgrade head` **once**, before the application pods
serve traffic — deliberately a Job rather than an entrypoint step, so concurrent
replicas cannot race each other applying schema changes. An initContainer waits for
Postgres to accept connections first (Kubernetes has no `depends_on`).

> **Re-running migrations:** a Job's pod template is immutable. To apply new
> migrations: `kubectl delete job backend-migrate -n incidentguard` then re-apply.

## 10. Deploy the frontend and Ingress

```bash
kubectl apply -f k8s/frontend/
kubectl apply -f k8s/ingress.yaml
```

## 11. Apply the admission policies

```bash
kubectl apply -f k8s/security/opa/template-block-latest.yaml \
              -f k8s/security/opa/template-require-non-root.yaml \
              -f k8s/security/opa/template-require-resources-limit.yaml \
              -f k8s/security/opa/template-require-resources-request.yaml

sleep 10   # let Gatekeeper register the generated CRDs

kubectl apply -f k8s/security/opa/constraint-block-latest.yaml \
              -f k8s/security/opa/constraint-require-non-root.yaml \
              -f k8s/security/opa/constraint-require-resource-limits.yaml \
              -f k8s/security/opa/constraint-require-resource-request.yaml
```

**Templates before constraints** — a Constraint's `kind` only exists once its
ConstraintTemplate has registered the corresponding CRD.

These constraints are set to `deny`. Applied to a live cluster for the first time,
policies should be rolled out with `enforcementAction: dryrun`, audited, remediated,
and only then promoted to `deny`.

## 12. Expose the cluster locally

```bash
minikube tunnel      # keep running in its own terminal
```

Add a hosts entry pointing `incidentguard.local` at `127.0.0.1`:

- **Windows** (as Administrator): `C:\Windows\System32\drivers\etc\hosts`
- **WSL2**: `/etc/hosts` — this is a *separate file*; WSL regenerates its copy at
  boot, so a Windows-side edit is not visible to a running WSL session.

```
127.0.0.1 incidentguard.local
```

---

## Verification

```bash
# everything running
kubectl get pods -n incidentguard

# policies active, no violations
kubectl get constraints

# network policy is actually enforced: this must TIME OUT
kubectl exec -it deploy/frontend -n incidentguard -- nc -zv -w 2 postgres 5432

# app reachable through the Ingress
curl -s http://incidentguard.local/health          # frontend  → "ok"
curl -si http://incidentguard.local/api/v1/auth/me # backend   → 401 (expected: no session)
```

Create the first user (the database is empty after a rebuild):

```bash
curl -s -X POST http://incidentguard.local/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@incidentguard.dev","password":"<password>","full_name":"Admin","role":"admin"}'
```

Then log in at `http://incidentguard.local`.

---

## What is *not* reproducible from Git

By design:

| Item | Why | Recreated by |
|---|---|---|
| Secrets | credentials must never be committed | `scripts/k8s-bootstrap-secrets.sh` |
| `incidentguard_app` DB role | lives inside PostgreSQL, not in a manifest | `scripts/k8s-bootstrap-db-roles.sh` |
| Application data | PVC contents die with the cluster | signup / migrations |

Everything else — namespace, workloads, services, ingress, network policies, RBAC,
admission policies — is declarative and reproducible with `kubectl apply`.

---

## Teardown

```bash
minikube delete
```

Destroys the cluster and its PersistentVolumes. Application data is lost; all
infrastructure is rebuildable from this document.
