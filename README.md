# ComputerTool Technical Documentation

**Version:** 1.0.0  
**License:** MIT  
**Author:** ComputerTool Project  
**Last Updated:** May 2026  

---

## 1. Overview

**ComputerTool** is a cross-platform Python utility designed to discover, categorize, and launch system administration tools on Windows, Linux, and macOS. It provides a unified, text-based interactive interface that adapts to the host operating system, offering relevant utilities for system monitoring, network diagnostics, disk management, and more.

### Key Features
- **Cross-Platform Support:** Automatically detects Windows, Linux (with distro detection), and macOS.
- **Dynamic Tool Discovery:** Loads only tools available on the current system (e.g., `apt` tools on Debian/Ubuntu, `brew` on macOS).
- **Interactive TUI:** A color-coded, menu-driven interface for easy navigation.
- **System Information Dashboard:** Displays detailed OS, hardware, disk, and memory statistics.
- **Safe Launching:** Handles terminal emulation for CLI tools and direct execution for GUI applications.

---

## 2. Requirements

- **Python:** Version 3.6 or higher.
- **Operating System:** Windows 10/11, modern Linux distributions, or macOS 10.15+.
- **Dependencies:** No external third-party libraries are required. The script uses only Python standard library modules (`os`, `sys`, `platform`, `subprocess`, `shutil`, `ctypes`, etc.).

---

## 3. Installation & Usage

### 3.1. Running the Script

No installation is required. Simply download `computertool.py` and run it using Python.

```bash
python3 computertool.py
```

### 3.2. Command-Line Arguments

| Argument | Description |
| :--- | :--- |
| *(None)* | Launches the interactive menu system. |
| `--list` | Prints all available tools for the current OS to stdout and exits. |
| `--info` | Displays system information summary and exits. |

### 3.3. Interactive Menu Controls

Once launched, the main menu provides the following options:

- **[1-N]**: Select a tool category (e.g., System Monitoring, Network).
- **[i]**: Show detailed System Information (OS, Disk, Memory).
- **[r]**: Refresh the tool list (useful if new tools were installed while the script was running).
- **[0]**: Exit the application.

Inside a category:
- **[1-N]**: Launch the selected tool.
- **[0]**: Return to the main menu.

---

## 4. Architecture

The codebase is structured using object-oriented principles with clear separation of concerns.

### 4.1. Core Classes

#### `Colors`
Handles ANSI escape codes for terminal coloring. It includes a check (`supports_color`) to disable colors on unsupported terminals (e.g., Windows CMD without VT support, though it attempts to enable it via `ctypes`).

#### `SystemInfo`
Responsible for detecting and storing system metadata.
- **Detection:** Uses `platform` module for OS/Arch/CPU.
- **Linux Distro:** Parses `/etc/os-release` or uses `lsb_release`.
- **Desktop Environment:** Checks environment variables (`XDG_CURRENT_DESKTOP`) and binary existence (`gnome-shell`, `plasmashell`, etc.).
- **Hardware Stats:**
  - **Windows:** Uses `ctypes` to call `GlobalMemoryStatusEx` and `GetLogicalDrives`.
  - **Linux/macOS:** Reads `/proc/meminfo` and uses `os.statvfs` for disk usage.

#### `Tool`
Represents a single executable command.
- **Attributes:** `name`, `description`, `command`, `args`, `run_in_terminal`, `requires_admin`.
- **Launch Logic:**
  - If `run_in_terminal` is `False`: Uses `subprocess.Popen` to detach the process (GUI apps).
  - If `run_in_terminal` is `True`: Spawns a new terminal window.
    - **Windows:** Uses `cmd /c start`.
    - **macOS:** Uses `osascript` to tell Terminal.app to execute the script.
    - **Linux:** Iterates through a list of known terminal emulators (`gnome-terminal`, `konsole`, `xterm`, etc.) to find one available on the system.

#### `ToolCategory`
A container for a list of `Tool` objects, used for grouping in the UI (e.g., "Network Tools").

