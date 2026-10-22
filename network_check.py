import socket

host = "127.0.0.1"
port = int(input("Enter port number: "))

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.settimeout(2)
    result = sock.connect_ex((host, port))

if result == 0:
    print("Port is open")
else:
    print("Port is closed or unreachable")
