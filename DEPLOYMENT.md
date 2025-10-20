# Deployment Instructions

## One-Time Setup (Switch to Production Mode)

Edit nginx config:
```bash
sudo nano /etc/nginx/sites-available/ai-agent
```

Comment out these lines (add `#` at the start):
```nginx
proxy_pass http://localhost:3002;
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
```

Uncomment these lines (remove `#`):
```nginx
root /home/ai/TicketingSDT/frontend/dist;
try_files $uri $uri/ /index.html;
```

Then:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

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
