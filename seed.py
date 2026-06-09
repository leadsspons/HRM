"""admin.html에서 내보낸 seed.json을 Google Sheet(Groups·Members)에 일괄 등록.

사용법:
    python seed.py            # 같은 폴더의 seed.json 사용
    python seed.py path.json
"""
import json
import sys

from hrm import HRM


def main(path="seed.json"):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    hrm = HRM()

    groups = data.get("groups", [])
    members = data.get("members", [])

    for g in groups:
        hrm.register_group(name=g.get("name", ""),
                           invite_url=g.get("invite_url", ""),
                           bot_token=g.get("bot_token", ""))
    for m in members:
        hrm.upsert_member(user_id=m.get("username", ""),
                          username=m.get("username", ""),
                          display_name=m.get("display_name", ""),
                          team=m.get("team", ""))

    print(f"✅ 등록 완료 — 채팅방 {len(groups)} · 임직원 {len(members)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "seed.json")
