"""Google Sheets를 HRM 백엔드로 사용하는 데이터 계층."""
from __future__ import annotations
import datetime as dt
from zoneinfo import ZoneInfo

import gspread
from google.oauth2.service_account import Credentials

import config

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

# status: open / in_progress / pending_review / done / missed
TABS = {
    "Tasks": ["task_id", "group_title", "group_id", "assigner", "assignee",
              "description", "created_at", "due_at", "status", "acknowledged_at",
              "completed_at", "confidence", "source_msg_id"],
    "Members": ["user_id", "username", "display_name", "team", "active"],
    "Groups": ["name", "invite_url", "chat_id", "bot_token", "active", "added_at"],
    "Activity": ["date", "week", "user_id", "username", "messages"],
    "Votes": ["created_at", "week", "voter_id", "votee_username"],
    "Points": ["week", "user_id", "username", "assigned", "completed",
               "completion_pct", "ontime_pct", "votes", "messages",
               "response_min", "base_score", "response_bonus",
               "score", "weekly_points", "awarded_at"],
    "Quarter": ["quarter", "user_id", "username", "total_points",
                "avg_score", "rank", "incentive"],
    "Config": ["key", "value"],
}


def _tz() -> ZoneInfo:
    return ZoneInfo(config.TIMEZONE)


def now() -> dt.datetime:
    return dt.datetime.now(_tz())


