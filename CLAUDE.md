# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Redirector is a Python web application that provides URL redirection with logging capabilities. It consists of two FastAPI servers:
- **Redirect Server**: Captures all incoming requests, logs them to SQLite database, and redirects to a configured target URL
- **Dashboard Server**: Provides a web interface to view logged requests

## Dependencies and Setup

The project uses Python with these key dependencies:
- FastAPI for web servers
- SQLAlchemy for database operations  
- Typer for CLI interface
- Uvicorn as ASGI server
- Jinja2 for HTML templating

Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Application

Main command to run both servers:
```bash
python redirector.py run --redirect "https://target-url.com" --redirect-port 8080 --dashboard-port 3000
```

Optional Cloudflare tunnel:
```bash
python redirector.py run --tunnel --redirect "https://target-url.com"
```

## Architecture

### Core Components

- `redirector.py:11-15`: Global configuration variables for redirect URL and port settings
- `redirector.py:16-41`: Redirect server with middleware that logs all requests to database and performs redirects
- `redirector.py:43-56`: Dashboard server that displays recent log entries from database
- `database.py:9-19`: SQLAlchemy LogEntry model defining the database schema for request logs
- `database.py:21-24`: SQLite database setup and session management

### Request Flow

1. All incoming requests to redirect server hit the middleware at `redirector.py:20-40`
2. Request details (IP, User-Agent, headers, etc.) are logged to SQLite database via LogEntry model
3. Request is redirected to configured target URL with 302 status
4. Dashboard queries the database to show recent logs in HTML table format

### Key Files

- `redirector.py`: Main application with CLI, servers, and routing logic
- `database.py`: SQLAlchemy models and database configuration  
- `templates/dashboard.html`: HTML template for log viewing interface
- `logs.db`: SQLite database file (auto-created)

## Database Schema

The `LogEntry` model captures:
- timestamp, ip, user_agent, method, url, headers
- Uses SQLite with auto-incrementing primary key
- Database file: `logs.db`