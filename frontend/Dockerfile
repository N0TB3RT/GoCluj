FROM node:22-alpine

WORKDIR /app

# Copiem doar fisierele care definesc pachetele pentru un build rapid
COPY package*.json ./
RUN npm install

# Copiem restul codului sursă
COPY . .

# Expunem portul cerut de docker-compose
EXPOSE 3000

# Pornim serverul
CMD ["npm", "run", "dev"]