import socket
from datetime import datetime

def scan_ports(target, start_port, end_port):
    print(f"Scanning {target} from port {start_port} to {end_port}")
    start_time = datetime.now()

    for port in range(start_port, end_port + 1):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(0.5)
            result = sock.connect_ex((target, port))
            if result == 0:
                print(f"[+] Port {port} is open")
            else:
                print(f"[-] Port {port} is closed")
            sock.close()

        except KeyboardInterrupt:
            print("\n[!] Exiting the scanner.")
            return
        except socket.gaierror:
            print("[!] Hostname could not be resolved.")
            return
        except socket.error:
            print("[!] Couldn't connect to server.")
            return

    end_time = datetime.now()
    total_time = end_time - start_time
    print(f"\n[✓] Scanning completed in: {total_time}")

if __name__ == "__main__":
    target = input("Enter the target IP address or hostname: ")
    start_port = int(input("Enter the starting port number: "))
    end_port = int(input("Enter the ending port number: "))
    scan_ports(target, start_port, end_port)