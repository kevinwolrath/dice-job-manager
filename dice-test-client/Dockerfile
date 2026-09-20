FROM node:20-alpine

WORKDIR /app

# Separate dependency install from source copy so `docker compose build` only
# re-runs `npm install` when package.json actually changes, not on every edit
# to src/.
COPY package.json package-lock.json* ./
RUN npm install

COPY . .

EXPOSE 5173

# --host 0.0.0.0 is required inside a container: Vite's dev server binds to
# 127.0.0.1 by default, which is unreachable from outside the container even
# with the port published in docker-compose.yml.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
