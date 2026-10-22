import socket
def is_valid_port(port):
    return isinstance(port, int) and 1 <= port <= 65535
def check_port(host, port, timeout=2):
    if not is_valid_port(port):
        raise ValueError("Invalid port")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0
if __name__ == "__main__":
    port = int(input("Enter a local port: "))
    print("Open" if check_port("127.0.0.1", port) else "Closed")
