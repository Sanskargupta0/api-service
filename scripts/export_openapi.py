"""Export the customer-facing OpenAPI specification.

The service's full OpenAPI document (from FastAPI) contains every endpoint,
including internal ones. This script filters it down to the customer-facing
subset and writes it to openapi/customer-openapi.json, which GitHub Actions
synchronizes into the documentation repository.

Usage:
    python scripts/export_openapi.py [--output openapi/customer-openapi.json]

How customer-facing endpoints are selected
------------------------------------------
CUSTOMER_API_PATHS below is an explicit allow-list. An endpoint appears in
the customer documentation if and only if its path is listed here AND it
exists in the service's OpenAPI document. Internal endpoints such as
/internal/health and /internal/admin/users are simply never listed.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app  # noqa: E402

# ---------------------------------------------------------------------------
# Customer API selection: the single source of truth for what is published.
# Add a path here to expose it in the customer documentation portal.
# ---------------------------------------------------------------------------
CUSTOMER_API_PATHS = {
    "/api/v1/users",
    "/api/v1/users/{user_id}",
    "/api/v1/users/{user_id}/tasks",
    "/api/v1/tasks",
}

# Customer-facing branding for the published spec (overrides service defaults).
CUSTOMER_INFO = {
    "title": "PioAgent Customer API",
    "description": (
        "Customer-facing API for PioAgent. This specification is generated "
        "from the PioAgent service and synchronized into this repository by "
        "GitHub Actions — do not edit it by hand."
    ),
    "contact": {"name": "PioAgent Support", "email": "support@piovation.com"},
}

CUSTOMER_SERVERS = [
    {"url": "https://api.pioagent.app", "description": "Production"}
]


def export_customer_openapi() -> dict:
    """Return the full service OpenAPI spec filtered to customer endpoints."""
    spec = app.openapi()

    missing = [p for p in CUSTOMER_API_PATHS if p not in spec["paths"]]
    if missing:
        raise SystemExit(
            f"Error: allow-listed paths not found in service OpenAPI: {missing}. "
            "Update CUSTOMER_API_PATHS in scripts/export_openapi.py."
        )

    filtered_paths = {
        path: methods
        for path, methods in spec["paths"].items()
        if path in CUSTOMER_API_PATHS
    }

    # Keep only schemas actually referenced by the filtered paths, so internal
    # response models do not leak into the customer spec either.
    referenced: set[str] = set()

    def collect_refs(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "$ref" and isinstance(value, str):
                    referenced.add(value.split("/")[-1])
                collect_refs(value)
        elif isinstance(node, list):
            for item in node:
                collect_refs(item)

    collect_refs(filtered_paths)

    filtered_schemas = {
        name: schema
        for name, schema in spec.get("components", {}).get("schemas", {}).items()
        if name in referenced or name in ("Error", "ValidationError")
    }

    # Attach API-key authentication to every published operation.
    for methods in filtered_paths.values():
        for operation in methods.values():
            if isinstance(operation, dict):
                operation["security"] = [{"bearerAuth": []}]

    return {
        "openapi": spec["openapi"],
        "info": {**spec["info"], **CUSTOMER_INFO},
        "servers": CUSTOMER_SERVERS,
        "tags": [
            tag
            for tag in spec.get("tags", [])
            if tag["name"] not in ("Internal",)
        ],
        "paths": filtered_paths,
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "description": (
                        "API key sent as a bearer token in the Authorization header."
                    ),
                }
            },
            "schemas": filtered_schemas,
        }
        if filtered_schemas
        else {},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="openapi/customer-openapi.json",
        help="Output file path (default: openapi/customer-openapi.json)",
    )
    args = parser.parse_args()

    spec = export_customer_openapi()

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")

    published = sorted(spec["paths"])
    print(f"[ok] Customer OpenAPI written to {output}")
    print(f"  Published endpoints ({len(published)}):")
    for path in published:
        print(f"    {path}")
    internal = sorted(set(app.openapi()["paths"]) - set(spec["paths"]))
    print(f"  Excluded internal endpoints ({len(internal)}):")
    for path in internal:
        print(f"    {path}")


if __name__ == "__main__":
    main()
