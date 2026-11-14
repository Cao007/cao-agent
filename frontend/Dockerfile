ARG NODE_IMAGE=node:24-alpine
ARG NGINX_IMAGE=nginx:1.28-alpine
FROM ${NODE_IMAGE} AS development
ARG NPM_REGISTRY=https://registry.npmmirror.com
WORKDIR /app
RUN npm install -g pnpm@10.29.3 --registry=$NPM_REGISTRY
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/.npmrc ./
RUN pnpm install --frozen-lockfile --registry=$NPM_REGISTRY
COPY frontend ./
CMD ["pnpm", "dev"]

FROM development AS build
RUN pnpm build

FROM ${NGINX_IMAGE} AS production
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
