# 🚀 Zero-VM Deployment Guide

Deploy your screenshot gallery to a custom domain without managing servers!

## 🏆 Recommended: Railway (Easiest)

**Why Railway?** Dead simple, supports Python + static files, custom domains

### Steps:
1. **Connect GitHub:** [railway.app](https://railway.app) → "Deploy from GitHub"
2. **Select repo:** `your-username/vibe-screenshots`
3. **Wait for first deploy** (will use demo token initially)
4. **Set environment variable:**
   - Go to Variables tab in Railway dashboard
   - Add `UPLOAD_TOKEN` = `your-secret-token-here`
   - Service will auto-redeploy
5. **Custom domain:** Railway dashboard → Settings → Domains
6. **Test health:** Visit `/health` to verify deployment

**Cost:** $5/month for hobby plan  
**Features:** Auto-deploy, custom domains, zero config

### Railway Troubleshooting:
- **Build fails?** Check Deployments tab for logs
- **Health check fails?** Visit `/health` to see detailed status
- **Upload not working?** Verify `UPLOAD_TOKEN` is set in Variables
- **Static files not loading?** Railway automatically handles static mounting

---

## 🥈 Alternative: Render.com (Free Tier)

**Why Render?** Free tier available, simple setup

### Steps:
1. **Connect GitHub:** [render.com](https://render.com) → "New Web Service"
2. **Select repo:** `your-username/vibe-screenshots`
3. **Settings:**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python railway_app.py`
4. **Environment:**
   - `UPLOAD_TOKEN` = `your-secret-token-here`
5. **Custom domain:** Render dashboard → Settings → Custom Domains

**Cost:** Free (with limitations), $7/month for better performance  
**Features:** Free tier, auto-deploy, SSL included

---

## 🔧 Advanced: Fly.io (Docker)

**Why Fly.io?** Fast global deployment, Docker-based

### Steps:
1. **Install CLI:** `curl -L https://fly.io/install.sh | sh`
2. **Login:** `fly auth login`
3. **Deploy:** `fly deploy`
4. **Set secrets:** `fly secrets set UPLOAD_TOKEN=your-secret-token`
5. **Custom domain:** `fly certs add yourdomain.com`

**Cost:** Pay-as-you-go, ~$2-5/month  
**Features:** Global edge, persistent storage, very fast

---

## 🐳 Self-Host with Docker

**Why Docker?** Run anywhere, consistent environment

### Local/VPS deployment:
```bash
# Build image
docker build -t vibe-screenshots .

# Run container
docker run -p 8000:8000 \
  -e UPLOAD_TOKEN=your-secret-token \
  -v ./screenshots:/app/source \
  vibe-screenshots
```

### With docker-compose:
```yaml
version: '3.8'
services:
  vibe-screenshots:
    build: .
    ports:
      - "8000:8000"
    environment:
      - UPLOAD_TOKEN=your-secret-token
    volumes:
      - ./screenshots:/app/source
```

---

## 📋 Deployment Checklist

### Before deploying:
- [ ] Set a secure `UPLOAD_TOKEN` (not the default!)
- [ ] Test locally with `./start_dev.sh`
- [ ] Commit all changes to GitHub

### After deploying:
- [ ] Test upload functionality at `/upload`
- [ ] Verify gallery displays at `/`
- [ ] Set up custom domain
- [ ] Test from mobile device

### Security notes:
- Change the default upload token!
- Consider adding rate limiting for public sites
- Monitor usage/costs on your chosen platform

---

## 🆚 Platform Comparison

| Platform | Setup Time | Cost | Custom Domain | Auto-deploy | Best For |
|----------|------------|------|---------------|-------------|----------|
| **Railway** | 5 min | $5/mo | ✅ Free | ✅ | Easiest option |
| **Render** | 5 min | Free/$7 | ✅ Free | ✅ | Budget-conscious |
| **Fly.io** | 10 min | $2-5/mo | ✅ Free | ✅ | Performance focused |
| **Docker** | 15 min | VPS cost | Manual | Manual | Full control |

## 🎯 Quick Start Recommendation

**For beginners:** Use Railway - it's the easiest and most reliable  
**For free tier:** Use Render - generous free tier  
**For performance:** Use Fly.io - global edge network  
**For control:** Use Docker on your preferred VPS

All options give you a custom domain and eliminate server management! 🎉