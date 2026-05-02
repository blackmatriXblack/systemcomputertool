#!/usr/bin/env python3
"""
ComputerTool - Cross-Platform System Tools Launcher
====================================================
A unified interface to discover and launch system tools
on Windows, Linux, and macOS.

Usage:
    python computertool.py          # Interactive menu
    python computertool.py --list   # List all available tools
    python computertool.py --info   # Show system information only

Author: ComputerTool Project
License: MIT
Version: 1.0.0
"""

import os
import sys
import platform
import subprocess
import shutil
import re
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple


# ============================================================
# COLOR SUPPORT
# ============================================================

class Colors:
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

    @staticmethod
    def supports_color() -> bool:
        """Check if the terminal supports ANSI colors."""
        if os.name == "nt":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                mode = ctypes.c_ulong()
                handle = kernel32.GetStdHandle(-11)
                kernel32.GetConsoleMode(handle, ctypes.byref(mode))
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
                return True
            except Exception:
                return False
        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def colorize(text: str, color: str) -> str:
    """Apply color to text if supported."""
    if Colors.supports_color():
        return f"{color}{text}{Colors.RESET}"
    return text


# ============================================================
# SYSTEM SCANNER
# ============================================================

class SystemInfo:
    """Detect and hold system information."""

    def __init__(self):
        self.os_name: str = platform.system()
        self.os_version: str = platform.version()
        self.os_release: str = platform.release()
        self.architecture: str = platform.machine()
        self.processor: str = platform.processor()
        self.hostname: str = platform.node()
        self.python_version: str = sys.version
        self.username: str = os.environ.get("USER", os.environ.get("USERNAME", "unknown"))

        # Linux distribution detection
        self.linux_distro: str = ""
        self.linux_distro_version: str = ""
        if self.os_name == "Linux":
            self._detect_linux_distro()

        # Desktop environment detection
        self.desktop_env: str = self._detect_desktop_environment()

    def _detect_linux_distro(self):
        """Detect Linux distribution name and version."""
        if shutil.which("lsb_release"):
            try:
                result = subprocess.run(
                    ["lsb_release", "-a"], capture_output=True, text=True, timeout=5
                )
                for line in result.stdout.split("\n"):
                    if "Distributor ID" in line:
                        self.linux_distro = line.split(":")[-1].strip()
                    if "Release" in line:
                        self.linux_distro_version = line.split(":")[-1].strip()
            except Exception:
                pass

        if not self.linux_distro:
            for path in ["/etc/os-release", "/etc/lsb-release"]:
                try:
                    with open(path, "r") as f:
                        content = f.read()
                        name_match = re.search(r'NAME="?(.+?)"?\n', content)
                        ver_match = re.search(r'VERSION_ID="?(.+?)"?\n', content)
                        if name_match:
                            self.linux_distro = name_match.group(1)
                        if ver_match:
                            self.linux_distro_version = ver_match.group(1)
                    if self.linux_distro:
                        break
                except FileNotFoundError:
                    pass

        if not self.linux_distro:
            self.linux_distro = "Unknown Linux"

    def _detect_desktop_environment(self) -> str:
        """Detect the desktop environment or window system."""
        if self.os_name == "Windows":
            return "Windows Desktop"
        elif self.os_name == "Darwin":
            return "Aqua (macOS Desktop)"
        elif self.os_name == "Linux":
            for env_var in ["XDG_CURRENT_DESKTOP", "DESKTOP_SESSION", "GDMSESSION"]:
                de = os.environ.get(env_var, "")
                if de:
                    return de
            # Check for common desktop environments
            if shutil.which("gnome-shell"):
                return "GNOME"
            elif shutil.which("plasmashell"):
                return "KDE Plasma"
            elif shutil.which("xfce4-session"):
                return "XFCE"
            elif shutil.which("mate-session"):
                return "MATE"
            elif shutil.which("cinnamon-session"):
                return "Cinnamon"
            return "Unknown WM"
        return "Unknown"

    @property
    def is_windows(self) -> bool:
        return self.os_name == "Windows"

    @property
    def is_linux(self) -> bool:
        return self.os_name == "Linux"

    @property
    def is_macos(self) -> bool:
        return self.os_name == "Darwin"

    def display(self):
        """Print a formatted system information summary."""
        print()
        print(colorize("=" * 60, Colors.CYAN))
        print(colorize("  SYSTEM INFORMATION", Colors.BOLD + Colors.CYAN))
        print(colorize("=" * 60, Colors.CYAN))

        info_items = [
            ("Operating System", self.os_name),
            ("OS Version", self.os_version),
            ("OS Release", self.os_release),
            ("Architecture", self.architecture),
            ("Processor", self.processor),
            ("Hostname", self.hostname),
            ("Current User", self.username),
            ("Desktop Environment", self.desktop_env),
            ("Python Version", self.python_version.split()[0]),
        ]

        if self.is_linux:
            info_items.insert(2, ("Distribution", self.linux_distro))
            if self.linux_distro_version:
                info_items.insert(3, ("Distro Version", self.linux_distro_version))

        max_label_len = max(len(label) for label, _ in info_items)

        for label, value in info_items:
            if value and value != "Unknown":
                print(f"  {colorize(label.ljust(max_label_len), Colors.BOLD)}  {colorize(value, Colors.GREEN)}")

        # Disk usage
        print()
        print(colorize("  DISK USAGE", Colors.BOLD))
        self._display_disk_usage()

        # Memory info
        print()
        print(colorize("  MEMORY", Colors.BOLD))
        self._display_memory_info()

        print(colorize("=" * 60, Colors.CYAN))
        print()

    def _display_disk_usage(self):
        """Display disk usage for all mounted filesystems."""
        try:
            if self.is_windows:
                import ctypes
                drives = []
                bitmask = ctypes.windll.kernel32.GetLogicalDrives()
                for letter in range(26):
                    if bitmask & (1 << letter):
                        drive = f"{chr(65 + letter)}:\\"
                        try:
                            total, used, free = shutil.disk_usage(drive)
                            drives.append((drive, total, used, free))
                        except Exception:
                            pass
                for drive, total, used, free in drives:
                    pct = (used / total) * 100
                    bar = self._make_bar(pct)
                    print(f"    {drive}  {self._format_bytes(total):>8} total  "
                          f"[{colorize(bar, Colors.YELLOW)}]  {pct:.1f}% used")
            else:
                import stat
                mounts = {}
                try:
                    with open("/proc/mounts", "r") as f:
                        for line in f:
                            parts = line.split()
                            if len(parts) >= 2:
                                mp = parts[1]
                                if mp.startswith("/") and not mp.startswith("/sys") and \
                                   not mp.startswith("/proc") and not mp.startswith("/dev"):
                                    mounts[mp] = mp
                except Exception:
                    mounts = {"/": "/", "/home": "/home"}

                for mp in list(mounts.keys())[:6]:
                    try:
                        stat_info = os.statvfs(mp)
                        total = stat_info.f_frsize * stat_info.f_blocks
                        free = stat_info.f_frsize * stat_info.f_bavail
                        used = total - free
                        pct = (used / total) * 100 if total > 0 else 0
                        bar = self._make_bar(pct)
                        print(f"    {mp:<20}  {self._format_bytes(total):>8} total  "
                              f"[{colorize(bar, Colors.YELLOW)}]  {pct:.1f}% used")
                    except Exception:
                        pass
        except Exception:
            print(colorize("    Could not retrieve disk information", Colors.RED))

    def _get_windows_memory(self) -> Tuple[int, int, int, float]:
        """Get Windows memory info. Returns (total, avail, used, pct)."""
        # Method 1: Try GlobalMemoryStatusEx via ctypes
        try:
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_uint32),
                    ("dwMemoryLoad", ctypes.c_uint32),
                    ("ullTotalPhys", ctypes.c_uint64),
                    ("ullAvailPhys", ctypes.c_uint64),
                    ("ullTotalPageFile", ctypes.c_uint64),
                    ("ullAvailPageFile", ctypes.c_uint64),
                    ("ullTotalVirtual", ctypes.c_uint64),
                    ("ullAvailVirtual", ctypes.c_uint64),
                ]
            mem = MEMORYSTATUSEX()
            mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            result = ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
            if result:
                total = mem.ullTotalPhys
                avail = mem.ullAvailPhys
                used = total - avail
                pct = (used / total) * 100
                return (total, avail, used, pct)
        except Exception:
            pass

        # Method 2: Fall back to PowerShell WMI query
        try:
            ps_cmd = (
                "Get-CimInstance Win32_OperatingSystem | "
                "Select-Object TotalVisibleMemorySize, FreePhysicalMemory | "
                "ConvertTo-Json"
            )
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                capture_output=True, text=True, timeout=10,
            )
            import json
            data = json.loads(result.stdout)
            # Values are in KB
            total = int(data.get("TotalVisibleMemorySize", 0)) * 1024
            avail = int(data.get("FreePhysicalMemory", 0)) * 1024
            if total > 0:
                used = total - avail
                pct = (used / total) * 100
                return (total, avail, used, pct)
        except Exception:
            pass

        return (0, 0, 0, 0.0)

    def _display_memory_info(self):
        """Display system memory information."""
        try:
            if self.is_windows:
                total, avail, used, pct = self._get_windows_memory()
                if total > 0:
                    bar = self._make_bar(pct)
                    print(f"    Total: {self._format_bytes(total)}  "
                          f"Used: {self._format_bytes(used)}  "
                          f"Free: {self._format_bytes(avail)}  "
                          f"[{colorize(bar, Colors.YELLOW)}]  {pct:.1f}%")
                else:
                    print(colorize("    Could not retrieve memory information", Colors.RED))
            else:
                try:
                    with open("/proc/meminfo", "r") as f:
                        meminfo = {}
                        for line in f:
                            parts = line.split(":")
                            if len(parts) == 2:
                                key = parts[0].strip()
                                val = parts[1].strip().split()[0]
                                meminfo[key] = int(val) * 1024
                    total = meminfo.get("MemTotal", 0)
                    avail = meminfo.get("MemAvailable", 0)
                    used = total - avail
                    pct = (used / total) * 100 if total > 0 else 0
                    bar = self._make_bar(pct)
                    print(f"    Total: {self._format_bytes(total)}  "
                          f"Used: {self._format_bytes(used)}  "
                          f"Free: {self._format_bytes(avail)}  "
                          f"[{colorize(bar, Colors.YELLOW)}]  {pct:.1f}%")
                except Exception:
                    print(colorize("    Could not retrieve memory information", Colors.RED))
        except Exception:
            print(colorize("    Could not retrieve memory information", Colors.RED))

    @staticmethod
    def _format_bytes(size: int) -> str:
        """Format bytes to human-readable size."""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if abs(size) < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} PB"

    @staticmethod
    def _make_bar(pct: float, width: int = 20) -> str:
        """Create a visual progress bar."""
        filled = int(pct / 100 * width)
        return "#" * filled + "-" * (width - filled)


