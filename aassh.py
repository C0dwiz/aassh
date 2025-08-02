#!/usr/bin/env python3
"""
AASSH - Another Awesome SSH Client (Python Edition)
Interactive SSH client with rich terminal interface
"""

import os
import sys
import argparse
import subprocess
import yaml

from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, NoReturn
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
from rich.panel import Panel

CONFIG_DIR = Path.home() / ".aassh"
CONFIG_FILE = CONFIG_DIR / "config.yml"
VERSION = "1.0.0"

console = Console()


@dataclass
class SSHProfile:
    """SSH profile configuration"""

    name: str
    host: str
    user: Optional[str] = None
    port: Optional[int] = None
    key: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None

    def connection_string(self) -> str:
        """Generate SSH connection string"""
        user_part = f"{self.user}@" if self.user else ""
        port_part = f" -p {self.port}" if self.port else ""
        key_part = f" -i {self.key}" if self.key else ""
        return f"ssh{port_part}{key_part} {user_part}{self.host}"

    def validate(self) -> bool:
        """Validate profile configuration"""
        if not self.host:
            console.print(f"[red]Error: Host missing for profile '{self.name}'[/red]")
            return False
        if self.port and not (0 < self.port <= 65535):
            console.print(
                f"[red]Error: Invalid port number for profile '{self.name}'[/red]"
            )
            return False
        if self.key and not Path(os.path.expanduser(self.key)).exists():
            console.print(
                f"[red]Error: SSH key not found for profile '{self.name}'[/red]"
            )
            return False
        return True


def error_exit(message: str, code: int = 1) -> NoReturn:
    """Display error message and exit"""
    console.print(f"[bold red]Error:[/bold red] {message}")
    sys.exit(code)


def load_config() -> Dict[str, SSHProfile]:
    """Load and parse configuration file"""
    if not CONFIG_FILE.exists():
        console.print(
            Panel(
                f"[bold red]Config file not found:[/bold red] {CONFIG_FILE}\n\n"
                "Please create a configuration file first with:\n"
                f"  [cyan]mkdir -p {CONFIG_DIR}[/cyan]\n"
                f"  [cyan]touch {CONFIG_FILE}[/cyan]\n\n"
                "You can also create a sample config with:\n"
                "  [cyan]aassh --create-sample-config[/cyan]",
                title="Configuration Required",
                border_style="red",
            )
        )
        sys.exit(1)

    try:
        with open(CONFIG_FILE, "r") as f:
            config_data = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        error_exit(f"Error parsing YAML config: {e}")
    except Exception as e:
        error_exit(f"Error reading config file: {e}")

    profiles = {}
    for name, settings in config_data.get("profiles", {}).items():
        try:
            profile = SSHProfile(
                name=name,
                host=settings.get("host", ""),
                user=settings.get("user"),
                port=settings.get("port"),
                key=settings.get("key"),
                description=settings.get("description"),
                tags=settings.get("tags", []),
            )
            if profile.validate():
                profiles[name] = profile
        except Exception as e:
            error_exit(f"Error creating profile '{name}': {e}")

    if not profiles:
        console.print(
            "[yellow]Warning: No valid profiles found in configuration[/yellow]"
        )

    return profiles


def display_profile_table(profiles: Dict[str, SSHProfile]):
    """Display profiles in a rich table"""
    if not profiles:
        console.print("[bold yellow]No profiles available to display[/bold yellow]")
        return

    table = Table(
        title="\n📡 [bold green]Available SSH Profiles[/bold green]",
        show_header=True,
        header_style="bold magenta",
        expand=True,
    )
    table.add_column("Name", style="cyan", width=20)
    table.add_column("Connection", style="yellow")
    table.add_column("Description", style="white")
    table.add_column("Tags", style="green")

    for name, profile in sorted(profiles.items()):
        conn_str = f"{profile.user + '@' if profile.user else ''}{profile.host}"
        if profile.port:
            conn_str += f":{profile.port}"

        tags = ", ".join(profile.tags) if profile.tags else "-"
        desc = profile.description or "No description"

        table.add_row(f"[bold]{name}[/bold]", conn_str, desc, tags)

    console.print(table)
    console.print(f"[dim]Total profiles: {len(profiles)}[/dim]\n")


