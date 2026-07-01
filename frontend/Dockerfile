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

# Copia código e executa build
COPY . .
RUN npm run build


# ---- Stage 2: runtime ----
FROM nginx:1.26-alpine@sha256:b17b00f7ef0038aeb11362157f49006a130628ee711cefcced871405d046f114 AS runtime

LABEL org.opencontainers.image.title="IncidentGuard Frontend"
LABEL org.opencontainers.image.description="Dashboard React do IncidentGuard"

# Remove configuração padrão do nginx
RUN rm /etc/nginx/conf.d/default.conf

# Copia configuração customizada (sem server tokens, com headers de segurança)
COPY nginx.conf /etc/nginx/conf.d/app.conf

# Copia build do React
COPY --from=builder /build/dist /usr/share/nginx/html

# Usuário não-root do nginx
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    touch /var/run/nginx.pid && \
    chown nginx:nginx /var/run/nginx.pid

USER nginx

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:80/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
