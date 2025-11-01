import axios from 'axios';

const client = axios.create({
  baseURL: window.location.hostname === 'localhost'
    ? 'http://localhost:8003'
    : '',  // Use relative URLs in production - nginx proxies /api/ to backend
  // Don't set default Content-Type - let axios auto-detect based on request data
  // (JSON objects get application/json, FormData gets multipart/form-data)
});

// Add auth token to requests
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default client;
