from __future__ import annotations

import argparse
from pathlib import Path

import requests


def main() -> None:
    parser = argparse.ArgumentParser(description="Send one image to the traffic-sign detection API.")
    parser.add_argument("image", type=Path, help="Path to an image file.")
    parser.add_argument("--url", default="http://127.0.0.1:8000/api/v1/detect/image")
    parser.add_argument("--api-key", default=None, help="Optional X-API-Key header value.")
    args = parser.parse_args()

    headers = {}
    if args.api_key:
        headers["X-API-Key"] = args.api_key

    with args.image.open("rb") as image_file:
        response = requests.post(
            args.url,
            headers=headers,
            files={"file": (args.image.name, image_file, "application/octet-stream")},
            timeout=120,
        )

    print(response.status_code)
    print(response.text)
    response.raise_for_status()


if __name__ == "__main__":
    main()

