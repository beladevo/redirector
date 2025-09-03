# Security Policy

## Reporting Security Vulnerabilities

We take security seriously at Redirector. If you discover a security vulnerability, please follow these steps:

### 🚨 **DO NOT** create a public GitHub issue for security vulnerabilities

### What to Include in Your Report

Please provide as much detail as possible:

- **Description** of the vulnerability
- **Steps to reproduce** the issue  
- **Potential impact** assessment
- **Affected versions**
- **Suggested fix** (if you have one)
- **Your contact information** for follow-up

### Our Response Process

1. **Acknowledgment** - We'll acknowledge your report within 48 hours
2. **Assessment** - We'll assess the vulnerability and determine severity
3. **Fix Development** - We'll develop a fix for the issue
4. **Testing** - We'll test the fix thoroughly
5. **Release** - We'll release the fix and security advisory
6. **Recognition** - We'll credit you in our security advisory (if desired)

### Security Best Practices for Users

When using Redirector, please follow these security guidelines:

#### 🔐 Authentication
- Use strong passwords for dashboard authentication
- Change default credentials immediately
- Consider using environment variables for sensitive config

#### 🌐 Network Security
- Run behind a reverse proxy (nginx, cloudflare) in production
- Use HTTPS/TLS termination
- Implement proper firewall rules
- Consider VPN access for sensitive operations

#### 💾 Data Protection  
- Regularly backup your database
- Use encrypted storage for sensitive data
- Implement data retention policies
- Sanitize logs before sharing externally

#### 🐳 Container Security
- Use official Docker images only
- Keep images updated to latest versions
- Run containers as non-root user (default behavior)
- Use Docker secrets for sensitive data

#### 📊 Operational Security
- Monitor logs for suspicious activity
- Implement rate limiting where appropriate
- Use campaign isolation for different operations
- Regularly review access logs

### Known Security Considerations

#### Data Collection
Redirector logs comprehensive request data including:
- IP addresses
- User agents
- HTTP headers
- Request timing
- Optional request bodies (if enabled)

**Important:** Be aware of privacy laws (GDPR, CCPA) and obtain proper consent when collecting user data.

#### Tunnel Security
When using Cloudflare tunnels:
- Tunnel URLs are publicly accessible
- Consider authentication for sensitive operations
- Monitor tunnel logs for unexpected traffic
- Disable tunnels when not needed

#### Database Security
- SQLite database contains all logged data
- Secure database file permissions
- Consider encryption at rest for sensitive data
- Implement backup encryption

### Supported Versions

We provide security updates for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 2.x.x   | ✅ Active support  |
| 1.x.x   | ⚠️ Critical fixes only |
| < 1.0   | ❌ No longer supported |

### Security Hardening Checklist

For production deployments:

- [ ] Enable dashboard authentication
- [ ] Use HTTPS with valid certificates  
- [ ] Configure proper firewall rules
- [ ] Set up log monitoring and alerting
- [ ] Implement backup and recovery procedures
- [ ] Regular security updates
- [ ] Network segmentation where possible
- [ ] Access control and user management

### Legal and Compliance

#### Responsible Use
This tool should only be used:
- With proper authorization
- In compliance with applicable laws
- For legitimate security research
- With respect for privacy rights

#### Prohibited Uses
Do not use Redirector for:
- Unauthorized data collection
- Malicious redirects or phishing
- Privacy violations
- Any illegal activities

### Security Features

Redirector includes several built-in security features:

- **Non-root execution** in Docker containers
- **Sensitive header filtering** (auth tokens, cookies)
- **Rate limiting** capabilities
- **Input validation** on all endpoints
- **Secure defaults** in configuration
- **Audit logging** for security events

### Contact Information

For security-related questions or concerns:

- **General Issues:** GitHub Issues (for non-security bugs)
- **Documentation:** README.md and inline help

### Hall of Fame

We recognize security researchers who help improve Redirector:

<!-- Security researchers will be listed here -->

Thank you for helping keep Redirector secure! 🔒
