import socket
import argparse
import sys
import json
from datetime import datetime
from threading import Thread, Lock
from queue import Queue
from typing import Dict, List, Tuple, Optional
from pathlib import Path

from colorama import Fore, Style, init
from tqdm import tqdm

# Initialize colorama for cross-platform color support
init(autoreset=True)

# Thread-safe lock for console output and results
output_lock = Lock()
results_lock = Lock()


class PortScanner:
    """Professional port scanner with multi-threading support."""
    
    def __init__(self, target: str, timeout: float = 1.0, max_threads: int = 100):
        """
        Initialize the port scanner.
        
        Args:
            target: Target IP address or hostname
            timeout: Socket timeout in seconds
            max_threads: Maximum number of concurrent threads
        """
        self.target = target
        self.timeout = timeout
        self.max_threads = max_threads
        self.open_ports: Dict[int, Dict] = {}
        self.closed_ports: List[int] = []
        self.queue = Queue()
        self.pbar = None
        
    def resolve_hostname(self) -> Optional[str]:
        """
        Resolve hostname to IP address.
        
        Returns:
            Resolved IP address or None if resolution fails
        """
        try:
            resolved_ip = socket.gethostbyname(self.target)
            return resolved_ip
        except socket.gaierror:
            with output_lock:
                print(f"{Fore.RED}[!] Error: Hostname '{self.target}' could not be resolved.{Style.RESET_ALL}")
            return None
    
    def grab_banner(self, host: str, port: int) -> Optional[str]:
        """
        Attempt to grab the service banner from an open port.
        
        Args:
            host: Target IP/hostname
            port: Port number
            
        Returns:
            Banner string or None if unable to grab
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            sock.connect((host, port))
            
            # Try to receive banner (first 1024 bytes)
            banner = sock.recv(1024).decode('utf-8', errors='ignore').strip()
            sock.close()
            
            return banner if banner else None
        except (socket.timeout, socket.error, ConnectionRefusedError):
            return None
    
    def scan_port(self, host: str, port: int) -> None:
        """
        Scan a single port.
        
        Args:
            host: Target IP address
            port: Port number to scan
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((host, port))
            
            if result == 0:
                # Port is open - attempt banner grab
                banner = self.grab_banner(host, port)
                
                with results_lock:
                    self.open_ports[port] = {
                        'status': 'open',
                        'banner': banner if banner else 'N/A',
                        'timestamp': datetime.now().isoformat()
                    }
                
                with output_lock:
                    banner_text = f" | {Fore.CYAN}{banner[:50]}{Style.RESET_ALL}" if banner else ""
                    print(f"{Fore.GREEN}[+] Port {port:5d} is OPEN{banner_text}{Style.RESET_ALL}")
            else:
                with results_lock:
                    self.closed_ports.append(port)
                
                with output_lock:
                    print(f"{Fore.RED}[-] Port {port:5d} is CLOSED{Style.RESET_ALL}")
            
            sock.close()
        except (socket.timeout, socket.error, ConnectionRefusedError) as e:
            with output_lock:
                print(f"{Fore.YELLOW}[?] Port {port:5d} - Error: {str(e)[:30]}{Style.RESET_ALL}")
        except Exception as e:
            with output_lock:
                print(f"{Fore.YELLOW}[?] Port {port:5d} - Unexpected error: {str(e)[:30]}{Style.RESET_ALL}")
    
    def worker(self, host: str) -> None:
        """
        Worker thread that processes ports from the queue.
        
        Args:
            host: Target IP address
        """
        while True:
            port = self.queue.get()
            if port is None:
                break
            
            self.scan_port(host, port)
            self.queue.task_done()
            if self.pbar:
                self.pbar.update(1)
    
    def execute_scan(self, start_port: int, end_port: int) -> Dict:
        """
        Execute the port scan with multi-threading.
        
        Args:
            start_port: Starting port number
            end_port: Ending port number
            
        Returns:
            Dictionary containing scan results
        """
        # Resolve hostname
        resolved_ip = self.resolve_hostname()
        if not resolved_ip:
            return {'error': 'Could not resolve hostname'}
        
        print(f"\n{Fore.CYAN}[*] Scanning {self.target} ({resolved_ip}):{Style.RESET_ALL}")
        print(f"{Fore.CYAN}[*] Port range: {start_port}-{end_port}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}[*] Using {self.max_threads} threads{Style.RESET_ALL}\n")
        
        start_time = datetime.now()
        port_count = end_port - start_port + 1
        
        # Populate queue with ports
        for port in range(start_port, end_port + 1):
            self.queue.put(port)
        
        # Create and start worker threads
        threads = []
        for _ in range(min(self.max_threads, port_count)):
            t = Thread(target=self.worker, args=(resolved_ip,), daemon=True)
            t.start()
            threads.append(t)
        
        # Progress bar
        pbar = tqdm(total=port_count, desc="Scanning", unit="port", bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt}')
        self.pbar = pbar
        
        # Signal threads to stop
        for _ in range(len(threads)):
            self.queue.put(None)
        
        # Wait for all threads to complete
        for t in threads:
            t.join()
        
        pbar.close()
        
        end_time = datetime.now()
        total_time = end_time - start_time
        
        results = {
            'target': self.target,
            'resolved_ip': resolved_ip,
            'start_port': start_port,
            'end_port': end_port,
            'open_ports': self.open_ports,
            'closed_ports': len(self.closed_ports),
            'total_ports_scanned': port_count,
            'scan_duration': str(total_time),
            'timestamp': start_time.isoformat()
        }
        
        return results


