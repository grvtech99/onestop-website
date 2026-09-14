import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERIFICATION = ROOT / "data" / "official-verification-state.json"
OUT = ROOT / "data" / "publication-queue.json"


def main():
    verification = json.loads(VERIFICATION.read_text(encoding="utf-8"))
    queue = []
    blocked = 0
    for item_id, item in verification.get("items", {}).items():
        if item.get("status") == "verified" and item.get("publicationStatus") == "ready":
            queue.append({"id": item_id, "status": "ready", "publicationStatus": "ready", "source": item.get("officialSource")})
        else:
            blocked += 1
    result = {
        "schemaVersion": 1,
        "generatedAt": verification.get("checkedAt"),
        "policy": "verified-only",
        "readyCount": len(queue),
        "blockedCount": blocked,
        "items": queue,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PASS", "readyCount": len(queue), "blockedCount": blocked}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
