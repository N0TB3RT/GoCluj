FROM node:22-alpine

WORKDIR /app

# Copiem doar fisierele care definesc pachetele pentru un build rapid
COPY package*.json ./
RUN npm ci

# Copiem restul codului sursă
COPY . .

# Expunem portul cerut de docker-compose
EXPOSE 3000

# The browser uses /api; only the Vite server resolves the Docker service name.
ENV VITE_API_URL=""
ENV API_PROXY_TARGET=http://backend:8000

# Pornim serverul
CMD ["npm", "run", "dev"]
