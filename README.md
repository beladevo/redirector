# Redirector 🎯

**A flexible request logger and redirector with campaign tracking, analytics, and tunnel support**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://hub.docker.com/)

## ⚡ Quick Start (30 seconds)

### Install & Run

```bash
# Install
pip install redirector

# Run (redirects to your target URL)
redirector run --redirect https://your-target.com

# View dashboard at http://localhost:3000
```

### Docker (One-liner)

```bash
docker run -p 8080:8080 -p 3000:3000 redirector:latest
```

> **Note**: The Docker image is now configured to automatically accept the security notice for non-interactive use.

## ✨ What it does

- **Redirects** all traffic to your target URL
- **Logs** every request (IP, User-Agent, headers, etc.)  
- **Dashboard** to view all logged requests
- **Export** data as CSV/JSON

Perfect for tracking marketing campaigns, testing, or analyzing traffic patterns.

![Demo GIF](docs/demo.gif)

## 🔧 Installation

### Method 1: pip (easiest)

```bash
pip install redirector
```

### Method 2: Docker

```bash
docker run -p 8080:8080 -p 3000:3000 redirector:latest
```

The Docker image automatically accepts the security notice for non-interactive use.

### Method 3: From source

```bash
git clone https://github.com/beladevo/redirector.git
cd redirector
pip install .
```

---

## 💻 Usage

### Basic Usage

```bash
# Simple redirect
redirector run --redirect https://example.com

# With campaign name
redirector run --redirect https://target.com --campaign operation-red

# With authentication
redirector run \
  --redirect https://target.com \
  --campaign secure-op \
  --dashboard-auth admin:password123

# With Cloudflare tunnel
redirector run \
  --redirect https://target.com \
  --campaign public-test \
  --tunnel
```

### Configuration File

Generate a configuration template:

```bash
redirector config --output my-config.yaml
```

Edit the configuration:

```yaml
# Redirector Configuration
redirect_url: https://your-target.com
redirect_port: 8080
dashboard_port: 3000
campaign: my-campaign
dashboard_raw: false
dashboard_auth: admin:secure123
store_body: false
tunnel: false
host: 0.0.0.0
log_level: info
```

Use the configuration:

```bash
redirector run --config my-config.yaml
```

### Advanced Usage

```bash
# Raw dashboard mode (no CSS/JS)
redirector run --redirect https://target.com --dashboard-raw

# Store request bodies (LAB USE ONLY)
redirector run --redirect https://target.com --store-body

# Custom ports
redirector run \
  --redirect https://target.com \
  --redirect-port 9080 \
  --dashboard-port 4000

# Custom database path
redirector run \
  --redirect https://target.com \
  --database /path/to/logs.db
```

---

## 📊 Dashboard Features

### Beautiful UI Mode (Default)
- **Real-time updates** - Auto-refresh every 10 seconds
- **Advanced filtering** - Campaign, time range, IP, User-Agent, method, path
- **Interactive tables** - Sortable columns with pagination
- **Detail modals** - Click any log entry for full details
- **Export buttons** - One-click CSV/JSONL export
- **Statistics cards** - Request counts, methods, top user agents
- **Mobile responsive** - Works perfectly on all devices

### Raw Mode
- **Terminal-style** - Green-on-black hacker aesthetic
- **Lightweight** - No JavaScript, minimal CSS
- **Fast loading** - Optimized for slow connections
- **Auto-refresh** - Simple page reload every 30 seconds

Access the dashboard at `http://localhost:3000` (or your configured port).

---

## 🔗 API Reference

### Base URL
```
http://localhost:3000/api
```

### Endpoints

#### Health Check
```http
GET /api/health
```

#### Campaigns
```http
GET /api/campaigns
POST /api/campaigns
```

#### Logs
```http
GET /api/logs?campaign=test&page=1&per_page=50
GET /api/logs?start_time=2024-01-01T00:00:00Z&end_time=2024-01-02T00:00:00Z
GET /api/logs?ip_filter=192.168&ua_filter=Chrome&method_filter=GET
```

#### Exports
```http
GET /api/logs/export.csv?campaign=test
GET /api/logs/export.jsonl?start_time=2024-01-01T00:00:00Z
```

#### Statistics
```http
GET /api/stats?campaign=specific-campaign
```

### Example API Usage

```python
import httpx

client = httpx.Client(base_url="http://localhost:3000")

# Get recent logs
response = client.get("/api/logs?per_page=10")
logs = response.json()

# Create new campaign
campaign_data = {
    "name": "api-campaign",
    "description": "Created via API"
}
response = client.post("/api/campaigns", json=campaign_data)

# Export logs as CSV
with open("export.csv", "wb") as f:
    with client.stream("GET", "/api/logs/export.csv") as response:
        for chunk in response.iter_bytes():
            f.write(chunk)
```

---

## 🐳 Docker Deployment

### Basic Deployment

```yaml
# docker-compose.yml
version: '3.8'

services:
  redirector:
    image: redirector:latest
    ports:
      - \"8080:8080\"
      - \"3000:3000\"
    environment:
      - REDIRECT_URL=https://your-target.com
      - CAMPAIGN=docker-campaign
    volumes:
      - ./data:/app/data
```

### With Cloudflare Tunnel

```bash
# Enable tunnel profile
docker-compose --profile tunnel up
```

### Production Setup

```yaml
version: '3.8'

services:
  redirector:
    image: redirector:latest
    restart: unless-stopped
    ports:
      - \"8080:8080\"
      - \"3000:3000\"
    environment:
      - REDIRECT_URL=https://your-target.com
      - CAMPAIGN=production-campaign
      - DASHBOARD_AUTH=admin:secure-password-123
    volumes:
      - redirector-data:/app/data
      - redirector-logs:/app/logs
    healthcheck:
      test: [\"CMD\", \"curl\", \"-f\", \"http://localhost:3000/health\"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  redirector-data:
  redirector-logs:
```

