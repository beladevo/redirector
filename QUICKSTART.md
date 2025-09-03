# Quick Start Guide 🚀

Get redirector running in under 5 minutes!

## 📊 About
**Professional URL redirector with comprehensive analytics and campaign tracking!**

---

## Method 1: Direct Python (Fastest)

```bash
# 1. Install dependencies
pip install fastapi uvicorn typer sqlalchemy jinja2 pyyaml rich httpx python-multipart aiofiles

# 2. Run directly
python redirector.py run --redirect https://example.com --campaign quick-test

# 3. Open dashboard
# Browser: http://localhost:3000
# Redirect URL: http://localhost:8080
```

## Method 2: Docker (Recommended)

```bash
# 1. Build and run
docker build -t redirector .
docker run -p 8080:8080 -p 3000:3000 redirector

# Or with docker-compose
docker-compose up --build
```

## Method 3: Package Install

```bash
# 1. Install package
pip install -e .

# 2. Run
redirector run --redirect https://example.com
```

---

## 🎯 What You Get

- **Redirect Server**: http://localhost:8080 → Redirects to your target
- **Dashboard**: http://localhost:3000 → Beautiful analytics interface  
- **API**: http://localhost:3000/api → RESTful API access

## 🔧 Quick Configuration

```bash
# Generate config file
redirector config --output my-config.yaml

# Edit my-config.yaml, then run:
redirector run --config my-config.yaml
```

## 🌍 Public Access with Tunnel

```bash
# Requires cloudflared installed
redirector run --redirect https://example.com --tunnel
```

## 🔐 With Authentication

```bash
redirector run \
  --redirect https://example.com \
  --dashboard-auth admin:password123 \
  --campaign secure-test
```

---

## 🆘 Troubleshooting

### Port Already in Use
```bash
# Use different ports
redirector run --redirect-port 9080 --dashboard-port 4000
```

### Permission Issues
```bash
# Run on high ports (>1024)
redirector run --redirect-port 8080 --dashboard-port 3000
```

### Missing Dependencies
```bash
# Install all requirements
pip install -r requirements.txt
```

---

## 📈 Next Steps

1. **Check the logs**: Visit http://localhost:3000
2. **Try the API**: `curl http://localhost:3000/api/health`
3. **Export data**: Use the export buttons in dashboard
4. **Read the docs**: See README.md for full documentation

**Happy redirecting! 🎯**