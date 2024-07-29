import gzip
import pathlib
import socket
import sys
import threading
import types
from collections.abc import Generator
from app.entities import Request, Response, ResponseGenerator
from app.utils import read_request
def process(sock: socket.socket) -> None:
    request = read_request(sock)
    if request.target == "/":
        response = Response()  # HTTP/1.1 200 OK\r\n\r\n
    elif request.target.startswith("/echo/"):
        body = request.target[6:].encode()
        response = Response(body=body)
        accept_encodings = (
            request.headers["Accept-Encoding"].split(", ")
            if request.headers.get("Accept-Encoding")
            else []
        )
        if accept_encodings and "gzip" in accept_encodings:
            response.headers["Content-Encoding"] = "gzip"
            response.body = gzip.compress(body)
    elif request.target.startswith("/user-agent"):
        body = (request.headers.get("User-Agent") or "").encode()
        headers = {"Content-Type": "text/plain", "Content-Length": len(body)}
        response = Response(headers=headers, body=body)
    elif request.target.startswith("/files/") and request.method.lower() == "get":
        filepath = pathlib.Path(sys.argv[2]) / request.target[7:]
        response = Response.from_file(filepath)
    elif request.target.startswith("/files/") and request.method.lower() == "post":
        filepath = pathlib.Path(sys.argv[2]) / request.target[7:]
        with open(filepath, "wb") as file:
            file.write(request.body)
        response = Response(status_code=201, status_text="Created")
    else:
        response = Response(
            status_code=404, status_text="Not Found"
        )  #  HTTP/1.1 404 Not Found\r\n\r\n
    if isinstance(response, Response):
        sock.send(response.to_raw())
    elif isinstance(response, types.GeneratorType):
        for data in response:
            sock.send(data)
    sock.close()
def main():
    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    while True:
        sock, addr_info = server_socket.accept()
        threading.Thread(target=process, args=(sock,)).start()
if __name__ == "__main__":
    main()