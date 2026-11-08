# 1. Official Node.js lightweight image
FROM node:18-alpine

# 2. Set working directory
WORKDIR /app

# 3. Copy package definitions and install npm modules
COPY package*.json ./
RUN npm install

# 4. Copy React app source code
COPY . .

# 5. Expose React development server port
EXPOSE 3000

# 6. Start React app
CMD ["npm", "start"]

