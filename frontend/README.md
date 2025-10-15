# AI Support Agent - Frontend

Modern React + TypeScript frontend for the AI Support Agent management dashboard.

## Features

- 🔐 **Authentication** - JWT-based secure login
- 📊 **Dashboard** - Real-time statistics and system overview
- 📧 **Email Queue** - Monitor processed emails and retry queue
- 🎫 **Tickets** - View and manage support tickets
- 🤖 **AI Decisions** - Review AI analysis and provide feedback
- ⚙️ **Settings** - Configure system parameters
- 📜 **Logs** - Real-time system log viewer

## Tech Stack

- **React 18** - UI framework
- **TypeScript** - Type safety
- **Vite** - Fast build tool
- **Tailwind CSS** - Styling
- **React Router** - Navigation
- **Axios** - API client
- **Lucide React** - Icons
- **date-fns** - Date formatting

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend API running on port 8002

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev
```

The app will be available at http://localhost:3000

### Build for Production

```bash
# Build optimized production bundle
npm run build

# Preview production build
npm run preview
```

## Project Structure

```
frontend/
├── src/
│   ├── api/              # API client and endpoints
│   │   ├── client.ts     # Axios instance with interceptors
│   │   ├── auth.ts       # Authentication API
│   │   ├── dashboard.ts  # Dashboard stats API
│   │   ├── tickets.ts    # Tickets API
│   │   ├── ai-decisions.ts # AI decisions API
│   │   └── emails.ts     # Emails API
│   ├── components/       # Reusable components
│   │   └── Layout.tsx    # Main layout with sidebar
│   ├── context/          # React context providers
│   │   └── AuthContext.tsx # Authentication context
│   ├── pages/            # Page components
│   │   ├── Login.tsx     # Login page
│   │   ├── Dashboard.tsx # Dashboard page
│   │   ├── Emails.tsx    # Email queue page
│   │   ├── Tickets.tsx   # Tickets list page
│   │   ├── AIDecisions.tsx # AI decisions page
│   │   ├── Settings.tsx  # Settings page
│   │   └── Logs.tsx      # Logs page
│   ├── App.tsx           # Main app component with routing
│   ├── main.tsx          # App entry point
│   └── index.css         # Global styles
├── index.html            # HTML template
├── vite.config.ts        # Vite configuration
├── tailwind.config.js    # Tailwind CSS configuration
├── tsconfig.json         # TypeScript configuration
└── package.json          # Project dependencies

## Configuration

### API Base URL

By default, the app proxies API requests to `http://localhost:8002`. To change this:

1. **Development**: Edit `vite.config.ts` proxy settings
2. **Production**: Set `VITE_API_URL` environment variable

```bash
# .env
VITE_API_URL=http://your-api-server:8002
```

### Proxy Configuration

The Vite dev server proxies API requests:

```typescript
// vite.config.ts
proxy: {
  '/api': {
    target: 'http://localhost:8002',
    changeOrigin: true,
  },
}
```

## Authentication

The app uses JWT authentication with the following flow:

1. User logs in with username/password
2. Backend returns JWT access token
3. Token stored in localStorage
4. Token included in all API requests via Authorization header
5. On 401 error, user redirected to login

### Token Storage

- **Token**: `localStorage.getItem('token')`
- **User Info**: `localStorage.getItem('user')`

## API Integration

All API calls are made through typed client functions:

```typescript
import { dashboardApi } from './api/dashboard';

// Get dashboard stats
const stats = await dashboardApi.getStats();
console.log(stats.emails_processed_today);
```

### Available APIs

- `authApi.login()` - Login
- `authApi.getMe()` - Get current user
- `dashboardApi.getStats()` - Get dashboard statistics
- `ticketsApi.getTickets()` - List tickets
- `ticketsApi.getTicketDetail()` - Get ticket details
- `aiDecisionsApi.getDecisions()` - List AI decisions
- `aiDecisionsApi.submitFeedback()` - Submit feedback
- `emailsApi.getProcessed()` - List processed emails
- `emailsApi.getRetryQueue()` - Get retry queue

## Development

### Run Development Server

```bash
npm run dev
```

- App: http://localhost:3000
- Vite HMR: Fast refresh on file changes

### Type Checking

```bash
npm run build  # Includes type checking
```

### Linting

```bash
npm run lint
```

## Deployment

### Option 1: Static Hosting

Build and deploy to any static hosting service:

```bash
npm run build
# Deploy the 'dist' folder to:
# - Netlify
# - Vercel
# - AWS S3 + CloudFront
# - GitHub Pages
```

### Option 2: Docker

```dockerfile
FROM node:18-alpine as build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Option 3: Serve with Backend

Configure your backend (FastAPI) to serve the built frontend:

```python
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")
```

## Environment Variables

Create `.env` file for development:

```bash
# API Base URL (optional, uses proxy by default)
VITE_API_URL=http://localhost:8002

# Any VITE_ prefixed variable is available in the app
# via import.meta.env.VITE_*
```

## Troubleshooting

### API Connection Issues

**Problem**: API calls fail with network errors

**Solution**:
1. Ensure backend is running on port 8002
2. Check proxy configuration in `vite.config.ts`
3. Verify CORS settings in backend

### Authentication Issues

**Problem**: Login succeeds but subsequent requests fail

**Solution**:
1. Check JWT token expiration (default 24 hours)
2. Verify token is stored in localStorage
3. Check Authorization header in Network tab

### Build Errors

**Problem**: TypeScript errors during build

**Solution**:
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
npm run build
```

## Browser Support

- Chrome/Edge (last 2 versions)
- Firefox (last 2 versions)
- Safari (last 2 versions)

## Performance

- Code splitting by route
- Lazy loading for pages
- Optimized production builds with Vite
- Tree shaking for smaller bundles

## Contributing

When adding new features:

1. Add API types in `src/api/`
2. Create API client functions
3. Add page components in `src/pages/`
4. Update routing in `App.tsx`
5. Add navigation links in `Layout.tsx`

## License

Same as parent project
