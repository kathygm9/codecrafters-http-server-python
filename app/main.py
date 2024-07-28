import asyncio
import argparse
import re
import sys
from asyncio.streams import StreamReader, StreamWriter
from pathlib import Path

GLOBALS = {}

def stderr(*args, **kwargs):
    print(*args, **kwargs, file=sys.stderr)

def parse_request(content: bytes) -> tuple[str, str, dict[str, str], str]:
    first_line, *tail = content.split(b"\r\n")
    method, path, _ = first_line.split(b" ")
    headers: dict[str, str] = {}
    while (line := tail.pop(0)) != b"":
        key, value = line.split(b": ")
        headers[key.decode()] = value.decode()
    return method.decode(), path.decode(), headers, b"".join(tail).decode()

def make_response(
    status: int,
    headers: dict[str, str] | None = None,
    body: str = "",
) -> bytes:
    headers = headers or {}
    msg = {
        200: "OK",
        201: "Created",
        404: "Not Found",
    }
    return b"\r\n".join(
        map(
            lambda i: i.encode(),
            [
                f"HTTP/1.1 {status} {msg[status]}",
                *[f"{k}: {v}" for k, v in headers.items()],
                f"Content-Length: {len(body)}",
                "",
                body,
            ],
        ),
    )

async def handle_connection(reader: StreamReader, writer: StreamWriter) -> None:
    method, path, headers, body = parse_request(await reader.read(2**16))

    # Determine if gzip encoding is requested and supported
    accept_encoding = headers.get("Accept-Encoding", "")
    supports_gzip = "gzip" in accept_encoding

    response_headers = {}

    if re.fullmatch(r"/", path):
        writer.write(make_response(200, response_headers))
        stderr(f"[OUT] /")
    elif re.fullmatch(r"/user-agent", path):
        ua = headers.get("User-Agent", "")
        writer.write(make_response(200, {"Content-Type": "text/plain"}, ua))
        stderr(f"[OUT] user-agent {ua}")
    elif match := re.fullmatch(r"/echo/(.+)", path):
        msg = match.group(1)
        if supports_gzip:
            response_headers["Content-Encoding"] = "gzip"
        writer.write(make_response(200, response_headers, msg))
        stderr(f"[OUT] echo {msg}")
    elif match := re.fullmatch(r"/files/(.+)", path):
        p = Path(GLOBALS["DIR"]) / match.group(1)
        if method.upper() == "GET" and p.is_file():
            writer.write(
                make_response(
                    200,
                    {"Content-Type": "application/octet-stream"},
                    p.read_text(),
                )
            )
        elif method.upper() == "POST":
            p.write_bytes(body.encode())
            writer.write(make_response(201))  # Returns 201 Created
        else:
            writer.write(make_response(404))
        stderr(f"[OUT] file {path}")
    else:
        writer.write(make_response(404, {}, ""))
        stderr(f"[OUT] 404")
    writer.close()

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", default=".")
    args = parser.parse_args()
    GLOBALS["DIR"] = args.directory
    server = await asyncio.start_server(handle_connection, "localhost", 4221)
    async with server:
        stderr("Starting server...")
        stderr(f"--directory {GLOBALS['DIR']}")
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
