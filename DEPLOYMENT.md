# Deployment Instructions

## One-Time Setup (Switch to Production Mode)

**Run this ONCE to configure nginx for production:**

```bash
cd ~/TicketingSDT
sudo ./setup-production.sh
```

This script will:
- Backup your current nginx config
- Switch from dev server (port 3002) to production mode (serving built files)
- Test and reload nginx

## Every Deployment (After git pull)

```bash
cd ~/TicketingSDT
chmod +x deploy.sh
./deploy.sh
```

That's it! The script will:
1. Build the frontend
2. Run database migrations
3. Restart the backend

## Manual Steps (if needed)

**View backend logs:**
```bash
tail -f ~/TicketingSDT/nohup.out
```

**Check backend status:**
```bash
ps aux | grep uvicorn
```

**Kill dev servers (if running):**
```bash
pkill -9 -f "npm run dev"
```
