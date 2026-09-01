FROM node:22-bookworm-slim

RUN apt-get update \
  && apt-get install -y --no-install-recommends python3 make g++ \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package.json package-lock.json* ./
COPY frontend/package.json frontend/package.json
RUN npm install \
  && npm install --prefix frontend

COPY . .
RUN npm run build --prefix frontend

ENV NODE_ENV=production
ENV PORT=3000
ENV DATABASE_PATH=/app/data/webhook-events.db
ENV PUBLIC_BASE_URL=http://localhost:3000

EXPOSE 3000
VOLUME ["/app/data"]

CMD ["npx", "tsx", "src/server.ts"]
