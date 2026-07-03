# ============================================================
# IncidentGuard — Frontend Dockerfile
# Stage 1 (builder): build do React com Vite
# Stage 2 (runtime): nginx-alpine servindo arquivos estáticos
# ============================================================

# ---- Stage 1: builder ----
FROM node:20-alpine@sha256:afdf98210b07b586eb71fa22ba2e432e058e4cd1304d31ed60888755b8c865fb AS builder

WORKDIR /build

# Copia manifests de dependências primeiro (cache layer)
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts

# Vite embute variáveis VITE_* no bundle em tempo de build (não em runtime) —
# por isso precisa ser recebida como build arg, e não como env do container.
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

# Copia código e executa build
COPY . .
RUN npm run build


# ---- Stage 2: runtime ----
FROM nginx:1.26-alpine@sha256:b17b00f7ef0038aeb11362157f49006a130628ee711cefcced871405d046f114 AS runtime

LABEL org.opencontainers.image.title="IncidentGuard Frontend"
LABEL org.opencontainers.image.description="Dashboard React do IncidentGuard"

# Remove configuração padrão do nginx
RUN rm /etc/nginx/conf.d/default.conf

# Copia configuração customizada como template — o entrypoint padrão da
# imagem roda envsubst sobre /etc/nginx/templates/*.template -> conf.d/
# na inicialização do container, resolvendo ${VITE_API_BASE_URL} na CSP.
COPY nginx.conf.template /etc/nginx/templates/app.conf.template

# Copia build do React
COPY --from=builder /build/dist /usr/share/nginx/html

# Usuário não-root do nginx
# conf.d precisa ser gravável pelo usuário nginx: o entrypoint da imagem
# roda envsubst sobre /etc/nginx/templates/*.template -> conf.d/ em
# tempo de container-start (não no build), já rodando como usuário nginx.
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /etc/nginx/conf.d && \
    touch /var/run/nginx.pid && \
    chown nginx:nginx /var/run/nginx.pid

USER nginx

EXPOSE 80

# 127.0.0.1 explícito: "localhost" resolve para ::1 antes de 127.0.0.1
# neste musl/Alpine, e o nginx só escuta em 0.0.0.0:80 (IPv4).
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1:80/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
