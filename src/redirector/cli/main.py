"""Main CLI interface for redirector."""
import sys
import os
import re
import threading
import subprocess
import time
import platform
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
    ),
    host: str = typer.Option(
        "127.0.0.1",
        "--host",
        help="Host to bind servers to (use 0.0.0.0 for Docker)"
    ),
    accept_security_notice: bool = typer.Option(
        False,
        "--accept-security-notice", "-y",
        help="Accept security notice without interactive prompt (for Docker/CI)"
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
            title="⚠️  SECURITY NOTICE",
            border_style="red",
            box=box.DOUBLE
        ))
        
        # Wait for user acknowledgment (unless auto-accepted)
        if not accept_security_notice:
            if not typer.confirm("\nDo you acknowledge that you will use this tool responsibly and ethically?"):
                console.print("[red]Tool usage not acknowledged. Exiting.[/red]")
                raise typer.Exit(1)
        else:
            console.print("[green]✅ Security notice acknowledged via --accept-security-notice flag[/green]")
        
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
            host=host,
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
    
    if config.tunnel:
        if config.tunnel_url:
            info_table.add_row("🌍 Public URL:", config.tunnel_url)
        else:
            info_table.add_row("🌍 Tunnel:", "Starting...")
    
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


def _show_updated_server_info(config: RedirectorConfig) -> None:
    """Show updated server info after tunnel is ready."""
    
    # Create info table
    info_table = Table.grid(padding=1)
    info_table.add_column(style="cyan", no_wrap=True)
    info_table.add_column(style="white", overflow="fold")  # Allow text wrapping for long URLs
    
    info_table.add_row("🎯 Target URL:", config.redirect_url)
    info_table.add_row("📡 Redirect Server:", f"http://{config.host}:{config.redirect_port}")
    info_table.add_row("📊 Dashboard:", f"http://{config.host}:{config.dashboard_port}")
    
    if config.tunnel_url:
        info_table.add_row("🌍 Public URL:", f"[bright_cyan]{config.tunnel_url}[/bright_cyan]")
    
    info_table.add_row("📋 Campaign:", config.campaign)
    
    console.print(Panel(
        info_table,
        title="🌐 Server Information",
        border_style="blue",
        box=box.ROUNDED
    ))


def _start_servers(config: RedirectorConfig) -> None:
    """Start redirect and dashboard servers."""
    global cloudflare_proc
    
    # Start Cloudflare tunnel if requested
    if config.tunnel:
        console.print("[blue]🌍 Starting Cloudflare tunnel...[/blue]")
        
        # First check if cloudflared is available
        if _check_cloudflared_available():
            _start_cloudflared_tunnel(config)
        else:
            console.print("[yellow]⚠️  cloudflared not found.[/yellow]")
            
            if typer.confirm("Would you like to install cloudflared automatically?"):
                if _install_cloudflared():
                    # Try starting tunnel again after successful installation
                    console.print("[blue]Starting tunnel after installation...[/blue]")
                    _start_cloudflared_tunnel(config)
                else:
                    console.print("[yellow]⚠️  Manual installation required. Download from https://github.com/cloudflare/cloudflared[/yellow]")
            else:
                console.print("[yellow]⚠️  Manual installation required. Download from https://github.com/cloudflare/cloudflared[/yellow]")
    
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


