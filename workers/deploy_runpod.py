"""Create (or reuse) the two RunPod serverless endpoints from the GHCR images.

    RUNPOD_API_KEY=rpa_... python workers/deploy_runpod.py [--image-tag latest] [--gpu "AMPERE_16,AMPERE_24"]

Prints the DOCPARSE_RUNPOD_* lines to paste into .env. Uses RunPod's GraphQL API with plain httpx.
Idempotent on names: an existing template/endpoint called docparse-easyocr / docparse-tfid is reused.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

import httpx

API = "https://api.runpod.io/graphql"
WORKERS = {
    "easyocr": {"disk_gb": 15},
    "tfid": {"disk_gb": 20},
}


def gql(key: str, query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    r = httpx.post(API, params={"api_key": key}, json={"query": query, "variables": variables or {}}, timeout=60)
    r.raise_for_status()
    body = r.json()
    if body.get("errors"):
        raise SystemExit(f"runpod error: {body['errors']}")
    return body["data"]


def existing(key: str) -> tuple[dict[str, str], dict[str, str]]:
    data = gql(key, "{ myself { podTemplates { id name } endpoints { id name } } }")["myself"]
    return ({t["name"]: t["id"] for t in data["podTemplates"]}, {e["name"]: e["id"] for e in data["endpoints"]})


def ensure_template(key: str, name: str, image: str, disk_gb: int, templates: dict[str, str]) -> str:
    if name in templates:
        return templates[name]
    q = """mutation($in: SaveTemplateInput) { saveTemplate(input: $in) { id } }"""
    out = gql(key, q, {"in": {
        "name": name, "imageName": image, "isServerless": True, "containerDiskInGb": disk_gb,
        "volumeInGb": 0, "dockerArgs": "", "env": [], "ports": "", "readme": "docparse worker",
    }})
    return str(out["saveTemplate"]["id"])


def ensure_endpoint(key: str, name: str, template_id: str, gpus: str, endpoints: dict[str, str]) -> str:
    if name in endpoints:
        return endpoints[name]
    q = """mutation($in: EndpointInput) { saveEndpoint(input: $in) { id } }"""
    out = gql(key, q, {"in": {
        "name": name, "templateId": template_id, "gpuIds": gpus, "workersMin": 0, "workersMax": 2,
        "idleTimeout": 5, "scalerType": "QUEUE_DELAY", "scalerValue": 4, "locations": "",
    }})
    return str(out["saveEndpoint"]["id"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image-tag", default="latest")
    ap.add_argument("--gpu", default="AMPERE_16,AMPERE_24,ADA_24")
    ap.add_argument("--registry", default="ghcr.io/yassine-64")
    args = ap.parse_args()
    key = os.environ.get("RUNPOD_API_KEY") or os.environ.get("DOCPARSE_RUNPOD_API_KEY")
    if not key:
        sys.exit("set RUNPOD_API_KEY (or DOCPARSE_RUNPOD_API_KEY)")

    templates, endpoints = existing(key)
    ids = {}
    for worker, cfg in WORKERS.items():
        name = f"docparse-{worker}"
        tpl = ensure_template(key, name, f"{args.registry}/docparse-{worker}:{args.image_tag}", cfg["disk_gb"], templates)
        ids[worker] = ensure_endpoint(key, name, tpl, args.gpu, endpoints)
        print(f"{name}: endpoint {ids[worker]}", file=sys.stderr)

    print(f"DOCPARSE_RUNPOD_API_KEY={key[:6]}…   # keep your real key here")
    print(f"DOCPARSE_RUNPOD_OCR_ENDPOINT={ids['easyocr']}")
    print(f"DOCPARSE_RUNPOD_LAYOUT_ENDPOINT={ids['tfid']}")


if __name__ == "__main__":
    main()
