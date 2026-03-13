# aassh - SSH Connection Manager

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-1.2.0-blue.svg)](https://github.com/C0dWiz/aassh/releases)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS-lightgrey.svg)](https://github.com/C0dWiz/aassh)


*Simple and convenient SSH connection manager with Mosh support*

</div>

## 📋 Description

aassh is a lightweight command-line tool for managing SSH connections. It allows you to save, organize, and quickly connect to your SSH servers using convenient aliases instead of memorizing IP addresses and parameters. Includes full Mosh support for better mobile connectivity.

## ✨ Features

- 🔐 **Security**: Designed to work with SSH keys
- 📝 **Simple Management**: Intuitive command-line interface
- 🚀 **Fast Connection**: Instant access to servers by name
- 🔄 **Flexible Configuration**: Easy editing of connection parameters
- 📦 **Easy Installation**: Single script for installation and setup
- 🛜 **Mosh Support**: Better connectivity for unstable networks
- 🎨 **Rich Interface**: Beautiful terminal UI with colors and tables

## 🚀 Installation

### Installation and Usage Instructions

1. Installation via script (safe flow):

```bash
# Download installer
curl -fsSL -o install.sh https://raw.githubusercontent.com/C0dWiz/aassh/dev/install.sh

# (Optional) inspect before running
less install.sh

# Run installer
bash install.sh

# Update PATH (if needed)
export PATH="$PATH:${HOME}/.local/bin"
```

2. Installation from source (pip):

```bash
git clone https://github.com/C0dWiz/aassh.git
cd aassh
python3 -m pip install .
```

3. **Usage:**
```bash
# Interactive mode (beautiful interface)
aassh

# List all profiles
aassh -l

# Filter profiles
aassh -f production

# Connect to specific profile
aassh aws-prod

# Add new profile
aassh --add

# Edit existing profile
aassh --edit home-server

# Delete profile
aassh --delete office-jumpbox

# Check Mosh installation
aassh --check-mosh

# Export profiles
aassh --export ./backup.yml

# Import profiles
aassh --import ./backup.yml

# Import hosts from OpenSSH config
aassh --import-ssh-config

# Show version
aassh -v
```

4. Uninstall:

```bash
bash install.sh --uninstall
```

## ⚙️ Configuration

Sample configuration (~/.aassh/config.yml):
```yaml
profiles:
  home-server:
    host: 192.168.1.100
    user: pi
    port: 2222
    description: Raspberry Pi home server
    tags: [raspberry, home]

  aws-prod:
    host: ec2-12-34-56-78.us-west-2.compute.amazonaws.com
    user: ubuntu
    key: ~/.ssh/aws-prod.pem
    description: Production web server
    tags: [aws, production]

  office-jumpbox:
    host: jumpbox.company.com
    user: myuser
    key: ~/.ssh/company_key
    description: Corporate jump server
    tags: [work, vpn]

  mobile-server:
    host: mobile.example.com
    user: mobile_user
    use_mosh: true
    mosh_port_range: 60000:61000
    description: Server with Mosh for mobile connections
    tags: [mosh, mobile]
```

## 🤝 Contributing

1. Fork the project
2. Create a branch for your changes (git checkout -b feature/amazing-feature)
3. Commit your changes (git commit -m 'Add amazing feature')
4. Push to the branch in your fork (git push origin feature/amazing-feature)
5. Open a Pull Request

## 📜 License

Distributed under the MIT License. See the [LICENSE](LICENSE) file for more information.

## 📞 Support

- 🐛 [Report a bug](https://github.com/C0dwiz/aassh/issues)
- 💡 [Suggest an improvement](https://github.com/C0dwiz/aassh/issues)
- 📧 [Contact the author](https://github.com/C0dwiz)