def _iso_week(d: dt.date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


class HRM:
    def __init__(self):
        creds = Credentials.from_service_account_file(
            config.GOOGLE_SA_KEYFILE, scopes=SCOPES)
        self.gc = gspread.authorize(creds)
        self.sh = self.gc.open_by_key(config.HRM_SHEET_ID)
        self.ensure_schema()

    # --- 스키마 ---
    def ensure_schema(self):
        existing = {ws.title for ws in self.sh.worksheets()}
        for tab, header in TABS.items():
            if tab not in existing:
                ws = self.sh.add_worksheet(title=tab, rows=2000, cols=len(header))
                ws.append_row(header)
            else:
                ws = self.sh.worksheet(tab)
                if ws.row_values(1) != header:
                    ws.update([header], "A1")

    def ws(self, tab: str):
        return self.sh.worksheet(tab)

    # --- Tasks ---
    def new_task_id(self) -> str:
        today = now().strftime("%Y%m%d")
        rows = self.ws("Tasks").get_all_records()
        seq = sum(1 for r in rows if str(r.get("task_id", "")).startswith(f"T-{today}")) + 1
        return f"T-{today}-{seq:03d}"

    def add_task(self, *, group_title, group_id, assigner, assignee,
                 description, due_at, source_msg_id) -> str:
        tid = self.new_task_id()
        self.ws("Tasks").append_row([
            tid, group_title, str(group_id), assigner, assignee, description,
            now().isoformat(timespec="seconds"), due_at.isoformat(timespec="seconds"),
            "open", "", "", "", str(source_msg_id),
        ])
        return tid

    def open_tasks_for_group(self, group_id) -> list[dict]:
        rows = self.ws("Tasks").get_all_records()
        return [r for r in rows
                if str(r.get("group_id")) == str(group_id)
                and r.get("status") in ("open", "in_progress")]

    def get_task(self, task_id) -> dict | None:
        for r in self.ws("Tasks").get_all_records():
            if r.get("task_id") == task_id:
                return r
        return None

    def pending_reviews(self) -> list[dict]:
        return [r for r in self.ws("Tasks").get_all_records()
                if r.get("status") == "pending_review"]

    def _find_row(self, task_id) -> int | None:
        col = self.ws("Tasks").col_values(1)
        for i, v in enumerate(col, start=1):
            if v == task_id:
                return i
        return None

    def _set(self, task_id, field, value) -> bool:
        r = self._find_row(task_id)
        if not r:
            return False
        self.ws("Tasks").update_cell(r, TABS["Tasks"].index(field) + 1, value)
        return True

    def set_status(self, task_id, status):
        return self._set(task_id, "status", status)

    def ack_task(self, task_id) -> bool:
        """담당자의 첫 응답 시각 기록(비어있을 때만). 응답속도 측정용."""
        t = self.get_task(task_id)
        if not t or t.get("acknowledged_at"):
            return False
        return self._set(task_id, "acknowledged_at",
                         now().isoformat(timespec="seconds"))

    def mark_in_progress(self, task_id):
        self.ack_task(task_id)
        self._set(task_id, "status", "in_progress")

    def mark_done(self, task_id, confidence=1.0):
        """확정 완료 (자동승인 임계 이상, /done, 또는 admin 승인)."""
        if not self._set(task_id, "status", "done"):
            return False
        self._set(task_id, "completed_at", now().isoformat(timespec="seconds"))
        self._set(task_id, "confidence", round(float(confidence), 2))
        return True

    def mark_pending_review(self, task_id, confidence):
        """완료로 추정되나 admin 승인 대기. completed_at은 잠정 기록(시간준수 판정용)."""
        if not self._set(task_id, "status", "pending_review"):
            return False
        self._set(task_id, "completed_at", now().isoformat(timespec="seconds"))
        self._set(task_id, "confidence", round(float(confidence), 2))
        return True

    def approve_task(self, task_id):
        """admin 승인 → done (잠정 completed_at 유지)."""
        t = self.get_task(task_id)
        if not t or t.get("status") != "pending_review":
            return False
        return self._set(task_id, "status", "done")

    def reject_task(self, task_id):
        """admin 반려 → in_progress 복귀, completed_at 제거."""
        t = self.get_task(task_id)
        if not t or t.get("status") != "pending_review":
            return False
        self._set(task_id, "completed_at", "")
        self._set(task_id, "confidence", "")
        return self._set(task_id, "status", "in_progress")

    def sweep_overdue(self):
        ws = self.ws("Tasks")
        rows = ws.get_all_records()
        n = now()
        for i, r in enumerate(rows, start=2):
            if r.get("status") in ("open", "in_progress"):
                try:
                    due = dt.datetime.fromisoformat(r["due_at"])
                except Exception:
                    continue
                if due < n:
                    ws.update_cell(i, TABS["Tasks"].index("status") + 1, "missed")

    def all_tasks(self) -> list[dict]:
        return self.ws("Tasks").get_all_records()

    # --- Members ---
    def upsert_member(self, user_id, username, display_name, team="", active=True):
        ws = self.ws("Members")
        ids = ws.col_values(1)
        if str(user_id) in ids:
            return
        ws.append_row([str(user_id), username or "", display_name or "",
                       team, "TRUE" if active else "FALSE"])

    def list_members(self) -> list[dict]:
        return self.ws("Members").get_all_records()

    # --- Groups (채팅방 등록) ---
    def register_group(self, name, invite_url="", chat_id="", bot_token=""):
        """이름 기준 upsert. chat_id가 있으면 빈 행에 채워 넣음."""
        ws = self.ws("Groups")
        rows = ws.get_all_records()
        for i, r in enumerate(rows, start=2):
            if (chat_id and str(r.get("chat_id")) == str(chat_id)) or \
               (name and r.get("name") == name):
                if chat_id and not r.get("chat_id"):
                    ws.update_cell(i, 3, str(chat_id))
                if invite_url and not r.get("invite_url"):
                    ws.update_cell(i, 2, invite_url)
                return r.get("name", name)
        ws.append_row([name, invite_url, str(chat_id), bot_token, "TRUE",
                       now().isoformat(timespec="seconds")])
        return name

    def touch_group(self, chat_id, title):
        """봇이 실제로 본 그룹의 chat_id를 자동 등록(중복 방지는 호출측)."""
        ws = self.ws("Groups")
        ids = [str(x) for x in ws.col_values(3)]
        if str(chat_id) in ids:
            return
        self.register_group(name=title or f"chat:{chat_id}", chat_id=chat_id)

    def list_groups(self) -> list[dict]:
        return self.ws("Groups").get_all_records()

    # --- Activity (대화수) : 일 단위 델타를 append, 주차로 합산 ---
    def flush_activity(self, counts: dict):
        """counts: {(user_id, username): n} 일일 누적분을 시트에 기록."""
        if not counts:
            return
        ws = self.ws("Activity")
        d = now().date()
        rows = [[d.isoformat(), _iso_week(d), str(uid), uname, n]
                for (uid, uname), n in counts.items() if n > 0]
        if rows:
            ws.append_rows(rows)

    def all_activity(self) -> list[dict]:
        return self.ws("Activity").get_all_records()

    # --- Votes (커뮤니케이션 투표) ---
    def add_vote(self, voter_id, votee_username) -> None:
        d = now()
        self.ws("Votes").append_row([
            d.isoformat(timespec="seconds"), _iso_week(d.date()),
            str(voter_id), votee_username.lstrip("@")])

    def all_votes(self) -> list[dict]:
        return self.ws("Votes").get_all_records()

    # --- Points / Quarter ---
    def write_points(self, week, rows: list[dict]):
        ws = self.ws("Points")
        ts = now().isoformat(timespec="seconds")
        for r in rows:
            ws.append_row([week, str(r["user_id"]), r["username"], r["assigned"],
                           r["completed"], r["completion_pct"], r["ontime_pct"],
                           r["votes"], r["messages"], r["response_min"],
                           r["base_score"], r["response_bonus"], r["score"],
                           r["weekly_points"], ts])

    def all_points(self) -> list[dict]:
        return self.ws("Points").get_all_records()

    def write_quarter(self, quarter, rows: list[dict]):
        ws = self.ws("Quarter")
        for r in rows:
            ws.append_row([quarter, str(r["user_id"]), r["username"],
                           r["total_points"], r["avg_score"], r["rank"],
                           r.get("incentive", "")])
