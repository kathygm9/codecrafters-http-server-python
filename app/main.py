import socket
from threading import Thread
import argparse
from pathlib import Path

RN = b"\r\n"

def parse_request(conn):
    d = {}
    headers = {}
    body = []
    target = 0  # request
    rest = b""
    ind = 0
    body_len = 0
    body_count = 0

    while data := conn.recv(1024):
        if rest:
            data = rest + data
            rest = b""
        if target == 0:
            ind = data.find(RN)
            if ind == -1:
                rest = data
                continue
            # GET URL HTTP
            line = data[:ind].decode()
            data = data[ind + 2:]
            d["request"] = line
            l = line.split()
            d["method"] = l[0]  # GET, POST
            d["url"] = l[1]
            target = 1  # headers
        if target == 1:
            if not data:
                continue
            while True:
                ind = data.find(RN)
                if ind == -1:
                    rest = data
                    break
                if ind == 0:  # \r\n\r\n
                    data = data[ind + 2:]
                    target = 2
                    break
                line = data[:ind].decode()
                data = data[ind + 2:]
                l = line.split(":", maxsplit=1)
                field = l[0].lower()
                value = l[1].strip()
                headers[field] = value
            if target == 1:
                continue
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
            response_headers.append(b"")  # End of headers section
            
            # Send response
            conn.sendall(b"HTTP/1.1 200 OK\r\n" + b"\r\n".join(response_headers))
            conn.sendall(body)
        elif url == "/user-agent":
            body = headers.get("user-agent", "").encode()
            response_headers = [
                b"Content-Type: text/plain",
                f"Content-Length: {len(body)}".encode(),
            ]
            response_headers.append(b"")  # End of headers section
            
            # Send response
            conn.sendall(b"HTTP/1.1 200 OK\r\n" + b"\r\n".join(response_headers))
            conn.sendall(body)
        elif url.startswith("/files/"):
            file = Path(dir_) / url[7:]
            if method == "GET":
                if file.exists():
                    with open(file, "rb") as fp:
                        body = fp.read()
                    response_headers = [
                        b"HTTP/1.1 200 OK",
                        b"Content-Type: application/octet-stream",
                        f"Content-Length: {len(body)}".encode(),
                    ]
                    response_headers.append(b"")  # End of headers section
                    
                    # Send response
                    conn.sendall(b"\r\n".join(response_headers))
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
    parser = argparse.ArgumentParser(description="socket server")
    parser.add_argument(
        "--directory", default=".", help="directory from which to get files"
    )
    args = parser.parse_args()  # args.directory
    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    while True:
        conn, _ = server_socket.accept()  # wait for client
        Thread(target=req_handler, args=(conn, args.directory)).start()

if __name__ == "__main__":
    main()
