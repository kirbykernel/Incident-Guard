# Security Scanning — decisions and maintenance notes

How the security gates in [`.github/workflows/security.yml`](../.github/workflows/security.yml)
are configured, why each threshold was chosen, and what to revisit over time.

---

## The gates

| Job | Category | Tool | Blocks a merge? |
|---|---|---|---|
| `secrets` | secret scanning (git history) | Gitleaks | ✅ |
| `sast` | static analysis of our source | Semgrep | ✅ |
| `sca (pip-audit)` | Python dependencies | pip-audit | ✅ |
| `sca (npm-audit)` | JavaScript dependencies | npm audit | ✅ |
| `image` | container image / OS packages | Trivy | ✅ |
| `iac` | Kubernetes manifests | Checkov | ⚠️ advisory (`soft_fail`) |

Every gate except Checkov blocks. Checkov is deliberately advisory until its
findings have been triaged — the same *dryrun → audit → remediate → enforce*
sequence used for the Gatekeeper constraints. Promote it once the backlog is
worked through.

---

## Base images: pinned by digest **and** patched at build time

⚠️ **This is the decision most likely to confuse someone later — read this before
changing the `FROM` lines or the upgrade steps.**

Both Dockerfiles pin their base image by SHA256 digest, and then run an OS
package upgrade on top:

```dockerfile
# backend/Dockerfile  (Debian)
RUN apt-get update && apt-get upgrade -y --no-install-recommends ...

# frontend/Dockerfile (Alpine)
RUN apk upgrade --no-cache
```

Those two things look contradictory. They are not — they solve different problems:

- **The digest pin** guarantees we always start from *the same* base image.
  Without it, `FROM python:3.12-slim` means something different every week, and
  a build that worked yesterday can break today with no change in our code.
- **The upgrade step** closes the gap that pinning creates. Base images are
  rebuilt on a slower cadence than distro security updates. A pinned base is
  therefore *guaranteed to drift* — with a fixed digest, the image only gets
  staler as CVEs are disclosed and patched upstream.

**The tradeoff, stated plainly:** the same digest can now produce slightly
different images over time, because `apt-get upgrade` / `apk upgrade` pull
whatever the distro currently ships. We accept weaker byte-for-byte
reproducibility in exchange for not shipping known-vulnerable OS packages. The
application dependencies (`requirements.txt`, `package-lock.json`) remain fully
pinned, so *our* code and its libraries are still deterministic.

### How we arrived here (2026-09-09)

Trivy's first real run reported **30 HIGH** in the backend and **28 (2 CRITICAL)**
in the frontend — all in OS packages, none in application code.

1. **Bumped both base digests.** The pins dated from mid-2024. This alone fixed
   the backend completely (Debian 13.6 already ships the patched `util-linux`
   and `openssl`).
2. **The frontend needed more.** A newer `nginx:1.26-alpine` digest barely
   helped, because the `1.26` tag is built on **Alpine 3.20**, and the fixes only
   exist in later Alpine releases. Compared the alternatives:

   | Base | Alpine | HIGH/CRITICAL |
   |---|---|---|
   | `1.26-alpine` (previous) | 3.20.6 | 28 (2 CRITICAL) |
   | `1.28-alpine` | 3.23.3 | 54 (2 CRITICAL) |
   | `1.29-alpine` | 3.23.4 | 36 |
   | **`stable-alpine`** ✅ | **3.24.1** | **7** |

   Moved to `nginx:stable-alpine` (nginx 1.30.4 / Alpine 3.24.1).
3. **Added the upgrade steps.** The remaining 7 findings (all `libuuid`) were
   fixed in Alpine's repositories but not yet in the published image. `apk upgrade`
   closed them. Final state: **0 HIGH/CRITICAL in both images.**

### Maintenance

- **Bumping the base:** update the digest, rebuild, scan, and *verify the
  assumptions the manifests depend on* — particularly that nginx still runs as
  **uid 101** (`k8s/frontend/deployment.yaml` sets `runAsUser: 101`) and that
  the backend's app user is still **uid 1001**. A base image changing its user
  ID would break the pods with a confusing permission error.
- **Watch the nginx tag, not just the digest.** The lesson from step 2: a tag can
  be pinned to an old distro release that will *never* receive the fixes. When
  findings persist after a digest bump, check `cat /etc/alpine-release` inside
  the image before assuming there is nothing to do.
- Dependabot tracks the Docker, pip, npm and github-actions ecosystems
  ([`.github/dependabot.yml`](../.github/dependabot.yml)). Its PRs are the
  intended remediation path — they are validated by this same workflow before
  merging.

---

## Threshold decisions

**`severity: CRITICAL,HIGH` (Trivy)** — MEDIUM and below are reported by manual
scans but do not gate. A gate that fires on everything gets disabled.

**`ignore-unfixed: true` (Trivy)** — vulnerabilities with no available patch
cannot be acted on. Blocking every build on them makes the gate an obstacle
rather than a control. These still deserve review; they just aren't merge
blockers.

**`--audit-level=high` (npm audit)** — same reasoning. Without it, the job fails
on low-severity advisories in dev-only dependencies.

**`--error` (Semgrep)** — required. Semgrep reports findings and still exits 0 by
default; without this flag the job would pass while reporting problems.

**`fetch-depth: 0` (Gitleaks)** — Gitleaks scans git *history*. The default
shallow clone would hide a credential that was committed and later removed —
which is still a compromised credential.

**Explicit Semgrep rulesets** — one per language in the repo (`python`,
`typescript`, `react`, `dockerfile`). A missing ruleset is a *silent* coverage
gap: Semgrep scans nothing for that language and still exits 0. Check the
"Scanned N files" line when adding a language.

**Pinned action versions** — actions are third-party code running on a runner
that holds a repository token. `@v4`-style tags are mutable; the hardened
practice is pinning to a full commit SHA. Tag pinning is the current compromise;
SHA pinning is the upgrade path.

---

## Triage: reachability before remediation

A scanner reports what is *present*, not what is *exploitable*. Every finding
gets four questions, and only the third is answered by the tool:

1. Is it real?
2. **Is it reachable in this architecture?**
3. Is a fix available?
4. What breaks if we apply it?

Worked examples from this project:

- **`python-multipart`** (7 CVEs) — the vulnerable code is a multipart form
  parser. The API has no endpoint that accepts `multipart/form-data`, so the
  parser is never invoked. Present, not reachable. Fixed anyway, since a patch
  existed.
- **`util-linux` / `libuuid`** (TOCTOU and SUID `mount` escalation) — requires
  invoking a SUID binary. The pods run non-root, drop **all** capabilities
  (`mount` needs `CAP_SYS_ADMIN`), and set `allowPrivilegeEscalation: false`,
  which sets `no_new_privs` and defeats SUID entirely. The package was present;
  the exploitation path was already closed by the pod SecurityContext. This is
  defense in depth working as intended.
- **`bcrypt 4.1.3 → 5.0.0`** — a major bump on password hashing. Verified before
  merging that bcrypt 5 still validates hashes produced by bcrypt 4; otherwise
  every existing user would have been locked out.

**A fix that exists is not a candidate for suppression.** `soft_fail` and
`.trivyignore` are for findings that have been examined and cannot be fixed
now — not for silencing an alert that a single command would resolve.
