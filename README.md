# aassh - SSH Connection Manager

<div align="center">

![aassh Logo](https://raw.githubusercontent.com/C0dwiz/aassh/dev/docs/assets/logo.png)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-1.0.5-blue.svg)](https://github.com/C0dwiz/aassh/releases)
[![Shell Script](https://img.shields.io/badge/language-Shell-green.svg)](https://www.gnu.org/software/bash/)

*Simple and convenient SSH connection manager for Linux*

</div>

## 📋 Description

aassh is a lightweight command-line tool for managing SSH connections. It allows you to save, organize, and quickly connect to your SSH servers using convenient aliases instead of memorizing IP addresses and parameters.

## ✨ Features

- 🔐 Security: Designed to work with SSH keys
- 📝 Simple Management: Intuitive command-line interface
- 🚀 Fast Connection: Instant access to servers by name
- 🔄 Flexible Configuration: Easy editing of connection parameters
- 📦 Easy Installation: Single script for installation and setup

## 🚀 Installation

### Installation and Usage Instructions

1. Installation via script:

```bash
# Download and run the installer
curl -sSL https://raw.githubusercontent.com/C0dWiz/aassh/dev/install.sh | bash

# Update PATH (if needed)
export PATH="$PATH:${HOME}/.local/bin"
```

2. **Usage:**
```bash
# Interactive mode (beautiful interface)
aassh

# List profiles
aassh -l

# Connect to a specific profile
aassh aws-prod

# Create sample config
aassh --create-sample-config

# Show version
aassh -v
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