def _start_cloudflared_tunnel(config) -> None:
    """Start the cloudflared tunnel."""
    global cloudflare_proc
    
    # Try different command variations
    commands_to_try = [
        ["cloudflared", "tunnel", "--url", f"http://localhost:{config.redirect_port}"],
        ["cloudflared.exe", "tunnel", "--url", f"http://localhost:{config.redirect_port}"],
    ]
    
    # Also try to find cloudflared in common WinGet locations
    if platform.system().lower() == "windows":
        winget_base = os.path.expanduser("~\\AppData\\Local\\Microsoft\\WinGet\\Packages")
        if os.path.exists(winget_base):
            for item in os.listdir(winget_base):
                if "cloudflare.cloudflared" in item.lower():
                    cloudflared_dir = os.path.join(winget_base, item)
                    cloudflared_exe = os.path.join(cloudflared_dir, "cloudflared.exe")
                    if os.path.exists(cloudflared_exe):
                        commands_to_try.insert(0, [cloudflared_exe, "tunnel", "--url", f"http://localhost:{config.redirect_port}"])
                        break
    
    for cmd in commands_to_try:
        try:
            console.print(f"[blue]Trying command: {' '.join(cmd)}[/blue]")
            cloudflare_proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
        
            # Parse tunnel URL with timeout
            tunnel_url = None
            start_time = time.time()
            timeout = 30  # 30 second timeout
            
            while time.time() - start_time < timeout:
                line = cloudflare_proc.stdout.readline()
                if not line:  # Process ended
                    break
                    
                line = line.strip()
                if "trycloudflare.com" in line:
                    # More robust URL extraction
                    # Look for various URL patterns that cloudflared might output
                    url_patterns = [
                        r'https://[a-zA-Z0-9-]+\.trycloudflare\.com',  # Standard pattern
                        r'http://[a-zA-Z0-9-]+\.trycloudflare\.com',   # HTTP variant
                        r'[a-zA-Z0-9-]+\.trycloudflare\.com'           # Domain only
                    ]
                    
                    tunnel_url = None
                    for pattern in url_patterns:
                        url_match = re.search(pattern, line)
                        if url_match:
                            tunnel_url = url_match.group(0)
                            # Ensure it has https://
                            if not tunnel_url.startswith('http'):
                                tunnel_url = f"https://{tunnel_url}"
                            break
                    
                    # If no regex match, try fallback method
                    if not tunnel_url:
                        parts = line.split()
                        for part in parts:
                            if "trycloudflare.com" in part:
                                tunnel_url = part.rstrip('.,;:')
                                if not tunnel_url.startswith('http'):
                                    tunnel_url = f"https://{tunnel_url}"
                                break
                    
                    # Debug: print the full line to see what we're getting
                    console.print(f"[dim]Cloudflared output: {line}[/dim]")
                    console.print(f"[dim]Extracted URL: {tunnel_url}[/dim]")
                    
                    # Validate URL
                    if tunnel_url and tunnel_url.startswith('https://') and '.trycloudflare.com' in tunnel_url:
                        # Store tunnel URL in config for use by dashboard
                        config.tunnel_url = tunnel_url
                        
                        # Display tunnel URL prominently
                        tunnel_table = Table.grid(padding=1)
                        tunnel_table.add_column(style="cyan", no_wrap=True)
                        tunnel_table.add_column(style="white", overflow="fold")  # Allow text wrapping
                        tunnel_table.add_row("🌍 Public Tunnel URL:", f"[bright_cyan]{tunnel_url}[/bright_cyan]")
                    else:
                        console.print(f"[red]Invalid tunnel URL extracted: {tunnel_url}[/red]")
                        console.print(f"[yellow]Full cloudflared line: {line}[/yellow]")
                        continue  # Don't break, keep looking for valid URL
                    
                    console.print(Panel(
                        tunnel_table,
                        title="✅ Cloudflare Tunnel Started",
                        border_style="green",
                        box=box.ROUNDED
                    ))
                    
                    # Also display updated server info with tunnel URL
                    console.print()  # Add some spacing
                    _show_updated_server_info(config)
                    
                    return  # Successfully started tunnel
                elif "error" in line.lower():
                    console.print(f"[red]Tunnel error: {line.strip()}[/red]")
                    break
            
            # Handle timeout case
            if not tunnel_url:
                console.print(f"[yellow]⚠️  Timeout waiting for tunnel URL (waited {timeout}s)[/yellow]")
                console.print("[blue]Tunnel process may still be starting in the background[/blue]")
            
            # If we get here, this command failed, try the next one
            if cloudflare_proc:
                try:
                    cloudflare_proc.terminate()
                except:
                    pass
                    
        except FileNotFoundError:
            console.print(f"[yellow]Command not found: {cmd[0]}[/yellow]")
            continue
        except Exception as e:
            console.print(f"[red]Failed to start tunnel with {cmd[0]}: {e}[/red]")
            continue
    
    # If we get here, all commands failed
    console.print(f"[red]Failed to start tunnel with any available command[/red]")




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