def run_ssh(profile: SSHProfile):
    """Execute SSH connection"""
    cmd = ["ssh", "-o", "StrictHostKeyChecking=yes"]

    if profile.port:
        cmd.extend(["-p", str(profile.port)])

    if profile.key:
        expanded_key = os.path.expanduser(profile.key)
        cmd.extend(["-i", expanded_key])

    host_str = f"{profile.user}@{profile.host}" if profile.user else profile.host
    cmd.append(host_str)

    console.print(
        f"\n🚀 [bold green]Connecting to [cyan]{profile.name}[/cyan]...[/bold green]"
    )
    console.print(f"🔗 [yellow]{profile.connection_string()}[/yellow]\n")

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        console.print(
            f"[bold red]SSH connection failed (code {e.returncode})[/bold red]"
        )
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Connection terminated by user[/bold yellow]")
    except FileNotFoundError:
        error_exit(
            "SSH client not found! Please ensure OpenSSH is installed and in your PATH"
        )


def interactive_select(profiles: Dict[str, SSHProfile]):
    """Interactive profile selection with rich interface"""
    if not profiles:
        error_exit("No profiles found in configuration!")

    display_profile_table(profiles)

    choices = list(profiles.keys())
    try:
        choice = Prompt.ask(
            "🔍 Select profile (name or number)", choices=choices, show_choices=False
        )
        if choice in profiles:
            run_ssh(profiles[choice])
        else:
            error_exit("Invalid selection!")
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Selection cancelled by user[/bold yellow]")


def show_version():
    """Display version information"""
    console.print(
        Panel(
            f"[bold green]AASSH v{VERSION}[/bold green]\n"
            "📖 GitHub: [underline blue]https://github.com/C0dWiz/aassh[/underline blue]",
            title="Version Information",
            border_style="green",
        )
    )


def create_sample_config():
    """Create sample configuration file"""
    sample_config = """# AASSH Configuration
profiles:
  example_server:
    host: server.example.com  # Required
    user: username            # Optional
    port: 22                  # Optional
    key: ~/.ssh/id_rsa        # Optional
    description: Example server
    tags: [dev, test]

  production:
    host: prod.example.com
    user: admin
    port: 2222
    description: Production server
    tags: [prod, critical]
"""
    try:
        CONFIG_DIR.mkdir(exist_ok=True, parents=True)
        with open(CONFIG_FILE, "w") as f:
            f.write(sample_config)
        console.print(
            Panel(
                f"[bold green]Sample configuration created:[/bold green] {CONFIG_FILE}\n"
                "[yellow]Please edit this file with your actual profiles[/yellow]",
                title="Configuration Created",
                border_style="green",
            )
        )
    except Exception as e:
        error_exit(f"Error creating sample config: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="AASSH - Another Awesome SSH Client (Python Edition)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("profile", nargs="?", help="SSH profile name to connect")
    parser.add_argument(
        "-l", "--list", action="store_true", help="List all available profiles"
    )
    parser.add_argument(
        "-i", "--interactive", action="store_true", help="Interactive profile selection"
    )
    parser.add_argument(
        "-v", "--version", action="store_true", help="Show version information"
    )
    parser.add_argument(
        "--create-sample-config",
        action="store_true",
        help="Create a sample configuration file",
    )

    args = parser.parse_args()

    if args.version:
        show_version()
        return

    if args.create_sample_config:
        create_sample_config()
        return

    profiles = load_config()

    if args.list:
        display_profile_table(profiles)
        return

    if args.interactive:
        interactive_select(profiles)
        return

    if args.profile:
        if args.profile in profiles:
            run_ssh(profiles[args.profile])
        else:
            error_exit(f"Profile '{args.profile}' not found!")
            console.print("Available profiles:")
            for name in sorted(profiles.keys()):
                console.print(f"  - {name}")
        return

    interactive_select(profiles)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Operation cancelled by user[/bold yellow]")
        sys.exit(0)
    except Exception as e:
        error_exit(f"Unexpected error: {e}")
