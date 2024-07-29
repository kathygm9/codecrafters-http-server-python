import gzip
import pathlib
import socket
import sys
import threading

def read_request(sock):
    request = sock.recv(4096).decode()
    headers = {}
    lines = request.split("\r\n")
    start_line = lines[0]
    method, target, _ = start_line.split()
    for line in lines[1:]:
        if line:
            key, value = line.split(": ", 1)
            headers[key] = value
    return method, target, headers

class Response:
    def __init__(self, status_code=200, status_text="OK", headers=None, body=b""):
        self.status_code = status_code
        self.status_text = status_text
        self.headers = headers or {}
        self.body = body

    def to_raw(self):
        response_line = f"HTTP/1.1 {self.status_code} {self.status_text}\r\n"
        headers = ''.join(f"{key}: {value}\r\n" for key, value in self.headers.items())
        return (response_line + headers + "\r\n").encode() + self.body

def process(sock):
    method, target, headers = read_request(sock)

    if target == "/":
        response = Response()
    elif target.startswith("/echo/"):
        body = target[6:].encode()
        response = Response(body=body)
        accept_encodings = headers.get("Accept-Encoding", "").split(", ")
        if "gzip" in accept_encodings:
            response.headers["Content-Encoding"] = "gzip"
            response.body = gzip.compress(body)
            response.headers["Content-Length"] = str(len(response.body))
    elif target.startswith("/user-agent"):
        body = (headers.get("User-Agent") or "").encode()
        response = Response(headers={"Content-Type": "text/plain", "Content-Length": str(len(body))}, body=body)
    elif target.startswith("/files/") and method.lower() == "get":
        filepath = pathlib.Path(sys.argv[2]) / target[7:]
        if filepath.exists():
            body = filepath.read_bytes()
            response = Response(headers={"Content-Type": "application/octet-stream", "Content-Length": str(len(body))}, body=body)
        else:
            response = Response(status_code=404, status_text="Not Found")
    elif target.startswith("/files/") and method.lower() == "post":
        filepath = pathlib.Path(sys.argv[2]) / target[7:]
        body = sock.recv(int(headers["Content-Length"]))
        with open(filepath, "wb") as file:
            file.write(body)
        response = Response(status_code=201, status_text="Created")
    else:
        response = Response(status_code=404, status_text="Not Found")

    sock.send(response.to_raw())
    sock.close()

def main():
    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    while True:
        sock, _ = server_socket.accept()
        threading.Thread(target=process, args=(sock,)).start()

if __name__ == "__main__":
    main()