def _refresh_windows_path() -> None:
    """Refresh PATH environment variable on Windows."""
    if platform.system().lower() == "windows":
        try:
            # Refresh environment variables
            import os
            import winreg
            
            # Get system PATH
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as key:
                    system_path = winreg.QueryValueEx(key, "PATH")[0]
            except Exception:
                system_path = ""
            
            # Get user PATH
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
                    user_path = winreg.QueryValueEx(key, "PATH")[0]
            except Exception:
                user_path = ""
            
            # Add common installation paths for cloudflared
            common_paths = [
                r"C:\Program Files\cloudflared",
                r"C:\Program Files (x86)\cloudflared",
                r"C:\Users\%USERNAME%\AppData\Local\Microsoft\WinGet\Packages",
                r"C:\ProgramData\chocolatey\bin",
                os.path.expanduser("~\\AppData\\Local\\Microsoft\\WinGet\\Packages")
            ]
            
            # Build combined PATH
            current_path = os.environ.get("PATH", "")
            paths_to_add = []
            
            for path in common_paths:
                expanded_path = os.path.expandvars(path)
                if os.path.exists(expanded_path) and expanded_path not in current_path:
                    paths_to_add.append(expanded_path)
            
            # Update current process PATH
            if system_path or user_path or paths_to_add:
                path_parts = [p for p in [current_path, system_path, user_path] + paths_to_add if p]
                combined_path = ";".join(path_parts)
                os.environ["PATH"] = combined_path
                console.print("[blue]Refreshed Windows PATH environment[/blue]")
                
                # Also try to find cloudflared in WinGet packages specifically
                winget_base = os.path.expanduser("~\\AppData\\Local\\Microsoft\\WinGet\\Packages")
                if os.path.exists(winget_base):
                    for item in os.listdir(winget_base):
                        if "cloudflare.cloudflared" in item.lower():
                            cloudflared_dir = os.path.join(winget_base, item)
                            if os.path.isdir(cloudflared_dir):
                                os.environ["PATH"] = f"{cloudflared_dir};{os.environ['PATH']}"
                                console.print(f"[blue]Added WinGet cloudflared path: {cloudflared_dir}[/blue]")
                                break
            
        except Exception as e:
            console.print(f"[yellow]Could not refresh PATH: {e}[/yellow]")


def _check_cloudflared_available() -> bool:
    """Check if cloudflared is available in PATH."""
    try:
        # Try different ways to find cloudflared
        commands_to_try = [
            ["cloudflared", "--version"],
            ["cloudflared.exe", "--version"],  # Windows explicit
        ]
        
        for cmd in commands_to_try:
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    console.print(f"[green]✅ cloudflared found: {result.stdout.strip()}[/green]")
                    return True
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
                
        return False
        
    except Exception as e:
        console.print(f"[yellow]Error checking cloudflared: {e}[/yellow]")
        return False


def _run_command_with_output(cmd: list, description: str) -> subprocess.CompletedProcess:
    """Run command and show real-time output."""
    console.print(f"[blue]Running: {' '.join(cmd)}[/blue]")
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    output_lines = []
    while True:
        output = process.stdout.readline()
        if output == '' and process.poll() is not None:
            break
        if output:
            line = output.strip()
            output_lines.append(line)
            console.print(f"[dim]{line}[/dim]")
    
    return_code = process.poll()
    return subprocess.CompletedProcess(cmd, return_code, '\n'.join(output_lines), '')


