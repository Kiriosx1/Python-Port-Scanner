📝 Repository Update Summary
Update Version: v2.0.0 (The "Performance" Update)

This update transforms the script from a basic sequential scanner into a high-performance, multi-threaded networking tool.

Key Improvements:
Concurrency & Speed: Migrated from synchronous socket connections to Multi-threading. The scanner now handles multiple ports simultaneously, reducing scan times by over 90%.

Professional CLI Interface: Integrated the argparse library. Users can now pass targets, port ranges, and timeout settings directly via the command line (e.g., -t 192.168.1.1 -p 1-1000).

Banner Grabbing: Added a feature to attempt service identification. If a port is open, the tool tries to capture the service banner to identify the running software (e.g., SSH, Apache, Nginx).

Enhanced Error Handling: Implemented robust try/except blocks for socket timeouts and OS errors, ensuring the scanner doesn't crash on unstable networks.

Visual Feedback: Added color-coded output (Green for OPEN, Red for CLOSED) using colorama for better readability during fast scans.

Compilation Ready: The code structure is now optimized for PyInstaller, allowing it to be compiled into a single-file executable for Windows or Linux without requiring a Python installation.

---


# ⚠️ Legal Disclaimer
## This tool is intended for educational purposes only.
## Do not scan IPs or systems you do not own or do not have permission to test.
## Unauthorized scanning may be illegal and unethical.

# Use responsibly and within the boundaries of the law.

---








