"""Export FastAPI OpenAPI schema to docs/openapi.json."""
import json
import sys
from pathlib import Path

# Add project root to path
root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))

from traffic_api.main import app

schema = app.openapi()
output_path = root / "docs" / "openapi.json"
output_path.write_text(json.dumps(schema, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"OpenAPI schema exported to {output_path}")
print(f"Paths: {list(schema.get('paths', {}).keys())}")