def _install_cloudflared() -> bool:
    """Install cloudflared based on the current OS."""
    system = platform.system().lower()
    
    console.print(f"[blue]Detecting OS: {system}[/blue]")
    
    try:
        if system == "windows":
            # Windows installation using winget or chocolatey
            console.print("[blue]Installing cloudflared via winget...[/blue]")
            result = _run_command_with_output(
                ["winget", "install", "cloudflare.cloudflared"],
                "Installing via winget"
            )
            
            # Check if already installed or if installation succeeded
            if "already installed" in result.stdout.lower() or "No newer package versions are available" in result.stdout:
                console.print("[yellow]⚠️  cloudflared already installed via winget[/yellow]")
                console.print("[blue]Attempting to refresh PATH and locate cloudflared...[/blue]")
                
                # Refresh Windows PATH
                _refresh_windows_path()
                
                # Check if we can find it after PATH refresh
                if _check_cloudflared_available():
                    return True
                
                # Try to find cloudflared manually in common WinGet locations
                winget_base = os.path.expanduser("~\\AppData\\Local\\Microsoft\\WinGet\\Packages")
                if os.path.exists(winget_base):
                    for item in os.listdir(winget_base):
                        if "cloudflare.cloudflared" in item.lower():
                            cloudflared_dir = os.path.join(winget_base, item)
                            cloudflared_exe = os.path.join(cloudflared_dir, "cloudflared.exe")
                            if os.path.exists(cloudflared_exe):
                                console.print(f"[green]✅ Found cloudflared at: {cloudflared_exe}[/green]")
                                # Add to PATH for this session
                                os.environ["PATH"] = f"{cloudflared_dir};{os.environ.get('PATH', '')}"
                                return True
                    
                console.print("[yellow]cloudflared installed but not accessible. You may need to restart your terminal.[/yellow]")
                console.print("[blue]Try running this command in a new terminal: cloudflared --version[/blue]")
                
                # Return True since it's installed, the tunnel startup will handle the PATH issue
                return True
                
            elif result.returncode != 0:
                # Try chocolatey as fallback
                console.print("[yellow]Winget failed, trying chocolatey...[/yellow]")
                console.print(f"[dim]Winget error: {result.stdout}[/dim]")
                
                # Check if chocolatey is available
                try:
                    choco_check = subprocess.run(["choco", "--version"], capture_output=True, text=True, timeout=5)
                    if choco_check.returncode != 0:
                        console.print("[red]Chocolatey not found. Please install cloudflared manually.[/red]")
                        return False
                except Exception:
                    console.print("[red]Chocolatey not found. Please install cloudflared manually.[/red]")
                    return False
                    
                result = _run_command_with_output(
                    ["choco", "install", "cloudflared", "-y"],
                    "Installing via chocolatey"
                )
                
        elif system == "darwin":  # macOS
            console.print("[blue]Installing cloudflared via Homebrew...[/blue]")
            result = _run_command_with_output(
                ["brew", "install", "cloudflared"],
                "Installing via Homebrew"
            )
            
        elif system == "linux":
            # Linux installation - try apt first, then yum
            console.print("[blue]Installing cloudflared on Linux...[/blue]")
            
            # Check if apt is available (Debian/Ubuntu)
            if subprocess.run(["which", "apt"], capture_output=True).returncode == 0:
                console.print("[blue]Setting up Cloudflare repository...[/blue]")
                
                # Add Cloudflare GPG key and repository
                _run_command_with_output([
                    "sudo", "mkdir", "-p", "--mode=0755", "/usr/share/keyrings"
                ], "Creating keyrings directory")
                
                _run_command_with_output([
                    "sudo", "curl", "-fsSL", "https://pkg.cloudflare.com/cloudflare-main.gpg",
                    "-o", "/usr/share/keyrings/cloudflare-main.gpg"
                ], "Downloading GPG key")
                
                # Create apt sources list
                sources_content = "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared $(lsb_release -cs) main\n"
                console.print("[blue]Adding Cloudflare repository to sources...[/blue]")
                subprocess.run([
                    "sudo", "tee", "/etc/apt/sources.list.d/cloudflared.list"
                ], input=sources_content, text=True, capture_output=True)
                
                _run_command_with_output(["sudo", "apt-get", "update"], "Updating package lists")
                result = _run_command_with_output(
                    ["sudo", "apt-get", "install", "cloudflared", "-y"],
                    "Installing cloudflared"
                )
                
            # Check if yum is available (RedHat/CentOS/Fedora)
            elif subprocess.run(["which", "yum"], capture_output=True).returncode == 0:
                result = _run_command_with_output([
                    "sudo", "yum", "install", "cloudflared", "-y"
                ], "Installing via yum")
                
            # Check if dnf is available (Fedora)
            elif subprocess.run(["which", "dnf"], capture_output=True).returncode == 0:
                result = _run_command_with_output([
                    "sudo", "dnf", "install", "cloudflared", "-y"
                ], "Installing via dnf")
                
            else:
                console.print("[red]Unsupported Linux distribution. Please install cloudflared manually.[/red]")
                return False
                
        else:
            console.print(f"[red]Unsupported OS: {system}[/red]")
            return False
            
        if result.returncode == 0:
            console.print("[green]✅ cloudflared installed successfully![/green]")
            console.print("[blue]Verifying installation...[/blue]")
            
            # Verify installation
            try:
                verify_result = subprocess.run(
                    ["cloudflared", "--version"], 
                    capture_output=True, 
                    text=True, 
                    timeout=10
                )
                if verify_result.returncode == 0:
                    console.print(f"[green]✅ Verification successful: {verify_result.stdout.strip()}[/green]")
                else:
                    console.print("[yellow]⚠️  Installation completed but verification failed[/yellow]")
            except Exception as e:
                console.print(f"[yellow]⚠️  Installation completed but verification failed: {e}[/yellow]")
                
            return True
        else:
            console.print(f"[red]❌ Installation failed (exit code: {result.returncode})[/red]")
            if result.stdout:
                console.print(f"[red]Output: {result.stdout}[/red]")
            return False
            
    except FileNotFoundError as e:
        console.print(f"[red]Installation tool not found: {e}[/red]")
        console.print("[yellow]Please install cloudflared manually from https://github.com/cloudflare/cloudflared[/yellow]")
        return False
    except Exception as e:
        console.print(f"[red]Installation error: {e}[/red]")
        return False


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