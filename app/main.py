import socket
import threading
import sys

def handle_req(client, addr, directory):
    try:
        data = client.recv(4096).decode()
        req_lines = data.split("\r\n")

        # Request line
        request_line = req_lines[0]
        method, path, _ = request_line.split(" ")

        # Parse headers
        headers = {}
        i = 1
        while req_lines[i]:
            header_line = req_lines[i]
            key, value = header_line.split(": ", 1)
            headers[key] = value
            i += 1

        # Determine response
        response = b"HTTP/1.1 404 Not Found\r\n\r\n"
        if method == "GET":
            if path == "/":
                response = b"HTTP/1.1 200 OK\r\n\r\n"
            elif path.startswith("/echo"):
                content = path[6:]
                response = f"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: {len(content)}\r\n\r\n{content}".encode()
            elif path.startswith("/user-agent"):
                user_agent = headers.get("User-Agent", "Unknown")
                response = f"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: {len(user_agent)}\r\n\r\n{user_agent}".encode()
            elif path.startswith("/files"):
                filename = path[7:]
                try:
                    with open(f"{directory}/{filename}", "r") as f:
                        body = f.read()
                    response = f"HTTP/1.1 200 OK\r\nContent-Type: application/octet-stream\r\nContent-Length: {len(body)}\r\n\r\n{body}".encode()
                except FileNotFoundError:
                    response = b"HTTP/1.1 404 Not Found\r\n\r\n"
        elif method == "POST" and path.startswith("/files"):
            filename = path[7:]
            content_length = int(headers.get("Content-Length", 0))
            body = data.split("\r\n\r\n", 1)[1][:content_length]
            try:
                with open(f"{directory}/{filename}", "w") as f:
                    f.write(body)
                response = b"HTTP/1.1 201 Created\r\n\r\n"
            except Exception as e:
                response = b"HTTP/1.1 500 Internal Server Error\r\n\r\n"
        else:
            response = b"HTTP/1.1 404 Not Found\r\n\r\n"

        client.send(response)
    finally:
        client.close()

def main():
    if len(sys.argv) != 3 or sys.argv[1] != "--directory":
        print("Usage: python main.py --directory <path>")
        sys.exit(1)

    directory = sys.argv[2]
    if not directory:
        print("Directory path is required.")
        sys.exit(1)

    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    print("Server is listening on port 4221")

    while True:
        client, addr = server_socket.accept()
        threading.Thread(target=handle_req, args=(client, addr, directory)).start()

if __name__ == "__main__":
    main()
