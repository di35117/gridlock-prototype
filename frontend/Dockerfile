# Stage 1: Build the React Application with Vite
FROM node:20-alpine as build

WORKDIR /app

# Accept the MapTiler token as a build argument
ARG VITE_MAPTILER_TOKEN
ENV VITE_MAPTILER_TOKEN=$VITE_MAPTILER_TOKEN

# Copy package files and install dependencies
COPY package*.json ./
RUN npm install

# Copy the rest of the frontend code and build it
COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Copy the Vite build output (dist) to Nginx's serving directory
COPY --from=build /app/dist /usr/share/nginx/html

# Expose port 80 inside the container
EXPOSE 80

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]