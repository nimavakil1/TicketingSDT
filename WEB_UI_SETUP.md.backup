# AI Support Agent - Web UI Setup

This document describes how to set up and use the Web UI management interface for the AI Support Agent.

## Overview

The Web UI provides a comprehensive dashboard for monitoring and managing the AI Support Agent system:

- **Dashboard**: Real-time statistics and system status
- **Email Queue**: View processed emails and retry queue
- **Tickets**: Browse tickets with AI analysis details
- **AI Decisions**: Review AI decisions and provide feedback
- **Settings**: Configure system parameters
- **Logs**: Real-time log streaming (WebSocket)

## Architecture

The Web UI consists of:
- **Backend**: FastAPI REST API (`src/api/web_api.py`)
- **Authentication**: JWT-based authentication with role-based access
- **Database**: Uses existing SQLAlchemy models with new User table
- **API Documentation**: Auto-generated Swagger/OpenAPI docs at `/docs`

## Setup Instructions

### 1. Install Dependencies

First, install the required Python packages:

```bash
pip install -r requirements.txt
```

New dependencies for Web UI:
- `uvicorn[standard]` - ASGI server
- `python-multipart` - Form data parsing
- `websockets` - WebSocket support
- `pyjwt` - JWT token handling
- `passlib[bcrypt]` - Password hashing
- `python-jose[cryptography]` - JWT encryption

### 2. Configure JWT Secret

Add to your `.env` file:

```bash
# Web UI Configuration
JWT_SECRET_KEY=your-secret-key-here-use-openssl-rand-hex-32
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

Generate a secure secret key:
```bash
openssl rand -hex 32
```

### 3. Initialize Database

The User table will be created automatically on first run. The database migration adds:
- `users` table with username, email, password_hash, role
- Support for admin, operator, and viewer roles

### 4. Create Admin User

Before you can login, create an initial admin user:

```bash
python3 scripts/create_admin_user.py
```

Follow the prompts to create your admin account:
```
Username: admin
Email: admin@example.com
Password: ********
Confirm Password: ********
```

### 5. Start the Web UI Server

Start the FastAPI backend:

```bash
./scripts/start_web_ui.sh
```

Or manually:
```bash
python3 -m uvicorn src.api.web_api:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at:
- API Base: http://localhost:8000
- Interactive Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Authentication

**POST /api/auth/login**
```json
{
  "username": "admin",
  "password": "your-password"
}
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_at": "2025-10-16T15:00:00"
}
```

**GET /api/auth/me**
Returns current user information (requires authentication).

### Dashboard

**GET /api/dashboard/stats**
```json
{
  "emails_processed_today": 45,
  "tickets_active": 23,
  "tickets_escalated": 3,
  "ai_decisions_today": 45,
  "average_confidence": 0.87,
  "emails_in_retry_queue": 2,
  "phase": 1
}
```

### Emails

**GET /api/emails/processed?limit=50&offset=0**
List processed emails with pagination.

**GET /api/emails/retry-queue**
View emails waiting for retry.

### Tickets

**GET /api/tickets?limit=50&offset=0&escalated_only=false**
List tickets with filters.

**GET /api/tickets/{ticket_number}**
Get detailed ticket info including all AI decisions.

### AI Decisions

**GET /api/ai-decisions?limit=100&offset=0**
List all AI decisions with pagination.

**POST /api/ai-decisions/{decision_id}/feedback**
```json
{
  "feedback": "correct",
  "notes": "Good analysis"
}
```

Feedback values: `correct`, `incorrect`, `partially_correct`

### Settings

**GET /api/settings**
Get current system configuration.

**PATCH /api/settings** (Admin only)
```json
{
  "deployment_phase": 2,
  "confidence_threshold": 0.8,
  "ai_temperature": 0.7
}
```

### Real-time Logs

**WebSocket /ws/logs**
Connect to receive real-time log stream.

Example (JavaScript):
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/logs');
ws.onmessage = (event) => {
  console.log('Log:', event.data);
};
```

## Authentication

All endpoints (except `/health` and `/api/auth/login`) require JWT authentication.

Include the token in the Authorization header:
```
Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...
```

### User Roles

- **admin**: Full access, can modify settings
- **operator**: Can view everything and provide feedback
- **viewer**: Read-only access

## CORS Configuration

The API allows requests from:
- http://localhost:3000 (React default)
- http://localhost:5173 (Vite default)

To add more origins, edit `src/api/web_api.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://your-domain.com"],
    ...
)
```

## Testing the API

### Using curl

```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"your-password"}'

# Get dashboard stats (replace TOKEN with your JWT)
curl http://localhost:8000/api/dashboard/stats \
  -H "Authorization: Bearer TOKEN"

# Get tickets
curl http://localhost:8000/api/tickets?limit=10 \
  -H "Authorization: Bearer TOKEN"
