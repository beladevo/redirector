"""Main CLI interface for redirector."""
import sys
import threading
import subprocess
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
import uvicorn

from ..core.config import RedirectorConfig, DEFAULT_CONFIG
from ..core.models import DatabaseManager
from .. import INFO_BANNER

# Initialize CLI app and console
app = typer.Typer(
    name="redirector",
    help="Professional URL redirector with campaign tracking and analytics",
    rich_markup_mode="rich"
)
console = Console()

# Global state
running_servers = []
cloudflare_proc = None


@app.command()
def run(
    redirect_url: str = typer.Option(
        "https://example.com", 
        "--redirect", "-r",
        help="Target URL to redirect visitors to"
    ),
    redirect_port: int = typer.Option(
        8080, 
        "--redirect-port", 
        help="Port for redirect server"
    ),
    dashboard_port: int = typer.Option(
        3000, 
        "--dashboard-port", 
        help="Port for dashboard server"
    ),
    campaign: Optional[str] = typer.Option(
        None, 
        "--campaign", "-c",
        help="Campaign name for organizing logs"
    ),
    dashboard_raw: bool = typer.Option(
        False, 
        "--dashboard-raw",
        help="Use raw HTML dashboard (no CSS/JS)"
    ),
    dashboard_auth: Optional[str] = typer.Option(
        None, 
        "--dashboard-auth",
        help="Dashboard authentication in format 'user:password'"
    ),
    store_body: bool = typer.Option(
        False, 
        "--store-body",
        help="Store request bodies (WARNING: Use only in lab environments)"
    ),
    tunnel: bool = typer.Option(
        False, 
        "--tunnel", "-t",
        help="Enable Cloudflare tunnel for redirect server"
    ),
    config_file: Optional[Path] = typer.Option(
        None, 
        "--config",
        help="Load configuration from YAML file"
    ),
    database_path: str = typer.Option(
        "logs.db",
        "--database",
        help="SQLite database path"
    ),
    log_level: str = typer.Option(
        "info",
        "--log-level",
        help="Log level (debug, info, warning, error)"
    )
) -> None:
    """
    Run redirector with redirect server and dashboard.
    
    📊  Professional URL redirection with analytics
    """
    try:
        # Show info banner
        console.print(Panel(
            INFO_BANNER,
            title="📊  REDIRECTOR INFO",
            border_style="blue",
            box=box.DOUBLE
        ))
        
        # Wait for user acknowledgment
        if not typer.confirm("\nDo you acknowledge that you will use this tool responsibly and ethically?"):
            console.print("[red]Tool usage not acknowledged. Exiting.[/red]")
            raise typer.Exit(1)
        
        # Load configuration
        config = RedirectorConfig(
            redirect_url=redirect_url,
            redirect_port=redirect_port,
            dashboard_port=dashboard_port,
            campaign=campaign,
            dashboard_raw=dashboard_raw,
            dashboard_auth=dashboard_auth,
            store_body=store_body,
            tunnel=tunnel,
            database_path=database_path,
            log_level=log_level
        )
        
        # Override with config file if provided
        if config_file:
            if config_file.exists():
                file_config = RedirectorConfig.from_file(config_file)
                # Update config with file values, but keep CLI overrides
                for field in config.__dataclass_fields__:
                    cli_value = getattr(config, field)
                    file_value = getattr(file_config, field)
                    
                    # Use CLI value if it's different from default, otherwise use file value
                    default_config = RedirectorConfig()
                    if getattr(default_config, field) != cli_value:
                        # CLI override
                        continue
                    else:
                        # Use file value
                        setattr(config, field, file_value)
            else:
                console.print(f"[yellow]Config file not found: {config_file}[/yellow]")
        
        # Validate configuration
        try:
            config.validate()
        except ValueError as e:
            console.print(f"[red]Configuration error: {e}[/red]")
            raise typer.Exit(1)
        
        # Initialize database
        db_manager = DatabaseManager(config.database_url)
        db_manager.create_tables()
        db_manager.ensure_campaign_exists(config.campaign)
        
        # Show configuration
        _show_startup_banner(config)
        
        # Start servers
        _start_servers(config)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Shutting down...[/yellow]")
        _cleanup()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def config(
    output_file: Path = typer.Option(
        Path("redirector-config.yaml"),
        "--output", "-o",
        help="Output configuration file path"
    )
) -> None:
    """Generate a configuration file template."""
    try:
        output_file.write_text(DEFAULT_CONFIG, encoding='utf-8')
        console.print(f"[green]Configuration template written to: {output_file}[/green]")
        console.print(f"[blue]Edit the file and use with: redirector run --config {output_file}[/blue]")
    except Exception as e:
        console.print(f"[red]Error writing config file: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def stats(
    database_path: str = typer.Option(
        "logs.db",
        "--database",
        help="SQLite database path"
    ),
    campaign: Optional[str] = typer.Option(
        None,
        "--campaign", "-c",
        help="Show stats for specific campaign"
    )
) -> None:
    """Show campaign statistics."""
    try:
        db_manager = DatabaseManager(f"sqlite:///{database_path}")
        
        # Get campaigns
        campaigns = db_manager.get_campaigns()
        if not campaigns:
            console.print("[yellow]No campaigns found.[/yellow]")
            return
        
        # Show campaign list
        campaign_table = Table(title="Campaigns")
        campaign_table.add_column("Name", style="cyan")
        campaign_table.add_column("Description", style="white")
        campaign_table.add_column("Created", style="green")
        campaign_table.add_column("Status", style="blue")
        
        for camp in campaigns:
            status = "Active" if camp.is_active else "Inactive"
            campaign_table.add_row(
                camp.name,
                camp.description or "",
                camp.created_at.strftime("%Y-%m-%d %H:%M") if camp.created_at else "",
                status
            )
        
        console.print(campaign_table)
        
        # Get stats for specific campaign or overall
        stats_data = db_manager.get_campaign_stats(campaign)
        
        # Show statistics
        stats_table = Table(title=f"Statistics - {campaign or 'All Campaigns'}")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="white")
        
        stats_table.add_row("Total Requests", str(stats_data['total_requests']))
        stats_table.add_row("Recent Requests (24h)", str(stats_data['recent_requests']))
        
        # Method breakdown
        if stats_data['methods']:
            methods_str = ", ".join([f"{method}: {count}" for method, count in stats_data['methods'].items()])
            stats_table.add_row("Methods", methods_str)
        
        console.print(stats_table)
        
        # Top user agents
        if stats_data['top_user_agents']:
            ua_table = Table(title="Top User Agents")
            ua_table.add_column("User Agent", style="cyan")
            ua_table.add_column("Count", style="white")
            
            for ua, count in list(stats_data['top_user_agents'].items())[:5]:
                # Truncate long user agents
                ua_display = ua[:50] + "..." if len(ua) > 50 else ua
                ua_table.add_row(ua_display, str(count))
            
            console.print(ua_table)
        
    except Exception as e:
        console.print(f"[red]Error retrieving stats: {e}[/red]")
        raise typer.Exit(1)


