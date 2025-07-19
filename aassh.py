#!/usr/bin/env python3
"""
AASSH - Another Awesome SSH Client (Python Edition)
Interactive SSH client with rich terminal interface
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional

import yaml
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
from rich import print as rprint

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
        return True


def load_config() -> Dict[str, SSHProfile]:
    """Load and parse configuration file"""
    if not CONFIG_FILE.exists():
        console.print(f"[bold red]Config file not found: {CONFIG_FILE}[/bold red]")
        console.print("Please create a configuration file first with:")
        console.print(f"  [cyan]mkdir -p {CONFIG_DIR}[/cyan]")
        console.print(f"  [cyan]touch {CONFIG_FILE}[/cyan]")
        console.print("See README for configuration examples")
        sys.exit(1)

    try:
        with open(CONFIG_FILE, "r") as f:
            config_data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        console.print(f"[bold red]Error parsing YAML config:[/bold red] {e}")
        sys.exit(1)

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
            console.print(f"[bold red]Error creating profile '{name}': {e}[/bold red]")
            sys.exit(1)

    return profiles


def display_profile_table(profiles: Dict[str, SSHProfile]):
    """Display profiles in a rich table"""
    table = Table(
        title="\n📡 [bold green]Available SSH Profiles[/bold green]",
        show_header=True,
        header_style="bold magenta",
    )
    table.add_column("Name", style="cyan", width=20)
    table.add_column("Connection", style="yellow")
    table.add_column("Description", style="white")
    table.add_column("Tags", style="green")

    for name, profile in profiles.items():
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
    cmd = ["ssh"]

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
        console.print(f"[bold red]SSH connection failed:[/bold red] {e}")
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Connection terminated by user[/bold yellow]")
    except FileNotFoundError:
        console.print("[bold red]Error: SSH client not found![/bold red]")
        console.print("Please ensure OpenSSH is installed and in your PATH")


def interactive_select(profiles: Dict[str, SSHProfile]):
    """Interactive profile selection with rich interface"""
    if not profiles:
        console.print("[bold red]No profiles found in configuration![/bold red]")
        console.print(f"Please edit {CONFIG_FILE} to add profiles")
        sys.exit(1)

    display_profile_table(profiles)

    choices = list(profiles.keys())
    choice = Prompt.ask(
        "🔍 Select profile (number or name)", choices=choices, show_choices=False
    )

    if choice in profiles:
        run_ssh(profiles[choice])
    else:
        console.print("[bold red]Invalid selection![/bold red]")


def show_version():
    """Display version information"""
    console.print(f"[bold green]AASSH v{VERSION}[/bold green]")
    console.print(
        "📖 GitHub: [underline blue]https://github.com/C0dWiz/aassh[/underline blue]"
    )


def create_sample_config():
    """Create sample configuration file"""
    sample_config = """# AASSH Configuration
# Format:
# profiles:
#   profile_name:
#     host: server.example.com  # Required
#     user: username            # Optional
#     port: 22                  # Optional
#     key: ~/.ssh/id_rsa        # Optional
#     description: Production server
#     tags: [prod, web]
"""
    try:
        CONFIG_DIR.mkdir(exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            f.write(sample_config)
        console.print(
            f"[bold green]Sample configuration created:[/bold green] {CONFIG_FILE}"
        )
        console.print(
            "[yellow]Please edit this file with your actual profiles[/yellow]"
        )
    except Exception as e:
        console.print(f"[bold red]Error creating sample config:[/bold red] {e}")


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
            console.print(f"[bold red]Profile '{args.profile}' not found![/bold red]")
            console.print("Available profiles:")
            for name in profiles.keys():
                console.print(f"  - {name}")
            sys.exit(1)
        return

    interactive_select(profiles)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Operation cancelled by user[/bold yellow]")
        sys.exit(0)
