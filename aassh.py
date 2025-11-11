#!/usr/bin/env python3
"""
AASSH - Another Awesome SSH Client (Python Edition)
Interactive SSH client with rich terminal interface with Mosh support
"""

import argparse
import os
import shlex
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, NoReturn, Optional

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

CONFIG_DIR = Path.home() / ".aassh"
CONFIG_FILE = CONFIG_DIR / "config.yml"
VERSION = "1.1.0"

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
    tags: List[str] = field(default_factory=list)  # type: ignore
    use_mosh: bool = False
    mosh_args: List[str] = field(default_factory=list)  # type: ignore
    mosh_port_range: Optional[str] = None

    def connection_string(self) -> str:
        """Generate SSH/Mosh connection string"""
        user_part = f"{self.user}@" if self.user else ""
        return f"{user_part}{self.host}"

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to a dictionary for YAML serialization."""
        data = asdict(self)
        del data["name"]
        return {k: v for k, v in data.items() if v not in [None, [], False]}

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

        if self.key:
            expanded_key = Path(os.path.expanduser(self.key))
            if not expanded_key.exists():
                console.print(
                    f"[red]Error: SSH key not found for profile '{self.name}': {expanded_key}[/red]"
                )
                return False

        # Validate Mosh port range format
        if self.mosh_port_range and not self._validate_mosh_port_range():
            return False

        return True

    def _validate_mosh_port_range(self) -> bool:
        """Validate Mosh port range format"""
        if not self.mosh_port_range:
            return True

        try:
            if ":" in self.mosh_port_range:
                start, end = map(int, self.mosh_port_range.split(":"))
                if not (0 < start <= 65535 and 0 < end <= 65535 and start < end):
                    raise ValueError("Invalid port range")
            else:
                port = int(self.mosh_port_range)
                if not (0 < port <= 65535):
                    raise ValueError("Invalid port")
        except (ValueError, AttributeError):
            console.print(
                f"[red]Error: Invalid Mosh port range for profile '{self.name}': {self.mosh_port_range}[/red]"
            )
            console.print("[yellow]Use format: 60000:61000 or single port[/yellow]")
            return False
        return True


def error_exit(message: str, code: int = 1) -> NoReturn:
    """Display error message and exit"""
    console.print(f"[bold red]Error:[/bold red] {message}")
    sys.exit(code)


def save_config(profiles: Dict[str, SSHProfile]) -> None:
    """Save profiles to the configuration file."""
    config_data: Dict[str, Any] = {
        "profiles": {
            name: profile.to_dict() for name, profile in sorted(profiles.items())
        }
    }
    try:
        CONFIG_DIR.mkdir(exist_ok=True, parents=True)
        with open(CONFIG_FILE, "w") as f:
            yaml.dump(
                config_data, f, sort_keys=False, default_flow_style=False, indent=2
            )
    except Exception as e:
        error_exit(f"Error saving config file: {e}")


def load_config() -> Dict[str, SSHProfile]:
    """Load and parse configuration file"""
    if not CONFIG_FILE.exists():
        return {}

    try:
        with open(CONFIG_FILE, "r") as f:
            config_data: Dict[str, Any] = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        error_exit(f"Error parsing YAML config: {e}")
    except Exception as e:
        error_exit(f"Error reading config file: {e}")

    profiles: Dict[str, SSHProfile] = {}
    for name, settings in config_data.get("profiles", {}).items():
        try:
            profile = SSHProfile(name=name, **settings)
            if profile.validate():
                profiles[name] = profile
        except TypeError as e:
            error_exit(f"Error in profile '{name}': Unknown setting. {e}")
        except Exception as e:
            error_exit(f"Error creating profile '{name}': {e}")

    return profiles


def display_profile_table(profiles: Dict[str, SSHProfile]) -> None:
    """Display profiles in a rich table"""
    if not profiles:
        console.print("[yellow]No profiles found.[/yellow]")
        return

    table = Table(
        title="\n📡 [bold green]Available SSH/Mosh Profiles[/bold green]",
        show_header=True,
        header_style="bold magenta",
        expand=True,
    )
    table.add_column("Name", style="cyan", width=20)
    table.add_column("Type", style="blue", width=8)
    table.add_column("Connection", style="yellow")
    table.add_column("Description", style="white")
    table.add_column("Tags", style="green")

    for name, profile in sorted(profiles.items()):
        conn_str = profile.connection_string()
        if profile.port:
            conn_str += f":{profile.port}"

        tags = ", ".join(profile.tags) if profile.tags else "-"
        desc = profile.description or "No description"
        connection_type = (
            Text("🛜 Mosh", style="bold blue")
            if profile.use_mosh
            else Text("🔗 SSH", style="bold green")
        )

        table.add_row(f"[bold]{name}[/bold]", connection_type, conn_str, desc, tags)

    console.print(table)
    console.print(f"[dim]Total profiles: {len(profiles)}[/dim]\n")


@contextmanager
def connection_runner(client_name: str, not_found_msg: str):
    """Context manager to handle common subprocess connection errors."""
    try:
        yield
    except subprocess.CalledProcessError as e:
        console.print(
            f"[bold red]{client_name} connection failed (code {e.returncode})[/bold red]"
        )
        sys.exit(e.returncode)
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Connection terminated by user[/bold yellow]")
        sys.exit(130)
    except FileNotFoundError:
        error_exit(not_found_msg)


def run_connection(profile: SSHProfile) -> None:
    """Execute SSH or Mosh connection"""
    if profile.use_mosh:
        run_mosh(profile)
    else:
        run_ssh(profile)


def run_ssh(profile: SSHProfile) -> None:
    """Execute SSH connection"""
    cmd = ["ssh", "-o", "StrictHostKeyChecking=yes"]
    if profile.port:
        cmd.extend(["-p", str(profile.port)])
    if profile.key:
        cmd.extend(["-i", os.path.expanduser(profile.key)])
    cmd.append(profile.connection_string())

    console.print(
        f"\n🚀 [bold green]Connecting via SSH to [cyan]{profile.name}[/cyan]...[/bold green]"
    )
    console.print(
        f"🔗 [yellow]{' '.join(shlex.quote(str(arg)) for arg in cmd)}[/yellow]\n"
    )

    with connection_runner(
        "SSH", "SSH client not found! Please ensure OpenSSH is installed."
    ):
        subprocess.run(cmd, check=True)


def run_mosh(profile: SSHProfile) -> None:
    """Execute Mosh connection"""
    cmd = ["mosh"]
    ssh_cmd_list = ["ssh"]
    if profile.port:
        ssh_cmd_list.extend(["-p", str(profile.port)])
    if profile.key:
        ssh_cmd_list.extend(["-i", os.path.expanduser(profile.key)])

    # Mosh's --ssh argument is passed to a shell, so it must be a single,
    # properly quoted string to handle paths with spaces in keys.
    ssh_command_str = " ".join(shlex.quote(arg) for arg in ssh_cmd_list)
    cmd.extend(["--ssh", ssh_command_str])

    if profile.mosh_args:
        cmd.extend(profile.mosh_args)
    if profile.mosh_port_range:
        cmd.extend(["--port", profile.mosh_port_range])

    cmd.append(profile.connection_string())

    console.print(
        f"\n🛜 [bold green]Connecting via Mosh to [cyan]{profile.name}[/cyan]...[/bold green]"
    )
    console.print(
        f"📡 [yellow]{' '.join(shlex.quote(str(arg)) for arg in cmd)}[/yellow]"
    )
    console.print(
        "[dim]Mosh provides better connectivity for unstable networks[/dim]\n"
    )

    mosh_install_info = (
        "Mosh client not found! Please ensure Mosh is installed:\n"
        "  Ubuntu/Debian: [cyan]sudo apt install mosh[/cyan]\n"
        "  macOS: [cyan]brew install mosh[/cyan]"
    )
    with connection_runner("Mosh", mosh_install_info):
        subprocess.run(cmd, check=True)


def interactive_select(
    profiles: Dict[str, SSHProfile], filter_str: Optional[str] = None
) -> None:
    """Interactive profile selection with rich interface"""
    if not profiles:
        error_exit("No profiles found. Use 'aassh --add' to create one.")

    if not filter_str:
        filter_str = Prompt.ask(
            "[dim]Filter by name, description or tag (optional)[/dim]", default=""
        )

    profiles_to_display = filter_profiles(profiles, filter_str)

    if not profiles_to_display:
        if filter_str:
            console.print(
                f"\n[yellow]No profiles found matching '[bold]{filter_str}[/bold]'.[/yellow]"
            )
        return

    display_profile_table(profiles_to_display)
    choices = list(sorted(profiles_to_display.keys()))

    if len(choices) == 1:
        # Auto-select if only one profile matches
        choice = choices[0]
        console.print(
            f"[green]Auto-selecting the only matching profile: {choice}[/green]"
        )
        if Confirm.ask("Connect to this profile?", default=True):
            run_connection(profiles_to_display[choice])
        return

    try:
        choice = Prompt.ask("🔍 Select profile", choices=choices, show_choices=False)
        if choice in profiles_to_display:
            run_connection(profiles_to_display[choice])
        else:
            error_exit("Invalid selection!")
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Selection cancelled by user[/bold yellow]")


def filter_profiles(
    profiles: Dict[str, SSHProfile], filter_str: str
) -> Dict[str, SSHProfile]:
    """Filter profiles by name, description, or tag."""
    if not filter_str:
        return profiles

    filter_str = filter_str.lower()
    return {
        name: profile
        for name, profile in profiles.items()
        if filter_str in name.lower()
        or filter_str in (profile.description or "").lower()
        or any(filter_str in tag.lower() for tag in profile.tags)
    }


def get_profile_input(existing_profile: Optional[SSHProfile] = None) -> Dict[str, Any]:
    """Get profile input from user, with existing values as defaults."""
    defaults: Dict[str, Any] = existing_profile.__dict__ if existing_profile else {}

    name: str = Prompt.ask("Profile Name", default=defaults.get("name", ""))
    if not name:
        error_exit("Profile name cannot be empty.")

    host: str = Prompt.ask("Host", default=defaults.get("host", ""))
    if not host:
        error_exit("Host cannot be empty.")

    user: Optional[str] = (
        Prompt.ask("User (optional)", default=defaults.get("user") or "") or None
    )

    port_str: str = Prompt.ask(
        "Port (optional, default: 22)", default=str(defaults.get("port") or "")
    )
    port: Optional[int] = None
    if port_str:
        try:
            port = int(port_str)
        except ValueError:
            error_exit(f"Invalid port number: '{port_str}'. Port must be an integer.")

    key: Optional[str] = (
        Prompt.ask(
            "SSH Key Path (optional, e.g., ~/.ssh/id_rsa)",
            default=defaults.get("key") or "",
        )
        or None
    )
    description: Optional[str] = (
        Prompt.ask("Description (optional)", default=defaults.get("description") or "")
        or None
    )

    default_tags: str = ", ".join(defaults.get("tags", []))
    tags_str: str = Prompt.ask("Tags (optional, comma-separated)", default=default_tags)
    tags: List[str] = [tag.strip() for tag in tags_str.split(",")] if tags_str else []

    use_mosh: bool = Confirm.ask("Use Mosh?", default=defaults.get("use_mosh", False))

    mosh_args: List[str] = []
    mosh_port_range: Optional[str] = None
    if use_mosh:
        default_mosh_args: str = " ".join(defaults.get("mosh_args", []))
        mosh_args_str: str = Prompt.ask(
            "Mosh args (optional, space-separated)", default=default_mosh_args
        )
        mosh_args = mosh_args_str.split() if mosh_args_str else []

        mosh_port_range = (
            Prompt.ask(
                "Mosh UDP port range (optional, e.g., 60000:61000)",
                default=defaults.get("mosh_port_range") or "",
            )
            or None
        )

    return {
        "name": name,
        "host": host,
        "user": user,
        "port": port,
        "key": key,
        "description": description,
        "tags": tags,
        "use_mosh": use_mosh,
        "mosh_args": mosh_args,
        "mosh_port_range": mosh_port_range,
    }


def add_profile(profiles: Dict[str, SSHProfile]) -> None:
    """Interactively add a new profile."""
    console.print(Panel("[bold green]Add New SSH Profile[/bold green]", expand=False))

    input_data: Dict[str, Any] = get_profile_input()
    name: str = input_data["name"]

    if name in profiles:
        error_exit(f"Profile '{name}' already exists.")

    new_profile = SSHProfile(**input_data)

    if not new_profile.validate():
        error_exit("Profile validation failed. Aborting.")

    profiles[name] = new_profile
    save_config(profiles)
    console.print(f"[bold green]✓ Profile '{name}' added successfully.[/bold green]")


def edit_profile(profiles: Dict[str, SSHProfile], name: str) -> None:
    """Interactively edit an existing profile."""
    if name not in profiles:
        error_exit(f"Profile '{name}' not found.")

    console.print(Panel(f"[bold green]Edit Profile: {name}[/bold green]", expand=False))

    input_data: Dict[str, Any] = get_profile_input(profiles[name])
    # Keep the original name for the profile
    input_data["name"] = name

    updated_profile = SSHProfile(**input_data)

    if not updated_profile.validate():
        error_exit("Profile validation failed. Aborting.")

    profiles[name] = updated_profile
    save_config(profiles)
    console.print(f"[bold green]✓ Profile '{name}' updated successfully.[/bold green]")


def delete_profile(profiles: Dict[str, SSHProfile], name: str) -> None:
    """Delete a profile."""
    if name not in profiles:
        error_exit(f"Profile '{name}' not found.")

    if Confirm.ask(f"Are you sure you want to delete profile '{name}'?", default=False):
        del profiles[name]
        save_config(profiles)
        console.print(f"[bold green]✓ Profile '{name}' deleted.[/bold green]")
    else:
        console.print("[yellow]Deletion cancelled.[/yellow]")


def show_version() -> None:
    """Display version information"""
    console.print(
        Panel(
            f"[bold green]AASSH v{VERSION}[/bold green]\n\n"
            "📖 GitHub: [underline blue]https://github.com/C0dWiz/aassh[/underline blue]\n"
            "🐛 Report Issues: [underline blue]https://github.com/C0dWiz/aassh/issues[/underline blue]",
            title="Version Information",
            border_style="green",
        )
    )


def create_sample_config() -> None:
    """Create sample configuration file"""
    if CONFIG_FILE.exists():
        if not Confirm.ask(
            f"[yellow]Config file {CONFIG_FILE} already exists. Overwrite?[/yellow]",
            default=False,
        ):
            console.print("[yellow]Operation cancelled.[/yellow]")
            return

    sample_config = """# AASSH Configuration
