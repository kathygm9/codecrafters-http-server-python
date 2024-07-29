import socket
import sys
from concurrent.futures import ThreadPoolExecutor
from typing import List
from pathlib import Path

def process_conn(conn):
    with conn:
        init = conn.recv(4096)
        
        def parse_http(bs: bytes):
            lines: List[bytes] = []
            while not bs.startswith(b"\r\n"):
                sp = bs.split(b"\r\n", 1)
                if len(sp) == 2:
                    line, bs = sp
                    lines.append(line)
                else:
                    cont = conn.recv(4096)
                    bs += cont
            return lines, bs[2:]
        
        (start_line, *raw_headers), body_start = parse_http(init)
        headers = {
            parts[0]: parts[1]
            for rh in raw_headers
            if (parts := rh.decode().split(": "))
        }
        
        method, path, _ = start_line.decode().split(" ")
        
        match (method, path, path.split("/")):
            case ("GET", "/", _):
                conn.send(b"HTTP/1.1 200 OK\r\n\r\n")
            case ("GET", _, ["", "echo", data]):
                body = data.encode()
                extra_headers = []
                if "Accept-Encoding" in headers:
                    encodings = headers["Accept-Encoding"].split(", ")
                    if "gzip" in encodings:
                        extra_headers.append(b"Content-Encoding: gzip\r\n")
                conn.send(
                    b"".join(
                        [
                            b"HTTP/1.1 200 OK",
                            b"\r\n",
                            *extra_headers,
                            b"Content-Type: text/plain\r\n",
                            b"Content-Length: %d\r\n" % len(body),
                            b"\r\n",
                            body,
                        ]
                    )
                )
            case ("GET", "/user-agent", _):
                body = headers["User-Agent"].encode()
                conn.send(
                    b"".join(
                        [
                            b"HTTP/1.1 200 OK",
                            b"\r\n",
                            b"Content-Type: text/plain\r\n",
                            b"Content-Length: %d\r\n" % len(body),
                            b"\r\n",
                            body,
                        ]
                    )
                )
            case ("GET", _, ["", "files", f]):
                target = Path(sys.argv[2]) / f
                if target.exists():
                    body = target.read_bytes()
                    conn.send(
                        b"".join(
                            [
                                b"HTTP/1.1 200 OK",
                                b"\r\n",
                                b"Content-Type: application/octet-stream\r\n",
                                b"Content-Length: %d\r\n" % len(body),
                                b"\r\n",
                                body,
                            ]
                        )
                    )
                else:
                    conn.send(b"HTTP/1.1 404 Not Found\r\n\r\n")
            case ("POST", _, ["", "files", f]):
                target = Path(sys.argv[2]) / f
                size = int(headers["Content-Length"])
                remaining = size - len(body_start)
                if remaining > 0:
                    body_rest = conn.recv(remaining, socket.MSG_WAITALL)
                else:
                    body_rest = b""
                body = body_start + body_rest
                target.write_bytes(body)
                conn.send(
                    b"".join(
                        [
                            b"HTTP/1.1 201 Created",
                            b"\r\n",
                            b"\r\n",
                        ]
                    )
                )
            case _:
                conn.send(b"HTTP/1.1 404 Not Found\r\n\r\n")

def process_conn_with_exception(conn):
    try:
        process_conn(conn)
    except Exception as ex:
        print(ex)

def main():
    with socket.create_server(("localhost", 4221), reuse_port=True) as server_socket:
        with ThreadPoolExecutor(max_workers=100) as executor:
            while True:
                (conn, _) = server_socket.accept()
                executor.submit(process_conn_with_exception, conn)

if __name__ == "__main__":
    main()
