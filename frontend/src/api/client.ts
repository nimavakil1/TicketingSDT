import axios from 'axios';

const client = axios.create({
  baseURL: window.location.hostname === 'localhost'
    ? 'http://localhost:8002'
    : '',  // Use relative URLs in production - nginx proxies /api/ to backend
  headers: {
    'Content-Type': 'application/json',
  },
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
