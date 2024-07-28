import socket

def main():
    # Create a TCP/IP socket
    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    print("Server is listening on port 4221")

    while True:
        client, _ = server_socket.accept()
        try:
            # Receive the HTTP request
            data = client.recv(1024).decode()
            print(f"Received request:\n{data}")

            # Split the request into lines
            request_lines = data.split("\r\n")
            request_line = request_lines[0] if request_lines else ""
            
            # Extract the method and path from the request line
            if request_line:
                method, path, _ = request_line.split(" ", 2)

                # Extract headers into a dictionary
                headers = {}
                for line in request_lines[1:]:
                    if ": " in line:
                        key, value = line.split(": ", 1)
                        headers[key] = value

                if method == "GET":
                    if path == "/":
                        # Handle root path
                        response = "HTTP/1.1 200 OK\r\n\r\n".encode()
                    elif path.startswith("/echo/"):
                        # Handle /echo/{str}
                        echo_text = path[len("/echo/"):]
                        response_body = echo_text
                        response = (
                            f"HTTP/1.1 200 OK\r\n"
                            f"Content-Type: text/plain\r\n"
                            f"Content-Length: {len(response_body)}\r\n"
                            "\r\n"
                            f"{response_body}"
                        ).encode()
                    elif path == "/user-agent":
                        # Handle /user-agent
                        user_agent = headers.get("User-Agent", "")
                        response_body = user_agent
                        response = (
                            f"HTTP/1.1 200 OK\r\n"
                            f"Content-Type: text/plain\r\n"
                            f"Content-Length: {len(response_body)}\r\n"
                            "\r\n"
                            f"{response_body}"
                        ).encode()
                    else:
                        response = "HTTP/1.1 404 Not Found\r\n\r\n".encode()
                else:
                    response = "HTTP/1.1 405 Method Not Allowed\r\n\r\n".encode()
            else:
                response = "HTTP/1.1 400 Bad Request\r\n\r\n".encode()

            # Send the HTTP response
            client.send(response)
        finally:
            client.close()

if __name__ == "__main__":
    main()
