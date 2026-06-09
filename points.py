"""주간 가중 점수 + 답변회신속도 가산점 + 분기 누적 엔진.

base_score = (Wc·완료율 + Wo·준수율 + Wv·투표 + Wa·대화수) / ΣW     (0~100)
response_bonus = 빠른 첫 응답에 대한 가산점 (0 ~ RESPONSE_BONUS_MAX)
score = base_score + response_bonus
순수 함수라 시트 없이 단독 테스트 가능.
"""
from __future__ import annotations
import datetime as dt
from collections import defaultdict

import config


def iso_week(d: dt.date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def quarter_of(d: dt.date) -> str:
    return f"{d.year}-Q{(d.month - 1)//3 + 1}"


def week_to_quarter_from_isoweek(wk: str) -> str:
    try:
        y, w = wk.split("-W")
        return quarter_of(dt.date.fromisocalendar(int(y), int(w), 1))
    except Exception:
        return ""


def _norm(value, maximum):
    return round(100 * value / maximum, 1) if maximum else 0.0


def response_bonus(avg_min):
    """평균 응답(분) → 가산점. FAST 이내 만점, SLOW 이상 0, 사이 선형."""
    if avg_min is None:
        return 0.0
    fast, slow, cap = (config.RESPONSE_FAST_MIN, config.RESPONSE_SLOW_MIN,
                       config.RESPONSE_BONUS_MAX)
    if avg_min <= fast:
        frac = 1.0
    elif avg_min >= slow:
        frac = 0.0
    else:
        frac = (slow - avg_min) / (slow - fast)
    return round(cap * frac, 1)


def compute_weekly(tasks, activity, votes, week, weights=None) -> list[dict]:
    W = weights or config.WEIGHTS
    wsum = sum(W.values()) or 1

    assigned = defaultdict(int)
    done = defaultdict(int)
    ontime = defaultdict(int)
    resp_sum = defaultdict(float)   # 응답 지연 합(분)
    resp_cnt = defaultdict(int)

    for t in tasks:
        try:
            created = dt.datetime.fromisoformat(str(t.get("created_at")))
        except Exception:
            continue
        if iso_week(created.date()) != week:
            continue
        u = (t.get("assignee") or "unknown").lstrip("@")
        assigned[u] += 1

        # 답변회신속도: 배정 → 첫 응답(acknowledged_at)
        ack = t.get("acknowledged_at")
        if ack:
            try:
                latency = (dt.datetime.fromisoformat(str(ack)) - created).total_seconds() / 60
                if latency >= 0:
                    resp_sum[u] += latency
                    resp_cnt[u] += 1
            except Exception:
                pass

        if t.get("status") == "done":
            done[u] += 1
            try:
                ca = dt.datetime.fromisoformat(str(t.get("completed_at")))
                due = dt.datetime.fromisoformat(str(t.get("due_at")))
                if ca <= due:
                    ontime[u] += 1
            except Exception:
                pass

    msgs = defaultdict(int)
    for a in activity:
        if str(a.get("week")) == week:
            u = str(a.get("username", "")).lstrip("@")
            try:
                msgs[u] += int(a.get("messages", 0) or 0)
            except Exception:
                pass
    vote_cnt = defaultdict(int)
    for v in votes:
        if str(v.get("week")) == week:
            vote_cnt[str(v.get("votee_username", "")).lstrip("@")] += 1

    users = list(assigned)
    max_msg = max((msgs[u] for u in users), default=0)
    max_vote = max((vote_cnt[u] for u in users), default=0)

    rows = []
    for u in users:
        a = assigned[u]
        comp_pct = round(100 * done[u] / a, 1) if a else 0.0
        ontime_pct = round(100 * ontime[u] / done[u], 1) if done[u] else 0.0
        vote_norm = _norm(vote_cnt[u], max_vote)
        act_norm = _norm(msgs[u], max_msg)
        base = round(
            (W["completion"] * comp_pct + W["ontime"] * ontime_pct
             + W["vote"] * vote_norm + W["activity"] * act_norm) / wsum, 1)

        avg_resp = round(resp_sum[u] / resp_cnt[u], 1) if resp_cnt[u] else None
        bonus = response_bonus(avg_resp)
        score = round(base + bonus, 1)

        rows.append({
            "user_id": u, "username": u,
            "assigned": a, "completed": done[u],
            "completion_pct": comp_pct, "ontime_pct": ontime_pct,
            "votes": vote_cnt[u], "messages": msgs[u],
            "vote_norm": vote_norm, "activity_norm": act_norm,
            "response_min": avg_resp if avg_resp is not None else "",
            "base_score": base, "response_bonus": bonus,
            "score": score, "weekly_points": 0,
        })

    elig = [r for r in rows
            if r["score"] >= config.MIN_SCORE_FOR_POINTS
            and r["completion_pct"] >= config.MIN_COMPLETION_FOR_POINTS]  # 완료율 하한 게이트
    elig.sort(key=lambda r: (r["score"], r["completion_pct"]), reverse=True)
    for i, r in enumerate(elig):
        if i < len(config.WEEKLY_POINTS):
            r["weekly_points"] = config.WEEKLY_POINTS[i]

    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows


def compute_quarter(points_rows, quarter) -> list[dict]:
    agg = defaultdict(lambda: {"points": 0, "scores": []})
    for p in points_rows:
        if week_to_quarter_from_isoweek(str(p.get("week", ""))) != quarter:
            continue
        u = p.get("username") or p.get("user_id")
        agg[u]["points"] += int(p.get("weekly_points", 0) or 0)
        try:
            agg[u]["scores"].append(float(p.get("score", 0) or 0))
        except Exception:
            pass
    rows = []
    for u, a in agg.items():
        avg = round(sum(a["scores"]) / len(a["scores"]), 1) if a["scores"] else 0.0
        rows.append({"user_id": u, "username": u,
                     "total_points": a["points"], "avg_score": avg})
    rows.sort(key=lambda r: (r["total_points"], r["avg_score"]), reverse=True)
    for i, r in enumerate(rows, start=1):
        r["rank"] = i
    return rows
