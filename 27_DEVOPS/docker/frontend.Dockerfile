FROM node:22-bookworm-slim

WORKDIR /workspace/21_FRONTEND

COPY 21_FRONTEND/package.json ./
RUN npm install

COPY 21_FRONTEND ./

EXPOSE 3000

CMD ["npm", "run", "dev"]
