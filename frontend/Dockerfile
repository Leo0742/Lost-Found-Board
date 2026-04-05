FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install
COPY . .
ARG VITE_API_BASE_URL=/api
ARG YANDEX_MAPS_API_KEY=
ARG YANDEX_MAPS_SUGGEST_API_KEY=
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
ENV YANDEX_MAPS_API_KEY=$YANDEX_MAPS_API_KEY
ENV YANDEX_MAPS_SUGGEST_API_KEY=$YANDEX_MAPS_SUGGEST_API_KEY
RUN npm run build

FROM caddy:2.8-alpine
COPY --from=build /app/dist /srv
COPY Caddyfile /etc/caddy/Caddyfile