#### `ToolProvider` Classes
Three static provider classes generate the tool lists based on the OS:
- `WindowsToolProvider`: Focuses on `.msc`, `.cpl`, and `ms-settings:` URIs.
- `LinuxToolProvider`: Focuses on CLI tools (`top`, `ip`, `systemctl`) and checks for their existence using `shutil.which`.
- `MacOSToolProvider`: Focuses on `.app` bundles via the `open` command and BSD-style CLI tools.

#### `ToolMenu`
The controller class that manages the user interaction loop, screen clearing, and input parsing.

---

## 5. Supported Tools by Platform

### 5.1. Windows
- **System:** Task Manager, System Info (`msinfo32`), Registry Editor, Event Viewer.
- **Disk:** Disk Management, Cleanup, Defrag.
- **Network:** Firewall, Network Connections, IP Config.
- **Admin:** Services, Local Users, Group Policy.
- **Recovery:** System Restore, Memory Diagnostic, SFC.

### 5.2. Linux
- **Monitoring:** `top`, `htop`, `glances`, `vmstat`, `iostat`.
- **Process:** `ps`, `pstree`, `lsof`, `pkill`.
- **Network:** `ip addr`, `ss`, `netstat`, `ping`, `traceroute`, `nmap` (if installed).
- **Systemd:** `systemctl` (list services, failed units), `journalctl` (logs), `systemd-analyze`.
- **Package Mgmt:** Dynamic detection of `apt`, `dnf`, `yum`, `pacman`, `zypper`, `snap`, `flatpak`.
- **Security:** `ufw`/`firewall-cmd`, `iptables`, `fail2ban`, `SELinux`/`AppArmor` status.

### 5.3. macOS
- **GUI Apps:** Activity Monitor, Disk Utility, System Settings, Console, Keychain Access.
- **CLI Tools:** `top`, `vm_stat`, `diskutil`, `system_profiler`, `launchctl`.
- **Network:** `ifconfig`, `netstat`, `arp`, `ping`.
- **Package Mgmt:** Homebrew (`brew list`, `brew outdated`) if detected.

---

## 6. Development & Extension

### 6.1. Adding New Tools

To add a new tool, modify the respective `ToolProvider` class.

**Example: Adding a new Linux tool**

```python
# Inside LinuxToolProvider.get_tools()
cat = ToolCategory("My Custom Category", "[*]")
# Check if the binary exists before adding
if shutil.which("my-custom-tool"):
    cat.add(Tool(
        name="My Custom Tool",
        description="Does something cool",
        command="my-custom-tool",
        args=["--verbose"],
        run_in_terminal=True
    ))
categories.append(cat)
```

### 6.2. Adding a New OS Support

1. Create a new class `NewOSToolProvider` inheriting the structure of existing providers.
2. Implement the `get_tools()` static method returning `List[ToolCategory]`.
3. Update `ToolMenu._load_tools()` to include a check for the new OS:
   ```python
   elif self.sys_info.os_name == "NewOS":
       self.categories = NewOSToolProvider.get_tools()
   ```

---

## 7. Troubleshooting

### 7.1. Colors not displaying
Ensure your terminal supports ANSI escape codes. On Windows, ensure you are using Windows Terminal, PowerShell, or a recent version of CMD. The script attempts to enable VT processing automatically on Windows.

### 7.2. "Command not found" errors
The script checks for binary existence using `shutil.which` for most Linux/macOS tools. If a tool fails to launch:
1. Ensure the tool is installed.
2. Ensure the tool is in the system `PATH`.
3. For Windows `.msc` or `.cpl` files, ensure they are present in `C:\Windows\System32`.

### 7.3. Terminal Emulator Detection on Linux
If launching a CLI tool fails to open a new window, the script iterates through a hardcoded list of terminal emulators. If your preferred terminal is not detected, install one of the supported ones (e.g., `gnome-terminal`, `xterm`, `konsole`) or modify the `terminals` list in `Tool._launch_in_terminal`.

---

## 8. License

This project is licensed under the **MIT License**. You are free to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software.
