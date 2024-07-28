import socket
from threading import Thread
import argparse
from pathlib import Path

RN = b"\r\n"

def parse_request(conn):
    d = {}
    headers = {}
    body = []
    target = 0  # 0: request line, 1: headers, 2: body
    rest = b""
    body_len = 0
    body_count = 0

    while data := conn.recv(1024):
        if rest:
            data = rest + data
            rest = b""
        
        # Handle request line
        if target == 0:
            ind = data.find(RN)
            if ind == -1:
                rest = data
                continue
            
            line = data[:ind].decode()
            data = data[ind + 2 :]
            d["request"] = line
            l = line.split()
            d["method"] = l[0]  # GET, POST
            d["url"] = l[1]
            target = 1  # Move to headers
        
        # Handle headers
        if target == 1:
            if not data:
                continue
            while True:
                ind = data.find(RN)
                if ind == -1:
                    rest = data
                    break
                if ind == 0:  # End of headers section
                    data = data[ind + 2 :]
                    target = 2
                    break
                line = data[:ind].decode()
                data = data[ind + 2 :]
                l = line.split(":", maxsplit=1)
                if len(l) == 2:
                    field = l[0].strip().lower()
                    value = l[1].strip()
                    headers[field] = value
            if target == 1:
                continue
        
        # Handle body
        if target == 2:
            if "content-length" not in headers:
                break
            body_len = int(headers["content-length"])
            if not body_len:
                break
            target = 3
        
        if target == 3:
            body.append(data)
            body_count += len(data)
            if body_count >= body_len:
                break

    d["headers"] = headers
    d["body"] = b"".join(body)
    return d

def req_handler(conn, dir_):
    with conn:
        d = parse_request(conn)
        url = d["url"]
        method = d["method"]
        headers = d["headers"]
        if url == "/":
            conn.sendall(b"HTTP/1.1 200 OK\r\n\r\n")
        elif url.startswith("/echo/"):
            body = url[6:].encode()
            response_headers = [
                b"Content-Type: text/plain",
            ]
            if encoding := headers.get("accept-encoding"):
                if "gzip" in encoding:
                    response_headers.append(b"Content-Encoding: gzip")
            response_headers.append(f"Content-Length: {len(body)}".encode())
            response_headers.append(RN)
            
            conn.sendall(b"HTTP/1.1 200 OK\r\n" + b"\r\n".join(response_headers))
            conn.sendall(body)
        elif url == "/user-agent":
            body = headers.get("user-agent", "").encode()
            conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n")
            conn.sendall(f"Content-Length: {len(body)}".encode() + RN)
            conn.sendall(body)
        elif url.startswith("/files/"):
            file = Path(dir_) / url[7:]
            if method == "GET":
                if file.exists():
                    conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: application/octet-stream\r\n")
                    with open(file, "rb") as fp:
                        body = fp.read()
                    conn.sendall(f"Content-Length: {len(body)}".encode() + RN)
                    conn.sendall(body)
                else:
                    conn.sendall(b"HTTP/1.1 404 Not Found\r\n\r\n")
            elif method == "POST":
                with open(file, "wb") as fp:
                    fp.write(d["body"])
                conn.sendall(b"HTTP/1.1 201 Created\r\n\r\n")
            else:
                conn.sendall(b"HTTP/1.1 404 Not Found\r\n\r\n")
        else:
            conn.sendall(b"HTTP/1.1 404 Not Found\r\n\r\n")

def main():
    parser = argparse.ArgumentParser(description="Socket server")
    parser.add_argument(
        "--directory", default=".", help="Directory from which to get files"
    )
    args = parser.parse_args()
    
    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    while True:
        conn, _ = server_socket.accept()
        Thread(target=req_handler, args=(conn, args.directory)).start()

if __name__ == "__main__":
    main()