```

### Using the Interactive Docs

1. Go to http://localhost:8000/docs
2. Click "Authorize" button
3. Login via `/api/auth/login` to get token
4. Copy the `access_token` from response
5. Click "Authorize" again and enter: `Bearer YOUR_TOKEN`
6. Now you can test all endpoints interactively

## Running Alongside Main Application

The Web UI runs independently of the main email processing loop:

**Terminal 1 - Main Agent**:
```bash
python3 main.py
```

**Terminal 2 - Web UI**:
```bash
./scripts/start_web_ui.sh
```

Both share the same database, so the Web UI displays real-time data from the running agent.

## Security Considerations

### Production Deployment

1. **Change JWT Secret**: Generate a strong secret key
   ```bash
   openssl rand -hex 32
   ```

2. **Use HTTPS**: Deploy behind a reverse proxy (nginx, Caddy)
   ```nginx
   server {
       listen 443 ssl;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

3. **Restrict CORS**: Only allow your frontend domain

4. **Strong Passwords**: Enforce password complexity

5. **Rate Limiting**: Add rate limiting to prevent brute force
   ```python
   from slowapi import Limiter
   limiter = Limiter(key_func=get_remote_address)

   @app.post("/api/auth/login")
   @limiter.limit("5/minute")
   async def login(...):
       ...
   ```

6. **Environment Variables**: Never commit secrets
   ```bash
   # .env
   JWT_SECRET_KEY=<strong-secret-here>
   TICKETING_API_PASSWORD=<password>
   ```

## Troubleshooting

### "Could not validate credentials"
- Token expired (24 hour default)
- Wrong JWT secret in `.env`
- Token not included in Authorization header

### "User not found"
- Run `python3 scripts/create_admin_user.py` to create first user

### Import errors
- Install dependencies: `pip install -r requirements.txt`

### Database errors
- Check database permissions: `ls -la data/support_agent.db`
- Tables created automatically on first run

### CORS errors (from browser)
- Check `allow_origins` in `src/api/web_api.py`
- Ensure frontend URL is in allowed origins list

## Next Steps: Frontend Development

To complete the Web UI, you can build a React frontend:

1. **Create React app**:
   ```bash
   npx create-react-app frontend
   cd frontend
   npm install axios react-router-dom recharts
   ```

2. **Key components to build**:
   - Login page
   - Dashboard with stats cards and charts
   - Email queue table with filters
   - Ticket detail view
   - AI decision log with feedback buttons
   - Settings panel
   - Real-time log viewer (WebSocket)

3. **API client** (`src/api/client.js`):
   ```javascript
   import axios from 'axios';

   const API_BASE = 'http://localhost:8000';

   const client = axios.create({
     baseURL: API_BASE,
   });

   client.interceptors.request.use((config) => {
     const token = localStorage.getItem('token');
     if (token) {
       config.headers.Authorization = `Bearer ${token}`;
     }
     return config;
   });

   export default client;
   ```

4. **Example Dashboard component**:
   ```jsx
   import { useEffect, useState } from 'react';
   import client from './api/client';

   function Dashboard() {
     const [stats, setStats] = useState(null);

     useEffect(() => {
       client.get('/api/dashboard/stats')
         .then(res => setStats(res.data));
     }, []);

     if (!stats) return <div>Loading...</div>;

     return (
       <div className="dashboard">
         <h1>AI Support Agent Dashboard</h1>
         <div className="stats-grid">
           <StatCard title="Emails Today" value={stats.emails_processed_today} />
           <StatCard title="Active Tickets" value={stats.tickets_active} />
           <StatCard title="Escalated" value={stats.tickets_escalated} />
           <StatCard title="Avg Confidence" value={`${(stats.average_confidence * 100).toFixed(1)}%`} />
         </div>
       </div>
     );
   }
   ```

## Support

For issues or questions:
1. Check the logs: `tail -f logs/support_agent.log`
2. Review API docs: http://localhost:8000/docs
3. Check database: `sqlite3 data/support_agent.db`

## API Integration Examples

### Python
```python
import requests

# Login
response = requests.post('http://localhost:8000/api/auth/login', json={
    'username': 'admin',
    'password': 'your-password'
})
token = response.json()['access_token']

# Get stats
headers = {'Authorization': f'Bearer {token}'}
stats = requests.get('http://localhost:8000/api/dashboard/stats', headers=headers)
print(stats.json())
```

### JavaScript/Node.js
```javascript
const axios = require('axios');

async function getStats() {
  // Login
  const loginResp = await axios.post('http://localhost:8000/api/auth/login', {
    username: 'admin',
    password: 'your-password'
  });

  const token = loginResp.data.access_token;

  // Get stats
  const statsResp = await axios.get('http://localhost:8000/api/dashboard/stats', {
    headers: { Authorization: `Bearer ${token}` }
  });

  console.log(statsResp.data);
}
```
