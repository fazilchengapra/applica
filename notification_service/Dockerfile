# ---- Base ----
FROM node:22-bookworm-slim AS base
WORKDIR /app
COPY package*.json ./

# ---- Development ----
FROM base AS development
RUN npm install
COPY . .
# src/generated/prisma is gitignored, so a fresh clone has no client until it is
# generated. Doing it here rather than relying on a stale copy in the build
# context keeps `npm run dev` working off a clean checkout.
RUN npx prisma generate
EXPOSE 8000
CMD ["npm", "run", "dev"]

# ---- Build ----
FROM base AS build
RUN npm install
COPY . .
# Generated from the schema in this image, not from whatever happened to be in
# the build context. A stale client would compile against fields that no longer
# exist in the schema.
RUN npx prisma generate
RUN npm run build

# ---- Production ----
FROM node:20-alpine AS production
WORKDIR /app
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

COPY package*.json ./
RUN npm install --omit=dev
COPY --from=build /app/dist ./dist

USER appuser
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD node -e "require('http').get('http://localhost:8000/health', r => process.exit(r.statusCode===200?0:1)).on('error', ()=>process.exit(1))"

CMD ["node", "dist/index.js"]