---

## 🧪 Development

### Setup Development Environment

```bash
git clone https://github.com/beladevo/redirector.git
cd redirector

# Install with development dependencies
make dev

# Or manually
pip install -e \".[dev]\"
pre-commit install
```

### Development Commands

```bash
# Run development server
make run

# Run with demo configuration
make run-demo

# Format code
make format

# Run linting
make lint

# Run type checking
make typecheck

# Run tests
make test

# Run all quality checks
make check

# Generate config template
make config

# View statistics
make stats
```

### Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# With coverage
pytest --cov=src/redirector --cov-report=html
```

### Project Structure

```
redirector/
├── src/redirector/           # Main package
│   ├── api/                  # API routes and models
│   ├── cli/                  # Command-line interface
│   ├── core/                 # Core functionality
│   ├── dashboard/            # Dashboard server
│   └── servers/              # Redirect and dashboard servers
├── templates/                # Jinja2 templates
├── static/                   # Static assets
├── tests/                    # Test suite
│   ├── unit/                 # Unit tests
│   └── integration/          # Integration tests
├── docs/                     # Documentation
├── Dockerfile               # Container definition
├── docker-compose.yml       # Container orchestration
├── pyproject.toml           # Package configuration
├── Makefile                 # Development commands
└── README.md                # This file
```

---

## 🎯 Use Cases

### Marketing & Analytics
- **Campaign Tracking** - Monitor marketing campaign performance
- **A/B Testing** - Track different redirect variants
- **User Behavior Analysis** - Understand user interaction patterns
- **Traffic Analysis** - Analyze visitor demographics and patterns

### Development & Research
- **API Testing** - Mock external service redirects and analyze responses
- **Integration Testing** - Test redirect behavior in different environments
- **Performance Monitoring** - Track response times and system performance
- **Data Collection** - Gather insights for research and optimization

### Development & Testing
- **API testing** - Mock external service redirects
- **Load testing** - Monitor performance under load
- **Integration testing** - Test redirect behavior
- **Monitoring setup** - Validate logging systems

---

## ⚙️ Configuration Options

### Core Settings
| Setting | Default | Description |
|---------|---------|-------------|
| `redirect_url` | `https://example.com` | Target URL for redirects |
| `redirect_port` | `8080` | Port for redirect server |
| `dashboard_port` | `3000` | Port for dashboard |
| `campaign` | Auto-generated | Campaign name |

### Dashboard Settings
| Setting | Default | Description |
|---------|---------|-------------|
| `dashboard_raw` | `false` | Use raw HTML mode |
| `dashboard_auth` | `null` | Basic auth (user:pass) |

### Logging Settings
| Setting | Default | Description |
|---------|---------|-------------|
| `store_body` | `false` | Store request bodies |
| `database_path` | `logs.db` | SQLite database path |

### Security Settings
| Setting | Default | Description |
|---------|---------|-------------|
| `max_body_size` | `10485760` | Max body size (10MB) |
| `rate_limit` | `null` | Requests per minute |

---

## 📈 Monitoring & Analytics

### Built-in Statistics
- **Request counts** by campaign, method, time period
- **Top user agents** for identifying common browsers/bots
- **Geographic distribution** (via IP analysis)
- **Timing analysis** with response time tracking
- **Traffic patterns** with hourly/daily breakdowns

### Alerting Integration
```python
# Example: Slack webhook integration
import httpx

def send_alert(message):
    webhook_url = "https://hooks.slack.com/..."
    httpx.post(webhook_url, json={"text": message})

# Monitor for specific conditions
logs = redirector_client.get("/api/logs").json()
for log in logs["logs"]:
    if "suspicious-pattern" in log.get("user_agent", ""):
        send_alert(f"Suspicious request from {log['ip']}")
```

---

## 🔒 Security Considerations

### Network Security
- Run behind reverse proxy (nginx, cloudflare) in production
- Use TLS termination for HTTPS
- Implement network segmentation
- Monitor for DDoS attacks

### Data Protection
- Regularly backup database
- Use encrypted storage for sensitive campaigns
- Implement data retention policies
- Sanitize logs before sharing

### Access Control
- Use strong passwords for dashboard authentication
- Limit dashboard access to authorized personnel
- Implement IP whitelisting where possible
- Use VPN access for remote operations

---

## 🤝 Contributing

We welcome contributions! Please read our [Contributing Guide](CONTRIBUTING.md) for details.

### Quick Contribution Setup
```bash
git clone https://github.com/beladevo/redirector.git
cd redirector
make dev
make check  # Run all quality checks
```

### Reporting Issues
Please report security issues privately.
For other issues, use GitHub Issues with the appropriate template.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🏆 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/) for high-performance APIs
- [Typer](https://typer.tiangolo.com/) for beautiful CLIs
- [Pico.css](https://picocss.com/) for elegant styling
- [Alpine.js](https://alpinejs.dev/) for reactive interfaces
- [SQLAlchemy](https://sqlalchemy.org/) for database management

---

## 📞 Support

- **Documentation**: This README and inline help (`redirector --help`)
- **Issues**: [GitHub Issues](https://github.com/beladevo/redirector/issues)
- **Discussions**: [GitHub Discussions](https://github.com/beladevo/redirector/discussions)

---

**Remember: Use this tool responsibly and only with proper authorization. Stay ethical, stay legal! 🛡️**