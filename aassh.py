#!/usr/bin/env python3
"""
AASSH - Another Awesome SSH Client (Python Edition)
Interactive SSH client with rich terminal interface with Mosh support
"""

import argparse
import os
import re
import shlex
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, NoReturn, Optional

import yaml
from ruamel.yaml import YAML
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

CONFIG_DIR = Path.home() / ".aassh"
CONFIG_FILE = CONFIG_DIR / "config.yml"
VERSION = "1.2.0"
MAX_CONFIG_SIZE_BYTES = 1024 * 1024

console = Console()
ruamel_yaml = YAML()
ruamel_yaml.default_flow_style = False


class AasshError(Exception):
    """Base application error."""


class AasshExitError(AasshError):
    """Error that carries desired process exit code."""

    def __init__(self, message: str, code: int = 1):
        super().__init__(message)
        self.code = code


class ConfigError(AasshError):
    """Configuration read/write/parsing error."""


class ConnectionErrorWithCode(AasshExitError):
    """Connection-related error with process exit code."""


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

    def ssh_args(self) -> List[str]:
        """Build common SSH argument list."""
        args: List[str] = []
        if self.port:
            args.extend(["-p", str(self.port)])
        if self.key:
            args.extend(["-i", os.path.expanduser(self.key)])
        return args

    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to a dictionary for YAML serialization."""
        data = asdict(self)
        del data["name"]
        return {k: v for k, v in data.items() if v not in [None, []]}

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
    sorted_profiles = {
        name: profile.to_dict() for name, profile in sorted(profiles.items())
    }
    try:
        CONFIG_DIR.mkdir(exist_ok=True, parents=True)
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r") as f:
                existing_data = ruamel_yaml.load(f) or {}
            if not isinstance(existing_data, dict):
                existing_data = {}
            existing_data["profiles"] = sorted_profiles
            with open(CONFIG_FILE, "w") as f:
                ruamel_yaml.dump(existing_data, f)
        else:
            config_data: Dict[str, Any] = {"profiles": sorted_profiles}
            with open(CONFIG_FILE, "w") as f:
                yaml.dump(
                    config_data, f, sort_keys=False, default_flow_style=False, indent=2
                )
    except Exception as e:
        raise ConfigError(f"Error saving config file: {e}") from e


def load_config() -> Dict[str, SSHProfile]:
    """Load and parse configuration file"""
    if not CONFIG_FILE.exists():
        return {}

    if CONFIG_FILE.stat().st_size > MAX_CONFIG_SIZE_BYTES:
        raise ConfigError(
            f"Config file is too large ({CONFIG_FILE.stat().st_size} bytes). "
            f"Max supported size: {MAX_CONFIG_SIZE_BYTES} bytes"
        )

    try:
        with open(CONFIG_FILE, "r") as f:
            config_data: Dict[str, Any] = yaml.safe_load(f) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"Error parsing YAML config: {e}") from e
    except Exception as e:
        raise ConfigError(f"Error reading config file: {e}") from e

    profiles: Dict[str, SSHProfile] = {}
    for name, settings in config_data.get("profiles", {}).items():
        try:
            profile = SSHProfile(name=name, **settings)
            if profile.validate():
                profiles[name] = profile
        except TypeError as e:
            raise ConfigError(f"Error in profile '{name}': Unknown setting. {e}") from e
        except Exception as e:
            raise ConfigError(f"Error creating profile '{name}': {e}") from e

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
def connection_runner(client_name: str, not_found_msg: str) -> Iterator[None]:
    """Context manager to handle common subprocess connection errors."""
    try:
        yield
    except subprocess.CalledProcessError as e:
        raise ConnectionErrorWithCode(
            f"{client_name} connection failed (code {e.returncode})", e.returncode
        ) from e
    except KeyboardInterrupt as e:
        raise ConnectionErrorWithCode("Connection terminated by user", 130) from e
    except FileNotFoundError as e:
        raise AasshError(not_found_msg) from e


def ensure_mosh_available() -> None:
    """Ensure mosh binary is present before attempting a mosh connection."""
    if not check_mosh_installed(show_ok=False, show_instructions=False):
        raise AasshError(
            "Mosh profile selected but mosh is not installed. "
            "Run 'aassh --check-mosh' for installation guidance."
        )


def run_connection(profile: SSHProfile) -> None:
    """Execute SSH or Mosh connection"""
    if profile.use_mosh:
        ensure_mosh_available()
        run_mosh(profile)
    else:
        run_ssh(profile)


def run_ssh(profile: SSHProfile) -> None:
    """Execute SSH connection"""
    cmd = ["ssh", "-o", "StrictHostKeyChecking=yes", *profile.ssh_args()]
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
    ssh_cmd_list = ["ssh", *profile.ssh_args()]

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
        raise AasshError("Profile name cannot be empty.")

    host: str = Prompt.ask("Host", default=defaults.get("host", ""))
    if not host:
        raise AasshError("Host cannot be empty.")

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
            raise AasshError(
                f"Invalid port number: '{port_str}'. Port must be an integer."
            )

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
        if mosh_args_str:
            try:
                mosh_args = shlex.split(mosh_args_str)
            except ValueError as e:
                raise AasshError(f"Invalid mosh args: {e}") from e

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
        raise AasshError(f"Profile '{name}' already exists.")

    new_profile = SSHProfile(**input_data)

    if not new_profile.validate():
        raise AasshError("Profile validation failed. Aborting.")

    profiles[name] = new_profile
    save_config(profiles)
    console.print(f"[bold green]✓ Profile '{name}' added successfully.[/bold green]")


def edit_profile(profiles: Dict[str, SSHProfile], name: str) -> None:
    """Interactively edit an existing profile."""
    if name not in profiles:
        raise AasshError(f"Profile '{name}' not found.")

    console.print(Panel(f"[bold green]Edit Profile: {name}[/bold green]", expand=False))

    input_data: Dict[str, Any] = get_profile_input(profiles[name])
    # Keep the original name for the profile
    input_data["name"] = name

    updated_profile = SSHProfile(**input_data)

    if not updated_profile.validate():
        raise AasshError("Profile validation failed. Aborting.")

    profiles[name] = updated_profile
    save_config(profiles)
    console.print(f"[bold green]✓ Profile '{name}' updated successfully.[/bold green]")


def delete_profile(profiles: Dict[str, SSHProfile], name: str) -> None:
    """Delete a profile."""
    if name not in profiles:
        raise AasshError(f"Profile '{name}' not found.")

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
        raise ConfigError(f"Error creating sample config: {e}") from e


def check_mosh_installed(
    show_ok: bool = True, show_instructions: bool = True
) -> bool:
    """Check if Mosh is installed"""
    try:
        result = subprocess.run(
            ["mosh", "--version"], capture_output=True, text=True, check=False
        )

        if result.returncode != 0:
            if show_instructions:
                console.print(
                    "[bold red]✗ Mosh check failed (non-zero exit code)[/bold red]"
                )
                console.print("\n[yellow]Installation instructions:[/yellow]")
                console.print("  Ubuntu/Debian: [cyan]sudo apt install mosh[/cyan]")
                console.print("  macOS: [cyan]brew install mosh[/cyan]")
                console.print("  CentOS/RHEL: [cyan]sudo yum install mosh[/cyan]")
            return False

        version_line = (
            result.stdout.split("\n")[0] if result.stdout else "Unknown version"
        )
        if show_ok:
            console.print(
                f"[bold green]✓ Mosh is installed: {version_line}[/bold green]"
            )
        return True
    except FileNotFoundError:
        if show_instructions:
            console.print("[bold red]✗ Mosh is not installed or not in PATH[/bold red]")
            console.print("\n[yellow]Installation instructions:[/yellow]")
            console.print("  Ubuntu/Debian: [cyan]sudo apt install mosh[/cyan]")
            console.print("  macOS: [cyan]brew install mosh[/cyan]")
            console.print("  CentOS/RHEL: [cyan]sudo yum install mosh[/cyan]")
        return False


def export_profiles(profiles: Dict[str, SSHProfile], path_str: str) -> None:
    """Export current profiles into a YAML file."""
    output_path = Path(path_str).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = {
        "profiles": {
            name: profile.to_dict() for name, profile in sorted(profiles.items())
        }
    }
    with open(output_path, "w") as file:
        yaml.dump(content, file, sort_keys=False, default_flow_style=False, indent=2)
    console.print(f"[bold green]✓ Profiles exported to {output_path}[/bold green]")


def import_profiles(profiles: Dict[str, SSHProfile], path_str: str) -> None:
    """Import profiles from a YAML file (upsert by name)."""
    input_path = Path(path_str).expanduser()
    if not input_path.exists():
        raise ConfigError(f"Import file not found: {input_path}")

    try:
        with open(input_path, "r") as file:
            config_data: Dict[str, Any] = yaml.safe_load(file) or {}
    except yaml.YAMLError as e:
        raise ConfigError(f"Error parsing import YAML: {e}") from e

    incoming_profiles: Dict[str, Any] = config_data.get("profiles", {})
    if not isinstance(incoming_profiles, dict):
        raise ConfigError("Invalid import format: expected top-level 'profiles' map")

    imported_count = 0
    for name, settings in incoming_profiles.items():
        profile = SSHProfile(name=name, **settings)
        if profile.validate():
            profiles[name] = profile
            imported_count += 1

    save_config(profiles)
    console.print(
        f"[bold green]✓ Imported {imported_count} profile(s) from {input_path}[/bold green]"
    )


def _is_plain_ssh_host(alias: str) -> bool:
    return "*" not in alias and "?" not in alias and "!" not in alias


def import_from_ssh_config(profiles: Dict[str, SSHProfile], ssh_config_path: str) -> None:
    """Import host entries from ~/.ssh/config into AASSH profiles."""
    path = Path(ssh_config_path).expanduser()
    if not path.exists():
        raise ConfigError(f"SSH config not found: {path}")

    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        raise ConfigError(f"Could not read SSH config: {e}") from e

    host_blocks: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = re.split(r"\s+", line, maxsplit=1)
        if len(parts) != 2:
            continue

        key, value = parts[0].lower(), parts[1].strip()
        if key == "host":
            aliases = value.split()
            if len(aliases) != 1 or not _is_plain_ssh_host(aliases[0]):
                current = None
                continue
            current = {
                "name": aliases[0],
                "host": aliases[0],
                "user": None,
                "port": None,
                "key": None,
                "description": "Imported from ~/.ssh/config",
                "tags": ["imported"],
            }
            host_blocks.append(current)
            continue

        if not current:
            continue

        if key == "hostname":
            current["host"] = value
        elif key == "user":
            current["user"] = value
        elif key == "port":
            try:
                current["port"] = int(value)
            except ValueError:
                current["port"] = None
        elif key == "identityfile":
            current["key"] = value

    imported_count = 0
    for block in host_blocks:
        profile = SSHProfile(
            name=block["name"],
            host=block["host"],
            user=block["user"],
            port=block["port"],
            key=block["key"],
            description=block["description"],
            tags=block["tags"],
        )
        if profile.validate():
            profiles[profile.name] = profile
            imported_count += 1

    save_config(profiles)
    console.print(
        f"[bold green]✓ Imported {imported_count} profile(s) from {path}[/bold green]"
    )


def create_parser() -> argparse.ArgumentParser:
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
    parser.add_argument(
        "--export",
        dest="export_path",
        metavar="FILE",
        help="Export all profiles to a YAML file.",
    )
    parser.add_argument(
        "--import",
        dest="import_path",
        metavar="FILE",
        help="Import profiles from a YAML file (upsert by name).",
    )
    parser.add_argument(
        "--import-ssh-config",
        dest="import_ssh_config",
        metavar="FILE",
        nargs="?",
        const=str(Path.home() / ".ssh" / "config"),
        help="Import host aliases from OpenSSH config (default: ~/.ssh/config).",
    )

    try:
        import argcomplete  # type: ignore

        argcomplete.autocomplete(parser)
    except ImportError:
        pass

    return parser


def handle_args(args: argparse.Namespace) -> int:
    if args.version:
        show_version()
        return 0

    if args.check_mosh:
        return 0 if check_mosh_installed() else 1

    if args.create_sample_config:
        create_sample_config()
        return 0

    profiles = load_config()

    if args.import_path:
        import_profiles(profiles, args.import_path)
        return 0

    if args.import_ssh_config:
        import_from_ssh_config(profiles, args.import_ssh_config)
        return 0

    if args.export_path:
        export_profiles(profiles, args.export_path)
        return 0

    if args.add:
        add_profile(profiles)
        return 0
    if args.edit:
        edit_profile(profiles, args.edit)
        return 0
    if args.delete:
        delete_profile(profiles, args.delete)
        return 0

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
        return 0

    if args.list:
        profiles_to_display = filter_profiles(profiles, args.filter or "")
        display_profile_table(profiles_to_display)
        return 0

    if args.interactive:
        interactive_select(profiles, filter_str=args.filter)
        return 0

    if args.profile:
        if args.profile in profiles:
            run_connection(profiles[args.profile])
        else:
            raise AasshExitError(f"Profile '{args.profile}' not found!", code=1)
        return 0

    interactive_select(profiles, filter_str=args.filter)
    return 0


def main() -> int:
    parser = create_parser()
    args = parser.parse_args()
    return handle_args(args)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Operation cancelled by user[/bold yellow]")
        sys.exit(130)
    except AasshExitError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(e.code)
    except AasshError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        error_exit(f"An unexpected error occurred: {e}")