def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Professional Port Scanner - Multi-threaded Network Scanning Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python scanner.py -t 192.168.1.1 -p 1-1000
  python scanner.py -t example.com -p 22,80,443,3306
  python scanner.py -t 10.0.0.1 -p 1-65535 -o results.json --threads 200
  python scanner.py -t localhost -p 8000-9000 --timeout 2.0
        '''
    )
    
    parser.add_argument('-t', '--target', type=str, required=True,
                       help='Target IP address or hostname')
    parser.add_argument('-p', '--ports', type=str, required=True,
                       help='Port(s) to scan: 22,80,443 or 1-1000 or 1-65535')
    parser.add_argument('-o', '--output', type=str, default=None,
                       help='Output file for results (JSON format)')
    parser.add_argument('--timeout', type=float, default=1.0,
                       help='Socket timeout in seconds (default: 1.0)')
    parser.add_argument('--threads', type=int, default=100,
                       help='Number of threads to use (default: 100)')
    
    return parser.parse_args()


def parse_ports(port_string: str) -> Tuple[int, int]:
    """
    Parse port argument into start and end port numbers.
    
    Supports:
    - Range: "1-1000"
    - Individual: "22,80,443"
    
    Args:
        port_string: Port specification string
        
    Returns:
        Tuple of (start_port, end_port)
    """
    if '-' in port_string:
        try:
            parts = port_string.split('-')
            start = int(parts[0].strip())
            end = int(parts[1].strip())
            
            if start < 1 or end > 65535:
                raise ValueError('Ports must be between 1 and 65535')
            if start > end:
                raise ValueError('Start port cannot be greater than end port')
            
            return start, end
        except (ValueError, IndexError) as e:
            print(f"{Fore.RED}[!] Error parsing port range: {e}{Style.RESET_ALL}")
            sys.exit(1)
    else:
        print(f"{Fore.YELLOW}[!] Only range format supported (e.g., 1-1000){Style.RESET_ALL}")
        sys.exit(1)


def save_results(results: Dict, output_file: str) -> None:
    """
    Save scan results to a JSON file.
    
    Args:
        results: Dictionary containing scan results
        output_file: Path to output file
    """
    try:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n{Fore.GREEN}[✓] Results saved to: {output_path}{Style.RESET_ALL}")
    except IOError as e:
        print(f"{Fore.RED}[!] Error saving results: {e}{Style.RESET_ALL}")


def print_results_summary(results: Dict) -> None:
    """Print a formatted summary of scan results."""
    if 'error' in results:
        print(f"{Fore.RED}[!] Scan failed: {results['error']}{Style.RESET_ALL}")
        return
    
    print(f"\n{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}[✓] SCAN COMPLETE{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"Target: {results['target']} ({results['resolved_ip']})")
    print(f"Ports scanned: {results['total_ports_scanned']}")
    print(f"{Fore.GREEN}Open ports: {len(results['open_ports'])}{Style.RESET_ALL}")
    print(f"{Fore.RED}Closed ports: {results['closed_ports']}{Style.RESET_ALL}")
    print(f"Scan duration: {results['scan_duration']}")
    
    if results['open_ports']:
        print(f"\n{Fore.CYAN}[*] Open Ports Details:{Style.RESET_ALL}")
        for port, info in sorted(results['open_ports'].items()):
            banner = info.get('banner', 'N/A')
            banner_display = f" | {banner[:50]}" if banner != 'N/A' else ""
            print(f"  {Fore.GREEN}Port {port}{Fore.RESET}{banner_display}")
    
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")


def main() -> None:
    """Main function - orchestrates the scanning process."""
    try:
        args = parse_arguments()
        start_port, end_port = parse_ports(args.ports)
        
        scanner = PortScanner(
            target=args.target,
            timeout=args.timeout,
            max_threads=args.threads
        )
        
        results = scanner.execute_scan(start_port, end_port)
        
        print_results_summary(results)
        
        if args.output:
            save_results(results, args.output)
    
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}[!] Scan interrupted by user.{Style.RESET_ALL}")
        sys.exit(0)
    except Exception as e:
        print(f"{Fore.RED}[!] Unexpected error: {e}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == "__main__":
    main()