# ============================================================
# TOOL DEFINITION BASE
# ============================================================

class Tool:
    """Represents a single launchable system tool."""

    def __init__(
        self,
        name: str,
        description: str,
        command: str,
        args: Optional[List[str]] = None,
        run_in_terminal: bool = False,
        requires_admin: bool = False,
        category: str = "General",
    ):
        self.name = name
        self.description = description
        self.command = command
        self.args = args or []
        self.run_in_terminal = run_in_terminal
        self.requires_admin = requires_admin
        self.category = category

    def launch(self) -> bool:
        """Launch the tool. Returns True if successful."""
        cmd_parts = [self.command] + self.args
        try:
            if self.run_in_terminal:
                return self._launch_in_terminal(cmd_parts)
            else:
                subprocess.Popen(
                    cmd_parts,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                )
            return True
        except FileNotFoundError:
            print(colorize(f"  Error: Command not found: {self.command}", Colors.RED))
            return False
        except Exception as e:
            print(colorize(f"  Error launching {self.name}: {e}", Colors.RED))
            return False

    def _launch_in_terminal(self, cmd_parts: list) -> bool:
        """Launch a command in a new terminal window."""
        full_cmd = " ".join(cmd_parts)
        system = platform.system()

        if system == "Windows":
            # Use start with a new cmd window
            subprocess.Popen(
                ["cmd", "/c", "start", f'"{self.name}"', "cmd", "/k", full_cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        elif system == "Darwin":
            # macOS - use osascript to open Terminal
            script = f'tell application "Terminal" to do script "{full_cmd}"'
            subprocess.Popen(
                ["osascript", "-e", script],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            # Linux - try various terminal emulators
            terminals = [
                ["gnome-terminal", "--", "bash", "-c", f"{full_cmd}; echo; read -p 'Press Enter to close...'"],
                ["konsole", "-e", "bash", "-c", f"{full_cmd}; echo; read -p 'Press Enter to close...'"],
                ["xfce4-terminal", "-e", f"bash -c '{full_cmd}; echo; read -p \"Press Enter to close...\"'"],
                ["x-terminal-emulator", "-e", f"bash -c '{full_cmd}; echo; read -p \"Press Enter to close...\"'"],
                ["lxterminal", "-e", f"bash -c '{full_cmd}; echo; read -p \"Press Enter to close...\"'"],
                ["mate-terminal", "-e", f"bash -c '{full_cmd}; echo; read -p \"Press Enter to close...\"'"],
                ["terminator", "-e", f"bash -c '{full_cmd}; echo; read -p \"Press Enter to close...\"'"],
                ["alacritty", "-e", "bash", "-c", f"{full_cmd}; echo; read -p 'Press Enter to close...'"],
                ["kitty", "bash", "-c", f"{full_cmd}; echo; read -p 'Press Enter to close...'"],
            ]
            for term_cmd in terminals:
                if shutil.which(term_cmd[0]):
                    subprocess.Popen(
                        term_cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return True
            # Fallback: just run in current terminal
            print(colorize("  No terminal emulator found. Running inline...", Colors.YELLOW))
            try:
                subprocess.run(cmd_parts)
            except KeyboardInterrupt:
                pass
        return True

    def display(self, index: int):
        """Display tool in a list."""
        admin_marker = colorize(" [ADMIN]", Colors.RED) if self.requires_admin else ""
        num = colorize(f"  [{index}]", Colors.BOLD + Colors.GREEN)
        name_str = colorize(self.name, Colors.BOLD)
        desc_str = colorize(f" - {self.description}", Colors.DIM)
        print(f"{num} {name_str}{admin_marker}{desc_str}")


class ToolCategory:
    """A collection of related tools."""

    def __init__(self, name: str, icon: str = ""):
        self.name = name
        self.icon = icon
        self.tools: List[Tool] = []

    def add(self, tool: Tool):
        self.tools.append(tool)

    def display(self):
        """Display the category header."""
        header = f"  {self.icon} {self.name} {self.icon}"
        print()
        print(colorize(f"  {'─' * 50}", Colors.CYAN))
        print(colorize(header, Colors.BOLD + Colors.MAGENTA))
        print(colorize(f"  {'─' * 50}", Colors.CYAN))


# ============================================================
# WINDOWS TOOLS
# ============================================================

class WindowsToolProvider:
    """Provides all Windows system tools."""

    @staticmethod
    def get_tools() -> List[ToolCategory]:
        categories = []

        # --- System Management ---
        cat = ToolCategory("System Management", "[#]")
        cat.add(Tool("Task Manager", "Monitor processes, performance, and startup programs", "taskmgr"))
        cat.add(Tool("System Information", "View detailed system hardware and software info", "msinfo32"))
        cat.add(Tool("System Configuration", "Manage startup, services, and boot options", "msconfig"))
        cat.add(Tool("System Properties", "View and configure system properties", "sysdm.cpl"))
        cat.add(Tool("Computer Management", "Manage disks, users, services, and devices", "compmgmt.msc"))
        cat.add(Tool("Windows Security", "Open Windows Security / Defender dashboard", "windowsdefender://"))
        cat.add(Tool("Windows Update", "Check for and install Windows updates", "ms-settings:windowsupdate"))
        cat.add(Tool("About Windows", "View Windows version and activation info", "winver"))
        cat.add(Tool("DirectX Diagnostic", "Diagnose DirectX and display issues", "dxdiag"))
        cat.add(Tool("Performance Monitor", "Advanced system performance monitoring", "perfmon.msc"))
        cat.add(Tool("Resource Monitor", "Real-time resource usage monitor", "resmon"))
        cat.add(Tool("Reliability Monitor", "View system reliability history", "perfmon", ["/rel"]))
        categories.append(cat)

        # --- Disk and Storage ---
        cat = ToolCategory("Disk and Storage", "[=]")
        cat.add(Tool("Disk Management", "Manage disks, partitions, and volumes", "diskmgmt.msc"))
        cat.add(Tool("Disk Cleanup", "Free up disk space by removing temporary files", "cleanmgr"))
        cat.add(Tool("Optimize Drives", "Defragment and optimize drives", "dfrgui"))
        cat.add(Tool("Storage Settings", "View and manage storage usage", "ms-settings:storagesense"))
        categories.append(cat)

        # --- Device and Hardware ---
        cat = ToolCategory("Device and Hardware", "[+]")
        cat.add(Tool("Device Manager", "Manage hardware devices and drivers", "devmgmt.msc"))
        cat.add(Tool("Printers and Scanners", "Manage printers and scanner devices", "control", ["printers"]))
        cat.add(Tool("Sound Settings", "Configure audio devices and volume", "mmsys.cpl"))
        cat.add(Tool("Display Settings", "Configure monitors and display resolution", "desk.cpl"))
        cat.add(Tool("Bluetooth Settings", "Manage Bluetooth devices", "ms-settings:bluetooth"))
        categories.append(cat)

        # --- Network and Internet ---
        cat = ToolCategory("Network and Internet", "[~]")
        cat.add(Tool("Network Connections", "View and configure network adapters", "ncpa.cpl"))
        cat.add(Tool("Network Status", "View network status and settings", "ms-settings:network"))
        cat.add(Tool("Windows Firewall", "Configure Windows Defender Firewall", "firewall.cpl"))
        cat.add(Tool("Advanced Firewall", "Advanced firewall with inbound/outbound rules", "wf.msc"))
        cat.add(Tool("Internet Options", "Configure internet properties and security", "inetcpl.cpl"))
        categories.append(cat)

        # --- Administration ---
        cat = ToolCategory("Administration", "[!]")
        cat.add(Tool("Services", "Manage Windows services", "services.msc"))
        cat.add(Tool("Registry Editor", "Edit the Windows registry", "regedit"))
        cat.add(Tool("Event Viewer", "View system and application event logs", "eventvwr.msc"))
        cat.add(Tool("Task Scheduler", "Schedule automated tasks", "taskschd.msc"))
        cat.add(Tool("Local Group Policy", "Edit local group policy settings", "gpedit.msc"))
        cat.add(Tool("Local Users and Groups", "Manage local users and groups", "lusrmgr.msc"))
        cat.add(Tool("Shared Folders", "Manage shared folders and sessions", "fsmgmt.msc"))
        cat.add(Tool("Certificate Manager", "Manage system and user certificates", "certmgr.msc"))
        cat.add(Tool("ODBC Data Sources", "Configure database connections", "odbcad32"))
        cat.add(Tool("Print Management", "Manage print servers and printers", "printmanagement.msc"))
        categories.append(cat)

        # --- Control Panel ---
        cat = ToolCategory("Control Panel", "[*]")
        cat.add(Tool("Control Panel Home", "Open the main Control Panel", "control"))
        cat.add(Tool("Programs and Features", "Install, uninstall, and modify programs", "appwiz.cpl"))
        cat.add(Tool("Power Options", "Configure power plans and sleep settings", "powercfg.cpl"))
        cat.add(Tool("Date and Time", "Set date, time, and time zone", "timedate.cpl"))
        cat.add(Tool("User Accounts", "Manage user accounts and passwords", "control", ["userpasswords2"]))
        cat.add(Tool("Ease of Access", "Accessibility settings", "utilman"))
        cat.add(Tool("Color Management", "Configure color profiles for displays", "colorcpl"))
        cat.add(Tool("File Explorer Options", "Configure folder and file explorer behavior", "control", ["folders"]))
        cat.add(Tool("Mouse Settings", "Configure mouse buttons and cursor", "main.cpl"))
        cat.add(Tool("Keyboard Settings", "Configure keyboard repeat and layout", "control", ["keyboard"]))
        cat.add(Tool("Region Settings", "Configure language and regional formats", "intl.cpl"))
        categories.append(cat)

        # --- Command Line ---
        cat = ToolCategory("Command Line and Scripting", "[>]")
        cat.add(Tool("Command Prompt", "Open Windows Command Prompt", "cmd", run_in_terminal=True))
        cat.add(Tool("PowerShell", "Open Windows PowerShell", "powershell", run_in_terminal=True))
        cat.add(Tool("PowerShell ISE", "PowerShell Integrated Scripting Environment", "powershell_ise"))
        cat.add(Tool("Windows Terminal", "Modern terminal app for Windows", "wt"))
        cat.add(Tool("Run Dialog", "Open the Run dialog", "cmd", ["/c", "start", "shell:::{2559a1f3-21d7-11d4-bdaf-00c04f60b9f0}"]))
        categories.append(cat)

        # --- Recovery and Diagnostics ---
        cat = ToolCategory("Recovery and Diagnostics", "[?]")
        cat.add(Tool("System Restore", "Create or restore system restore points", "rstrui"))
        cat.add(Tool("Memory Diagnostic", "Check for memory problems", "mdsched"))
        cat.add(Tool("Disk Error Check", "Check disk for errors (CHKDSK GUI)", "cmd", ["/c", "start", "chkdsk"], run_in_terminal=True))
        cat.add(Tool("System File Checker", "Scan and repair system files", "cmd", ["/c", "start", "cmd", "/k", "sfc /scannow"], run_in_terminal=True))
        cat.add(Tool("Malicious Software Removal", "Run the Malicious Software Removal Tool", "mrt"))
        cat.add(Tool("Steps Recorder", "Record steps to reproduce a problem", "psr"))
        categories.append(cat)

        return categories


# ============================================================
# LINUX TOOLS
# ============================================================

class LinuxToolProvider:
    """Provides all Linux system tools."""

    @staticmethod
    def get_tools() -> List[ToolCategory]:
        categories = []

        # --- System Monitoring ---
        cat = ToolCategory("System Monitoring", "[#]")
        cat.add(Tool("top - Process Monitor", "Interactive process and resource monitor", "top", run_in_terminal=True))
        if shutil.which("htop"):
            cat.add(Tool("htop - Enhanced Process Viewer", "Colorful interactive process monitor", "htop", run_in_terminal=True))
        if shutil.which("btm"):
            cat.add(Tool("btm - Bottom Monitor", "Modern graphical system monitor", "btm", run_in_terminal=True))
        if shutil.which("glances"):
            cat.add(Tool("glances - System Dashboard", "Comprehensive system monitoring dashboard", "glances", run_in_terminal=True))
        cat.add(Tool("uptime - System Uptime", "Show how long the system has been running", "uptime", run_in_terminal=True))
        cat.add(Tool("vmstat - Virtual Memory Stats", "Report virtual memory statistics", "vmstat", ["1", "5"], run_in_terminal=True))
        cat.add(Tool("iostat - IO Statistics", "Report CPU and I/O statistics", "iostat", ["-x", "1", "3"], run_in_terminal=True))
        cat.add(Tool("dstat - System Stats", "Versatile system resource statistics", "dstat", run_in_terminal=True))
        categories.append(cat)

        # --- Process Management ---
        cat = ToolCategory("Process Management", "[&]")
        cat.add(Tool("ps - Process List", "Display current running processes", "ps", ["aux", "--sort=-%mem"], run_in_terminal=True))
        cat.add(Tool("pstree - Process Tree", "Display processes in tree format", "pstree", run_in_terminal=True))
        if shutil.which("pkill"):
            cat.add(Tool("pkill - Kill Process", "Kill a process by name (interactive)", "bash", ["-c", "read -p 'Process name to kill: ' pn; pkill $pn"], run_in_terminal=True))
        if shutil.which("lsof"):
            cat.add(Tool("lsof - List Open Files", "List open files and their processes", "lsof", ["-i"], run_in_terminal=True))
        categories.append(cat)

        # --- Memory and CPU ---
        cat = ToolCategory("Memory and CPU", "[%]")
        cat.add(Tool("free - Memory Info", "Display memory usage information", "free", ["-h"], run_in_terminal=True))
        cat.add(Tool("lscpu - CPU Information", "Display CPU architecture information", "lscpu", run_in_terminal=True))
        cat.add(Tool("lshw - Hardware List", "List detailed hardware information", "lshw", ["-short"], run_in_terminal=True))
        if shutil.which("cpufreq-info"):
            cat.add(Tool("cpufreq-info", "Show CPU frequency information", "cpufreq-info", run_in_terminal=True))
        if shutil.which("sensors"):
            cat.add(Tool("sensors - Temperature", "Show CPU and system temperatures", "sensors", run_in_terminal=True))
        cat.add(Tool("/proc/cpuinfo", "View CPU details", "cat", ["/proc/cpuinfo"], run_in_terminal=True))
        cat.add(Tool("/proc/meminfo", "View memory details", "cat", ["/proc/meminfo"], run_in_terminal=True))
        categories.append(cat)

        # --- Disk and Storage ---
        cat = ToolCategory("Disk and Storage", "[=]")
        cat.add(Tool("df - Disk Free", "Show disk space usage for all filesystems", "df", ["-h"], run_in_terminal=True))
        cat.add(Tool("du - Disk Usage", "Show directory space usage (current dir)", "du", ["-sh", "."], run_in_terminal=True))
        if shutil.which("ncdu"):
            cat.add(Tool("ncdu - Interactive Disk Usage", "Interactive disk usage analyzer", "ncdu", run_in_terminal=True))
        cat.add(Tool("lsblk - List Block Devices", "List all block devices and partitions", "lsblk", ["-f"], run_in_terminal=True))
        cat.add(Tool("blkid - Block Device IDs", "Show block device attributes", "blkid", run_in_terminal=True))
        cat.add(Tool("fdisk - Partition Table", "List partition tables (all devices)", "fdisk", ["-l"], run_in_terminal=True))
        if shutil.which("iotop"):
            cat.add(Tool("iotop - IO Monitor", "Monitor disk I/O by process", "iotop", run_in_terminal=True))
        cat.add(Tool("mount - List Mounts", "Show all mounted filesystems", "mount", run_in_terminal=True))
        if shutil.which("swapon"):
            cat.add(Tool("swapon - Swap Info", "Show swap usage summary", "swapon", ["--show"], run_in_terminal=True))
        categories.append(cat)

        # --- Network ---
        cat = ToolCategory("Network and Internet", "[~]")
        cat.add(Tool("ip addr - IP Addresses", "Show network interfaces and IP addresses", "ip", ["addr", "show"], run_in_terminal=True))
        cat.add(Tool("ip route - Routing Table", "Show the IP routing table", "ip", ["route"], run_in_terminal=True))
        cat.add(Tool("ss - Socket Statistics", "Show network socket connections", "ss", ["-tulpn"], run_in_terminal=True))
        if shutil.which("netstat"):
            cat.add(Tool("netstat - Network Stats", "Network connections and statistics", "netstat", ["-tulpn"], run_in_terminal=True))
        if shutil.which("ping"):
            cat.add(Tool("Ping Test", "Test network connectivity to 8.8.8.8", "ping", ["-c", "4", "8.8.8.8"], run_in_terminal=True))
        if shutil.which("traceroute"):
            cat.add(Tool("traceroute", "Trace network path to destination", "bash", ["-c", "read -p 'Host to trace: ' host; traceroute $host"], run_in_terminal=True))
        if shutil.which("nmap"):
            cat.add(Tool("nmap - Network Scanner", "Network discovery and security scanning", "nmap", run_in_terminal=True))
        if shutil.which("iftop"):
            cat.add(Tool("iftop - Bandwidth Monitor", "Display bandwidth usage on an interface", "iftop", run_in_terminal=True))
        if shutil.which("nslookup"):
            cat.add(Tool("nslookup", "Query DNS records", "bash", ["-c", "read -p 'Domain to lookup: ' domain; nslookup $domain"], run_in_terminal=True))
        if shutil.which("dig"):
            cat.add(Tool("dig - DNS Lookup", "Advanced DNS query tool", "bash", ["-c", "read -p 'Domain to query: ' domain; dig $domain ANY"], run_in_terminal=True))
        if shutil.which("wget") or shutil.which("curl"):
            cat.add(Tool("Public IP Check", "Show your public IP address", "curl" if shutil.which("curl") else "wget", ["-qO-", "ifconfig.me"], run_in_terminal=True))
        categories.append(cat)

        # --- Services and Systemd ---
        cat = ToolCategory("Services and SystemD", "[!]")
        cat.add(Tool("systemctl - Services", "List all running services", "systemctl", ["list-units", "--type=service", "--state=running"], run_in_terminal=True))
        cat.add(Tool("systemctl - All Units", "List all systemd units", "systemctl", ["list-units"], run_in_terminal=True))
        cat.add(Tool("systemctl - Failed", "Show failed systemd units", "systemctl", ["--failed"], run_in_terminal=True))
        cat.add(Tool("journalctl - Boot Log", "Show logs from current boot", "journalctl", ["-b"], run_in_terminal=True))
        cat.add(Tool("journalctl - Errors", "Show error level messages", "journalctl", ["-p", "3", "-xb"], run_in_terminal=True))
        cat.add(Tool("systemd-analyze", "Analyze system boot performance", "systemd-analyze", run_in_terminal=True))
        cat.add(Tool("systemd-analyze blame", "Show boot time by component", "systemd-analyze", ["blame"], run_in_terminal=True))
        cat.add(Tool("timedatectl - Time Settings", "Show date and time configuration", "timedatectl", ["status"], run_in_terminal=True))
        cat.add(Tool("hostnamectl - Host Info", "Show hostname and system info", "hostnamectl", ["status"], run_in_terminal=True))
        categories.append(cat)

        # --- User and Group Management ---
        cat = ToolCategory("Users and Groups", "[@]")
        cat.add(Tool("who - Logged In Users", "Show who is currently logged in", "who", run_in_terminal=True))
        cat.add(Tool("w - User Activity", "Show who is logged in and what they're doing", "w", run_in_terminal=True))
        cat.add(Tool("last - Login History", "Show recent login history", "last", ["-n", "20"], run_in_terminal=True))
        cat.add(Tool("id - User Info", "Show current user and group IDs", "id", run_in_terminal=True))
        cat.add(Tool("groups - Group List", "List groups for current user", "groups", run_in_terminal=True))
        cat.add(Tool("/etc/passwd", "View all user accounts", "cat", ["/etc/passwd"], run_in_terminal=True))
        cat.add(Tool("/etc/group", "View all groups", "cat", ["/etc/group"], run_in_terminal=True))
        categories.append(cat)

        # --- Package Management ---
        cat = ToolCategory("Package Management", "[+]")
        if shutil.which("apt"):
            cat.add(Tool("apt - List Installed", "List installed packages", "apt", ["list", "--installed"], run_in_terminal=True))
            cat.add(Tool("apt - Update", "Update package list", "apt", ["update"], run_in_terminal=True))
            cat.add(Tool("apt - Upgradable", "List upgradable packages", "apt", ["list", "--upgradable"], run_in_terminal=True))
        elif shutil.which("dnf"):
            cat.add(Tool("dnf - List Installed", "List installed packages", "dnf", ["list", "installed"], run_in_terminal=True))
            cat.add(Tool("dnf - Check Updates", "Check for available updates", "dnf", ["check-update"], run_in_terminal=True))
        elif shutil.which("yum"):
            cat.add(Tool("yum - List Installed", "List installed packages", "yum", ["list", "installed"], run_in_terminal=True))
        elif shutil.which("pacman"):
            cat.add(Tool("pacman - List Installed", "List installed packages", "pacman", ["-Q"], run_in_terminal=True))
            cat.add(Tool("pacman - Updates", "Check for updates", "pacman", ["-Qu"], run_in_terminal=True))
        elif shutil.which("zypper"):
            cat.add(Tool("zypper - List Installed", "List installed packages", "zypper", ["search", "-i"], run_in_terminal=True))
        if shutil.which("snap"):
            cat.add(Tool("snap - List Installed", "List installed snap packages", "snap", ["list"], run_in_terminal=True))
        if shutil.which("flatpak"):
            cat.add(Tool("flatpak - List Installed", "List installed flatpaks", "flatpak", ["list"], run_in_terminal=True))
        if shutil.which("pip"):
            cat.add(Tool("pip - List Packages", "List installed Python packages", "pip", ["list"], run_in_terminal=True))
        categories.append(cat)

        # --- Logs and Diagnostics ---
        cat = ToolCategory("Logs and Diagnostics", "[?]")
        cat.add(Tool("dmesg - Kernel Messages", "Print kernel ring buffer messages", "dmesg", ["-H"], run_in_terminal=True))
        cat.add(Tool("dmesg - Errors/Warnings", "Show only error and warning kernel messages", "dmesg", ["--level=err,warn"], run_in_terminal=True))
        if os.path.exists("/var/log/syslog"):
            cat.add(Tool("syslog Tail", "View last 50 lines of syslog", "tail", ["-n", "50", "/var/log/syslog"], run_in_terminal=True))
        if os.path.exists("/var/log/auth.log"):
            cat.add(Tool("Auth Log Tail", "View last 50 lines of auth log", "tail", ["-n", "50", "/var/log/auth.log"], run_in_terminal=True))
        if os.path.exists("/var/log/kern.log"):
            cat.add(Tool("Kernel Log Tail", "View last 50 lines of kernel log", "tail", ["-n", "50", "/var/log/kern.log"], run_in_terminal=True))
        if shutil.which("lsmod"):
            cat.add(Tool("lsmod - Kernel Modules", "List loaded kernel modules", "lsmod", run_in_terminal=True))
        if shutil.which("modinfo"):
            cat.add(Tool("modinfo - Module Info", "Show module information (interactive)", "bash", ["-c", "read -p 'Module name: ' mod; modinfo $mod"], run_in_terminal=True))
        categories.append(cat)

        # --- Firewall and Security ---
        cat = ToolCategory("Firewall and Security", "[^]")
        if shutil.which("ufw"):
            cat.add(Tool("ufw - Firewall Status", "Show UFW firewall status", "ufw", ["status", "verbose"], run_in_terminal=True))
        elif shutil.which("firewall-cmd"):
            cat.add(Tool("firewall-cmd - Status", "Show firewalld status", "firewall-cmd", ["--list-all"], run_in_terminal=True))
        if shutil.which("iptables"):
            cat.add(Tool("iptables - Rules", "Show iptables firewall rules", "iptables", ["-L", "-n", "-v"], run_in_terminal=True))
        if shutil.which("fail2ban-client"):
            cat.add(Tool("fail2ban - Status", "Show fail2ban status", "fail2ban-client", ["status"], run_in_terminal=True))
        if shutil.which("aa-status"):
            cat.add(Tool("AppArmor Status", "Show AppArmor security profiles", "aa-status", run_in_terminal=True))
        if shutil.which("sestatus"):
            cat.add(Tool("SELinux Status", "Show SELinux enforcement status", "sestatus", run_in_terminal=True))
        categories.append(cat)

        # --- System Information ---
        cat = ToolCategory("System Information", "[i]")
        cat.add(Tool("uname - System Info", "Print system information", "uname", ["-a"], run_in_terminal=True))
        cat.add(Tool("lsb_release - Distro Info", "Show Linux distribution details", "lsb_release", ["-a"], run_in_terminal=True))
        cat.add(Tool("hostnamectl", "Show full hostname details", "hostnamectl", run_in_terminal=True))
        if shutil.which("neofetch"):
            cat.add(Tool("neofetch - System Info Art", "Display system info with ASCII art", "neofetch", run_in_terminal=True))
        if shutil.which("screenfetch"):
            cat.add(Tool("screenfetch", "Display system info with ASCII art", "screenfetch", run_in_terminal=True))
        if shutil.which("inxi"):
            cat.add(Tool("inxi - System Report", "Comprehensive system information", "inxi", ["-Fxz"], run_in_terminal=True))
        cat.add(Tool("lspci - PCI Devices", "List all PCI devices", "lspci", run_in_terminal=True))
        cat.add(Tool("lsusb - USB Devices", "List all USB devices", "lsusb", run_in_terminal=True))
        cat.add(Tool("/proc/version", "View kernel version", "cat", ["/proc/version"], run_in_terminal=True))
        if shutil.which("dmidecode"):
            cat.add(Tool("dmidecode - DMI Info", "Show DMI/SMBIOS hardware info", "dmidecode", ["-t", "system"], run_in_terminal=True))
        categories.append(cat)

        # --- File Management ---
        cat = ToolCategory("File Management", "[f]")
        if shutil.which("mc"):
            cat.add(Tool("mc - Midnight Commander", "Text-based file manager", "mc", run_in_terminal=True))
        if shutil.which("ranger"):
            cat.add(Tool("ranger", "VIM-inspired file manager", "ranger", run_in_terminal=True))
        cat.add(Tool("find - Large Files", "Find files larger than 100MB in /home", "bash", ["-c", "find /home -type f -size +100M 2>/dev/null | head -20"], run_in_terminal=True))
        cat.add(Tool("find - Recent Files", "Find files modified in last 24h in /home", "bash", ["-c", "find /home -type f -mtime -1 2>/dev/null | head -30"], run_in_terminal=True))
        categories.append(cat)

        return categories


# ============================================================
# MACOS TOOLS
# ============================================================

class MacOSToolProvider:
    """Provides all macOS system tools."""

    @staticmethod
    def get_tools() -> List[ToolCategory]:
        categories = []

        # --- System Monitoring ---
        cat = ToolCategory("System Monitoring", "[#]")
        cat.add(Tool("Activity Monitor", "Monitor processes, CPU, memory, energy, disk, and network", "open", ["-a", "Activity Monitor"]))
        cat.add(Tool("System Information", "View detailed system hardware and software report", "open", ["-a", "System Information"]))
        if shutil.which("htop"):
            cat.add(Tool("htop - Process Monitor", "Interactive terminal process monitor", "htop", run_in_terminal=True))
        cat.add(Tool("top - Process Monitor (CLI)", "Command-line process monitor", "top", run_in_terminal=True))
        cat.add(Tool("vm_stat - Memory Stats", "Show virtual memory statistics", "vm_stat", run_in_terminal=True))
        if shutil.which("iostat"):
            cat.add(Tool("iostat - IO Statistics", "Report I/O statistics", "iostat", run_in_terminal=True))
        categories.append(cat)

        # --- Disk and Storage ---
        cat = ToolCategory("Disk and Storage", "[=]")
        cat.add(Tool("Disk Utility", "Manage disks, partitions, and volumes", "open", ["-a", "Disk Utility"]))
        cat.add(Tool("df - Disk Free (CLI)", "Show disk space usage", "df", ["-h"], run_in_terminal=True))
        cat.add(Tool("du - Disk Usage (CLI)", "Show current directory disk usage", "du", ["-sh", "."], run_in_terminal=True))
        cat.add(Tool("diskutil list", "List all disks and partitions (CLI)", "diskutil", ["list"], run_in_terminal=True))
        cat.add(Tool("diskutil info", "Show disk information (CLI)", "bash", ["-c", "read -p 'Disk (e.g., disk0): ' disk; diskutil info /dev/$disk"], run_in_terminal=True))
        categories.append(cat)

        # --- System Settings ---
        cat = ToolCategory("System Settings", "[*]")
        cat.add(Tool("System Settings", "Open macOS System Settings", "open", ["-a", "System Settings"]))
        cat.add(Tool("System Preferences (Legacy)", "Open legacy System Preferences", "open", ["-a", "System Preferences"]))
        cat.add(Tool("Network Settings", "Open network preferences directly", "open", ["x-apple.systempreferences:com.apple.preference.network"]))
        cat.add(Tool("Display Settings", "Open display preferences", "open", ["x-apple.systempreferences:com.apple.preference.displays"]))
        cat.add(Tool("Sound Settings", "Open sound preferences", "open", ["x-apple.systempreferences:com.apple.preference.sound"]))
        cat.add(Tool("Bluetooth Settings", "Open Bluetooth preferences", "open", ["x-apple.systempreferences:com.apple.preference.Bluetooth"]))
        cat.add(Tool("Printers and Scanners", "Open printer preferences", "open", ["x-apple.systempreferences:com.apple.preference.printfax"]))
        cat.add(Tool("Battery Settings", "Open battery/energy saver preferences", "open", ["x-apple.systempreferences:com.apple.preference.battery"]))
        cat.add(Tool("Date and Time", "Open date & time preferences", "open", ["x-apple.systempreferences:com.apple.preference.datetime"]))
        cat.add(Tool("Users and Groups", "Open users & groups preferences", "open", ["x-apple.systempreferences:com.apple.preference.users"]))
        cat.add(Tool("Accessibility", "Open accessibility preferences", "open", ["x-apple.systempreferences:com.apple.preference.universalaccess"]))
        cat.add(Tool("Software Update", "Open software update preferences", "open", ["x-apple.systempreferences:com.apple.preferences.softwareupdate"]))
        categories.append(cat)

        # --- Utilities ---
        cat = ToolCategory("Utilities", "[!]")
        cat.add(Tool("Terminal", "Open macOS Terminal", "open", ["-a", "Terminal"]))
        cat.add(Tool("Console", "View system logs and diagnostic messages", "open", ["-a", "Console"]))
        cat.add(Tool("Keychain Access", "Manage passwords and certificates", "open", ["-a", "Keychain Access"]))
        cat.add(Tool("Script Editor", "Edit and run AppleScript scripts", "open", ["-a", "Script Editor"]))
        cat.add(Tool("Automator", "Create automated workflows", "open", ["-a", "Automator"]))
        cat.add(Tool("ColorSync Utility", "Manage color profiles", "open", ["-a", "ColorSync Utility"]))
        cat.add(Tool("Digital Color Meter", "Pick colors from the screen", "open", ["-a", "Digital Color Meter"]))
        cat.add(Tool("Grapher", "Graph equations and data", "open", ["-a", "Grapher"]))
        cat.add(Tool("Screenshot", "Open screenshot utility", "open", ["-a", "Screenshot"]))
        categories.append(cat)

        # --- Network Tools ---
        cat = ToolCategory("Network Tools", "[~]")
        cat.add(Tool("Network Utility (Legacy)", "Network diagnostics utility", "open", ["-a", "Network Utility"]))
        cat.add(Tool("AirPort Utility", "Manage Apple WiFi base stations", "open", ["-a", "AirPort Utility"]))
        cat.add(Tool("ifconfig - Network Info (CLI)", "Show network interface configuration", "ifconfig", run_in_terminal=True))
        cat.add(Tool("netstat - Connections (CLI)", "Show network statistics", "netstat", ["-an"], run_in_terminal=True))
        cat.add(Tool("arp - ARP Table (CLI)", "Show ARP table", "arp", ["-a"], run_in_terminal=True))
        cat.add(Tool("Ping Test (CLI)", "Ping google.com to test connectivity", "ping", ["-c", "4", "google.com"], run_in_terminal=True))
        if shutil.which("traceroute"):
            cat.add(Tool("traceroute (CLI)", "Trace network path to destination", "bash", ["-c", "read -p 'Host: ' host; traceroute $host"], run_in_terminal=True))
        if shutil.which("nslookup"):
            cat.add(Tool("nslookup (CLI)", "DNS lookup tool", "bash", ["-c", "read -p 'Domain: ' domain; nslookup $domain"], run_in_terminal=True))
        if shutil.which("dig"):
            cat.add(Tool("dig (CLI)", "Advanced DNS query", "bash", ["-c", "read -p 'Domain: ' domain; dig $domain ANY"], run_in_terminal=True))
        categories.append(cat)

        # --- System Management CLI ---
        cat = ToolCategory("System Management (CLI)", "[>]")
        cat.add(Tool("system_profiler", "Full system hardware/software report", "system_profiler", ["SPSoftwareDataType", "SPHardwareDataType"], run_in_terminal=True))
        cat.add(Tool("sysctl - System Info", "View kernel state and system info", "sysctl", ["-a"], run_in_terminal=True))
        cat.add(Tool("launchctl - Services", "List launchd services", "launchctl", ["list"], run_in_terminal=True))
        cat.add(Tool("ps - Process List", "Show running processes", "ps", ["aux", "-m"], run_in_terminal=True))
        cat.add(Tool("lsof - Open Files", "List open files (as root shows all)", "lsof", run_in_terminal=True))
        cat.add(Tool("pmset - Power Settings", "Show power management settings", "pmset", ["-g"], run_in_terminal=True))
        cat.add(Tool("nvram - Firmware Vars", "Show firmware variables", "nvram", ["-p"], run_in_terminal=True))
        cat.add(Tool("systemsetup", "Show system setup configuration", "systemsetup", ["-print"], run_in_terminal=True))
        cat.add(Tool("softwareupdate - History", "Show software update history", "softwareupdate", ["--history"], run_in_terminal=True))
        cat.add(Tool("softwareupdate - List", "List available software updates", "softwareupdate", ["-l"], run_in_terminal=True))
        if shutil.which("brew"):
            cat.add(Tool("Homebrew - Installed", "List Homebrew-installed packages", "brew", ["list", "--versions"], run_in_terminal=True))
            cat.add(Tool("Homebrew - Outdated", "List outdated Homebrew packages", "brew", ["outdated"], run_in_terminal=True))
        if shutil.which("pip"):
            cat.add(Tool("pip - Python Packages", "List installed Python packages", "pip", ["list"], run_in_terminal=True))
        categories.append(cat)

        # --- Directory and File Tools ---
        cat = ToolCategory("File and Directory Tools", "[f]")
        cat.add(Tool("Finder", "Open Finder", "open", ["-a", "Finder"]))
        cat.add(Tool("Font Book", "Manage system fonts", "open", ["-a", "Font Book"]))
        cat.add(Tool("TextEdit", "Simple text editor", "open", ["-a", "TextEdit"]))
        cat.add(Tool("Home Folder", "Open current user home folder", "open", [os.path.expanduser("~")]))
        cat.add(Tool("Applications Folder", "Open Applications folder", "open", ["/Applications"]))
        cat.add(Tool("Utilities Folder", "Open Utilities folder", "open", ["/Applications/Utilities"]))
        cat.add(Tool("Downloads Folder", "Open Downloads folder", "open", [os.path.expanduser("~/Downloads")]))
        cat.add(Tool("Desktop Folder", "Open Desktop folder", "open", [os.path.expanduser("~/Desktop")]))
        categories.append(cat)

        return categories


# ============================================================
# TOOL LAUNCHER / MENU SYSTEM
# ============================================================

class ToolMenu:
    """Interactive menu system for browsing and launching tools."""

    def __init__(self, system_info: SystemInfo):
        self.sys_info = system_info
        self.categories: List[ToolCategory] = []
        self._load_tools()

    def _load_tools(self):
        """Load tools appropriate for the current operating system."""
        if self.sys_info.is_windows:
            self.categories = WindowsToolProvider.get_tools()
        elif self.sys_info.is_linux:
            self.categories = LinuxToolProvider.get_tools()
        elif self.sys_info.is_macos:
            self.categories = MacOSToolProvider.get_tools()

    def run(self):
        """Start the interactive menu loop."""
        while True:
            self._clear_screen()
            self._print_header()
            self._print_categories()

            choice = self._get_choice()

            if choice == "0":
                break
            elif choice == "i":
                self.sys_info.display()
                input(colorize("\n  Press Enter to return to menu...", Colors.DIM))
            elif choice == "r":
                # Refresh tools (in case something changed)
                self._load_tools()
                print(colorize("\n  Tools refreshed.", Colors.GREEN))
                time.sleep(1)
            else:
                self._handle_category_choice(choice)

        self._print_goodbye()

    def _clear_screen(self):
        """Clear the terminal screen."""
        if os.name == "nt":
            os.system("cls")
        else:
            os.system("clear")

    def _print_header(self):
        """Print the main header with system info."""
        print()
        print(colorize("╔" + "═" * 58 + "╗", Colors.CYAN))
        print(colorize("║", Colors.CYAN) + colorize("  COMPUTERTOOL - System Tools Launcher v1.0.0", Colors.BOLD + Colors.WHITE).center(58) + colorize("║", Colors.CYAN))
        print(colorize("╠" + "═" * 58 + "╣", Colors.CYAN))

        if self.sys_info.is_windows:
            os_label = f"Windows {self.sys_info.os_release}"
        elif self.sys_info.is_linux:
            os_label = f"{self.sys_info.linux_distro} {self.sys_info.linux_distro_version}"
        else:
            os_label = f"macOS {self.sys_info.os_release}"

        info_line = f"  OS: {os_label}  |  Arch: {self.sys_info.architecture}  |  User: {self.sys_info.username}"
        print(colorize("║", Colors.CYAN) + info_line.ljust(58)[:58] + colorize("║", Colors.CYAN))
        print(colorize("╚" + "═" * 58 + "╝", Colors.CYAN))

    def _print_categories(self):
        """Print all tool categories with their tools."""
        print()
        print(colorize("  CATEGORIES:", Colors.BOLD + Colors.YELLOW))
        print()

        for idx, category in enumerate(self.categories, 1):
            tool_count = len(category.tools)
            letter = colorize(f"  [{idx}]", Colors.BOLD + Colors.GREEN)
            name = colorize(category.name, Colors.BOLD)
            count = colorize(f"({tool_count} tools)", Colors.DIM)
            print(f"{letter} {name}  {count}")

        print()
        print(colorize(f"  [0] ", Colors.BOLD + Colors.RED) + colorize("Exit", Colors.RED))
        print(colorize(f"  [i] ", Colors.BOLD + Colors.BLUE) + colorize("Show System Information", Colors.BLUE))
        print(colorize(f"  [r] ", Colors.BOLD + Colors.BLUE) + colorize("Refresh Tool List", Colors.BLUE))
        print()

    def _get_choice(self) -> str:
        """Get menu choice from user."""
        try:
            choice = input(colorize("  Enter your choice > ", Colors.BOLD + Colors.GREEN)).strip().lower()
            return choice
        except (EOFError, KeyboardInterrupt):
            return "0"

    def _handle_category_choice(self, choice: str):
        """Handle a category selection and show tools within it."""
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(self.categories):
                self._show_category_tools(self.categories[idx])
            else:
                print(colorize("\n  Invalid category number.", Colors.RED))
                time.sleep(1)
        except ValueError:
            print(colorize("\n  Invalid input. Please enter a number, 'i', or '0'.", Colors.RED))
            time.sleep(1)

    def _show_category_tools(self, category: ToolCategory):
        """Show all tools in a category and allow launching."""
        while True:
            self._clear_screen()
            self._print_header()
            category.display()

            for i, tool in enumerate(category.tools, 1):
                tool.display(i)

            print()
            print(colorize(f"  [0] Back to main menu", Colors.YELLOW))
            print()

            try:
                choice = input(colorize("  Launch tool [#] > ", Colors.BOLD + Colors.GREEN)).strip()
                if choice == "0":
                    break
                elif choice == "":
                    continue
                idx = int(choice) - 1
                if 0 <= idx < len(category.tools):
                    tool = category.tools[idx]
                    self._launch_tool(tool)
                else:
                    print(colorize(f"\n  Invalid tool number (1-{len(category.tools)}).", Colors.RED))
                    time.sleep(1)
            except ValueError:
                print(colorize("\n  Please enter a valid number.", Colors.RED))
                time.sleep(1)
            except (EOFError, KeyboardInterrupt):
                break

    def _launch_tool(self, tool: Tool):
        """Launch a tool and show feedback."""
        print()
        print(colorize(f"  Launching: {tool.name}...", Colors.YELLOW))
        if tool.run_in_terminal:
            print(colorize("  Opening in a new terminal window...", Colors.DIM))
        success = tool.launch()
        if success:
            print(colorize(f"  {tool.name} launched successfully.", Colors.GREEN))
        else:
            print(colorize(f"  Failed to launch {tool.name}.", Colors.RED))
            print(colorize(f"  Command attempted: {tool.command} {' '.join(tool.args)}", Colors.DIM))
        time.sleep(1)

    def _print_goodbye(self):
        """Print goodbye message."""
        print()
        print(colorize("  Thank you for using ComputerTool!", Colors.BOLD + Colors.CYAN))
        print(colorize("  Goodbye.", Colors.CYAN))
        print()

    def list_all_tools(self):
        """Print all tools and their categories without the interactive menu."""
        print()
        print(colorize("COMPUTERTOOL - All Available Tools", Colors.BOLD + Colors.CYAN))
        print(colorize("=" * 60, Colors.CYAN))
        print()

        for category in self.categories:
            category.display()
            for i, tool in enumerate(category.tools, 1):
                tool.display(i)

        print()
        print(colorize(f"Total: {sum(len(c.tools) for c in self.categories)} tools in {len(self.categories)} categories", Colors.BOLD))
        print()


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def print_banner():
    """Print the startup banner."""
    banner = r"""
   ____                      _              _______          _
  / ___|___  _ __ ___  _ __ | |_ ___ _ __  |_   _\ \___ ___ | |
 | |   / _ \| '_ ` _ \| '_ \| __/ _ \ '__|   | |  \ \ / _ \| |
 | |__| (_) | | | | | | |_) | ||  __/ |      | |  /\ \ (_) | |
  \____\___/|_| |_| |_| .__/ \__\___|_|      |_| /_/ \_\___/|_|
  _____         _     |_|     _____       _   _       _
 |_   _|__  ___| |_   ___   |_   _|__   | | | | ___ | |
   | |/ _ \/ __| __| / _ \    | |/ _ \  | |_| |/ _ \| |
   | |  __/\__ \ |_ | (_) |   | | (_) | |  _  | (_) | |
   |_|\___||___/\__| \___/    |_|\___/  |_| |_|\___/|_|
    """
    print(colorize(banner, Colors.CYAN))
    print(colorize("  Cross-Platform System Tools Launcher v1.0.0", Colors.BOLD + Colors.WHITE))
    print(colorize("  Works on Windows, Linux, and macOS", Colors.DIM))
    print(colorize("  " + "─" * 52, Colors.DIM))
    print()


def main():
    """Main entry point."""
    print_banner()

    # Initialize system scanner
    print(colorize("  Scanning system...", Colors.YELLOW))
    sys_info = SystemInfo()
    time.sleep(0.5)

    # Show system info
    sys_info.display()

    # Check for command line arguments
    if "--list" in sys.argv:
        menu = ToolMenu(sys_info)
        menu.list_all_tools()
        return
    elif "--info" in sys.argv:
        return

    # Start interactive menu
    menu = ToolMenu(sys_info)
    try:
        menu.run()
    except KeyboardInterrupt:
        print()
        print(colorize("\n  Interrupted. Goodbye.", Colors.YELLOW))
        print()


if __name__ == "__main__":
    main()
