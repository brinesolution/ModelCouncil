FROM node:22-alpine AS dependencies
WORKDIR /app
COPY frontend/package.json ./package.json
RUN npm install

FROM node:22-alpine AS build
WORKDIR /app
COPY --from=dependencies /app/node_modules ./node_modules
COPY frontend ./
ARG NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
ENV NEXT_PUBLIC_API_BASE_URL=$NEXT_PUBLIC_API_BASE_URL
RUN npm run build

FROM node:22-alpine AS runtime
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app ./
EXPOSE 3000
CMD ["npm", "run", "start"]