profiles:
  example:
    host: server.example.com
    user: username
    description: Example server
    tags:
      - dev
      - web

  prod-server:
    host: prod.example.com
    user: admin
    port: 2222
    key: ~/.ssh/prod_key
    description: Production server
    tags:
      - prod
      - critical

  mosh-server:
    host: mobile.example.com
    user: mobile_user
    use_mosh: true
    mosh_port_range: 60000:61000
    description: Server with Mosh for unstable connections
    tags:
      - mosh
      - mobile
"""
    try:
        CONFIG_DIR.mkdir(exist_ok=True, parents=True)
        with open(CONFIG_FILE, "w") as f:
            f.write(sample_config)
        console.print(
            Panel(
                f"[bold green]Sample configuration created:[/bold green] {CONFIG_FILE}\n"
                "[yellow]Please edit this file with your actual profiles.[/yellow]",
                title="Configuration Created",
                border_style="green",
            )
        )
    except Exception as e:
        error_exit(f"Error creating sample config: {e}")


def check_mosh_installed() -> bool:
    """Check if Mosh is installed"""
    try:
        result = subprocess.run(
            ["mosh", "--version"], capture_output=True, check=True, text=True
        )
        version_line = (
            result.stdout.split("\n")[0] if result.stdout else "Unknown version"
        )
        console.print(f"[bold green]✓ Mosh is installed: {version_line}[/bold green]")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        console.print("[bold red]✗ Mosh is not installed or not in PATH[/bold red]")
        console.print("\n[yellow]Installation instructions:[/yellow]")
        console.print("  Ubuntu/Debian: [cyan]sudo apt install mosh[/cyan]")
        console.print("  macOS: [cyan]brew install mosh[/cyan]")
        console.print("  CentOS/RHEL: [cyan]sudo yum install mosh[/cyan]")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="AASSH - Another Awesome SSH Client with Mosh support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("profile", nargs="?", help="Name of the profile to connect to.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "-l", "--list", action="store_true", help="List all available profiles."
    )
    group.add_argument(
        "-i", "--interactive", action="store_true", help="Select profile interactively."
    )
    group.add_argument("--add", action="store_true", help="Add a new profile.")
    group.add_argument("--edit", metavar="P", help="Edit an existing profile.")
    group.add_argument("--delete", metavar="P", help="Delete a profile.")
    # Other
    parser.add_argument(
        "-f",
        "--filter",
        help="Filter profiles by name, description, or tag (used with -l or -i).",
    )
    parser.add_argument(
        "-v", "--version", action="store_true", help="Show version information."
    )
    parser.add_argument(
        "--create-sample-config",
        action="store_true",
        help="Create a sample configuration file.",
    )
    parser.add_argument(
        "--check-mosh",
        action="store_true",
        help="Check if Mosh is installed and available.",
    )

    args = parser.parse_args()

    if args.version:
        show_version()
        return

    if args.check_mosh:
        check_mosh_installed()
        return

    if args.create_sample_config:
        create_sample_config()
        return

    profiles = load_config()
    if args.add:
        add_profile(profiles)
        return
    if args.edit:
        edit_profile(profiles, args.edit)
        return
    if args.delete:
        delete_profile(profiles, args.delete)
        return

    if not profiles:
        console.print(
            Panel(
                "[bold yellow]No configuration found.[/bold yellow]\n\n"
                "Create a sample config with:\n"
                "  [cyan]aassh --create-sample-config[/cyan]\n\n"
                "Or add a new profile with:\n"
                "  [cyan]aassh --add[/cyan]",
                title="Welcome to AASSH!",
                border_style="yellow",
            )
        )
        return

    mosh_profiles = [p for p in profiles.values() if p.use_mosh]
    if mosh_profiles and not check_mosh_installed():
        console.print(
            f"\n[yellow]Warning: {len(mosh_profiles)} profile(s) require Mosh but it's not installed.[/yellow]"
        )

    if args.list:
        profiles_to_display = filter_profiles(profiles, args.filter or "")
        display_profile_table(profiles_to_display)
        return

    if args.interactive:
        interactive_select(profiles, filter_str=args.filter)
        return

    if args.profile:
        if args.profile in profiles:
            run_connection(profiles[args.profile])
        else:
            console.print(
                f"[bold red]Error:[/bold red] Profile '{args.profile}' not found!"
            )
            console.print("\n[bold]Available profiles:[/bold]")
            for name in sorted(profiles.keys()):
                console.print(f"  - {name}")
            sys.exit(1)
        return

    interactive_select(profiles, filter_str=args.filter)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Operation cancelled by user[/bold yellow]")
        sys.exit(0)
    except Exception as e:
        error_exit(f"An unexpected error occurred: {e}")
