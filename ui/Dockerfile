# syntax=docker/dockerfile:1

FROM node:24-alpine AS deps

RUN corepack enable && corepack prepare pnpm@latest --activate

WORKDIR /app

COPY package.json pnpm-lock.yaml ./

RUN pnpm install --frozen-lockfile


FROM deps AS dev

COPY . .

EXPOSE 5173

CMD ["pnpm", "dev", "--host", "0.0.0.0"]


FROM deps AS builder

COPY . .

RUN pnpm build


FROM nginx:alpine AS prod

COPY --from=builder /app/dist/ /usr/share/nginx/html/

EXPOSE 80