def _show_startup_banner(config: RedirectorConfig) -> None:
    """Show startup banner with configuration."""
    
    # Create info table
    info_table = Table.grid(padding=1)
    info_table.add_column(style="cyan", no_wrap=True)
    info_table.add_column(style="white")
    
    info_table.add_row("🎯 Target URL:", config.redirect_url)
    info_table.add_row("📡 Redirect Server:", f"http://{config.host}:{config.redirect_port}")
    info_table.add_row("📊 Dashboard:", f"http://{config.host}:{config.dashboard_port}")
    info_table.add_row("📋 Campaign:", config.campaign)
    info_table.add_row("💾 Database:", config.database_path)
    
    if config.dashboard_auth:
        info_table.add_row("🔐 Dashboard Auth:", "Enabled")
    
    if config.store_body:
        info_table.add_row("⚠️  Body Storage:", "[red]ENABLED (Lab mode)[/red]")
    
    console.print(Panel(
        info_table,
        title="🚀 Redirector Starting",
        border_style="green",
        box=box.ROUNDED
    ))


def _start_servers(config: RedirectorConfig) -> None:
    """Start redirect and dashboard servers."""
    global cloudflare_proc
    
    # Start Cloudflare tunnel if requested
    if config.tunnel:
        console.print("[blue]🌍 Starting Cloudflare tunnel...[/blue]")
        try:
            cloudflare_proc = subprocess.Popen(
                ["cloudflared", "tunnel", "--url", f"http://localhost:{config.redirect_port}"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Parse tunnel URL
            tunnel_url = None
            for line in iter(cloudflare_proc.stdout.readline, ''):
                if "trycloudflare.com" in line:
                    tunnel_url = line.strip().split()[-1]
                    console.print(f"[green]✅ Public URL: {tunnel_url}[/green]")
                    break
                elif "error" in line.lower():
                    console.print(f"[red]Tunnel error: {line.strip()}[/red]")
                    break
            
        except FileNotFoundError:
            console.print("[yellow]⚠️  cloudflared not found. Install from https://github.com/cloudflare/cloudflared[/yellow]")
        except Exception as e:
            console.print(f"[red]Failed to start tunnel: {e}[/red]")
    
    # Start dashboard in background thread
    dashboard_thread = threading.Thread(
        target=_run_dashboard_server,
        args=(config,),
        daemon=True
    )
    dashboard_thread.start()
    
    # Give dashboard a moment to start
    time.sleep(2)
    
    console.print("[green]✅ Servers starting...[/green]")
    console.print("[blue]Press Ctrl+C to stop[/blue]")
    
    # Start redirect server (blocking)
    _run_redirect_server(config)


def _run_redirect_server(config: RedirectorConfig) -> None:
    """Run the redirect server."""
    from ..servers.redirect import create_redirect_app
    
    app = create_redirect_app(config)
    
    uvicorn.run(
        app,
        host=config.host,
        port=config.redirect_port,
        log_level=config.log_level,
        access_log=True,
        reload=False
    )


def _run_dashboard_server(config: RedirectorConfig) -> None:
    """Run the dashboard server."""
    from ..servers.dashboard import create_dashboard_app
    
    app = create_dashboard_app(config)
    
    uvicorn.run(
        app,
        host=config.host,
        port=config.dashboard_port,
        log_level=config.log_level,
        access_log=False,
        reload=False
    )


def _cleanup() -> None:
    """Cleanup resources on shutdown."""
    global cloudflare_proc
    
    if cloudflare_proc:
        try:
            cloudflare_proc.terminate()
            cloudflare_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cloudflare_proc.kill()
        except Exception:
            pass


if __name__ == "__main__":
    app()