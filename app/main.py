import socket

def main():
    # Create a TCP/IP socket
    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    print("Server is listening on port 4221")

    while True:
        connection, _ = server_socket.accept()
        try:
            # Receive the HTTP request
            request = connection.recv(1024).decode()
            print(f"Received request:\n{request}")

            # Extract the request line (first line of the request)
            request_line = request.split('\r\n')[0]
            print(f"Request line: {request_line}")

            # Parse the request line
            method, path, _ = request_line.split(' ', 2)

            # Determine the response based on the path
            if path == '/':
                response = b"HTTP/1.1 200 OK\r\n\r\n"
            else:
                response = b"HTTP/1.1 404 Not Found\r\n\r\n"

            # Send the HTTP response
            connection.sendall(response)
        finally:
            connection.close()

if __name__ == "__main__":
    main()
