"""Emirard HRM Telegram 봇 — 메인 엔트리 (하이브리드 승인 + 가중점수)."""
from __future__ import annotations
import datetime as dt
import logging
from collections import defaultdict
from zoneinfo import ZoneInfo

from telegram import (Update, InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (Application, CommandHandler, MessageHandler,
                          CallbackQueryHandler, ContextTypes, filters)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import config
import completion
import points
from hrm import HRM, now

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("emirard-hrm")

hrm = HRM()
TZ = ZoneInfo(config.TIMEZONE)

# 대화수: 메시지마다 in-memory 누적, 매일 flush (시트 쓰기 부하 절감)
ACTIVITY: dict[tuple, int] = defaultdict(int)
SEEN_GROUPS: set = set()   # 세션 내 자동 등록한 그룹 chat_id


def _handle(user) -> str:
    return user.username or user.full_name


def _is_admin_chat(chat_id) -> bool:
    return str(chat_id) == str(config.HRM_ADMIN_CHAT_ID)


# ---------- 명령어 ----------
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Emirard HRM 봇 가동 중 ✅\n"
        "• 작업 지시: @담당자 …해줘  또는  /task @담당자 내용\n"
        "• 완료: '완료' / ✅ / /done <task_id>\n"
        "• 투표: /vote @동료  (커뮤니케이션 우수자)\n"
        "• 현황: /tasks   승인대기: /pending (admin)\n"
        "• 등록: /addgroup (그룹), /addmember @user 팀 (admin)")


async def cmd_task(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = " ".join(ctx.args)
    assignee, desc = completion.parse_assignment(text)
    if not assignee or not desc:
        await update.message.reply_text("사용법: /task @담당자 작업내용")
        return
    await _create_task(update, assignee, desc)


async def cmd_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("사용법: /done <task_id>")
        return
    # 명시적 /done 은 본인 보고 → 자동완료 임계 비교
    await _resolve_completion(ctx, ctx.args[0], config.KEYWORD_CONFIDENCE,
                              reporter_chat=update.effective_chat.id,
                              reply=update.message)


async def cmd_vote(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("사용법: /vote @동료")
        return
    votee = ctx.args[0].lstrip("@")
    hrm.add_vote(update.message.from_user.id, votee)
    await update.message.reply_text(f"🗳 @{votee} 에게 커뮤니케이션 투표 완료")


async def cmd_tasks(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    rows = hrm.open_tasks_for_group(update.effective_chat.id)
    if not rows:
        await update.message.reply_text("열린 작업이 없습니다 🎉")
        return
    lines = [f"• {r['task_id']} @{r['assignee']} — {r['description']} "
             f"[{r['status']}] (~{str(r['due_at'])[5:16]})" for r in rows[:30]]
    await update.message.reply_text("열린 작업:\n" + "\n".join(lines))


async def cmd_addgroup(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """그룹 안에서 실행 → 현재 채팅방 등록. 인자로 표시이름/URL 지정 가능."""
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text("이 명령은 그룹챗 안에서 실행하세요.")
        return
    name = " ".join(ctx.args) if ctx.args else (chat.title or f"chat:{chat.id}")
    url = next((a for a in ctx.args if a.startswith("http")), "")
    hrm.register_group(name=name, invite_url=url, chat_id=chat.id)
    SEEN_GROUPS.add(chat.id)
    await update.message.reply_text(f"🏠 채팅방 등록됨: {name}\nchat_id={chat.id}")


async def cmd_addmember(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/addmember @user [표시이름] [팀]  (admin 채팅 전용)."""
    if not _is_admin_chat(update.effective_chat.id):
        await update.message.reply_text("admin 채팅에서만 사용할 수 있습니다.")
        return
    if not ctx.args:
        await update.message.reply_text("사용법: /addmember @user [표시이름] [팀]")
        return
    username = ctx.args[0].lstrip("@")
    display = ctx.args[1] if len(ctx.args) > 1 else username
    team = ctx.args[2] if len(ctx.args) > 2 else ""
    hrm.upsert_member(user_id=username, username=username,
                      display_name=display, team=team)
    await update.message.reply_text(f"👤 임직원 등록: @{username} · {display} · {team}")


async def cmd_groups(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    rows = hrm.list_groups()
    if not rows:
        await update.message.reply_text("등록된 채팅방이 없습니다. 그룹에서 /addgroup 실행.")
        return
    txt = "\n".join(f"• {r.get('name')} (chat_id={r.get('chat_id')})" for r in rows[:40])
    await update.message.reply_text("등록 채팅방:\n" + txt)


async def cmd_members(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    rows = hrm.list_members()
    if not rows:
        await update.message.reply_text("등록된 임직원이 없습니다.")
        return
    txt = "\n".join(f"• @{r.get('username')} · {r.get('display_name')} · {r.get('team')}"
                     for r in rows[:60])
    await update.message.reply_text("임직원:\n" + txt)


async def cmd_pending(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_admin_chat(update.effective_chat.id):
        return
    rows = hrm.pending_reviews()
    if not rows:
        await update.message.reply_text("승인 대기 중인 작업이 없습니다 ✅")
        return
    for r in rows[:20]:
        await update.message.reply_text(_review_text(r),
                                        reply_markup=_review_kb(r["task_id"]))


# ---------- 승인 UI ----------
def _review_text(t: dict) -> str:
    conf = t.get("confidence", "")
    return (f"🟡 *완료 승인 대기*\n{t['task_id']} · @{t['assignee']}\n"
            f"{t['description']}\n신뢰도: {conf}")


def _review_kb(task_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ 승인", callback_data=f"approve:{task_id}"),
        InlineKeyboardButton("❌ 반려", callback_data=f"reject:{task_id}"),
    ]])


async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not _is_admin_chat(q.message.chat.id):
        await q.answer("관리자만 승인할 수 있습니다", show_alert=True)
        return
    action, tid = q.data.split(":", 1)
    if action == "approve":
        ok = hrm.approve_task(tid)
        await q.edit_message_text(f"✅ 승인됨 · {tid} 완료 확정" if ok
                                  else f"이미 처리됨 · {tid}")
    elif action == "reject":
        ok = hrm.reject_task(tid)
        await q.edit_message_text(f"❌ 반려됨 · {tid} 진행중 복귀" if ok
                                  else f"이미 처리됨 · {tid}")


async def cmd_approve(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_admin_chat(update.effective_chat.id) or not ctx.args:
        return
    ok = hrm.approve_task(ctx.args[0])
    await update.message.reply_text("✅ 승인 완료" if ok else "대기 상태가 아님")


async def cmd_reject(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _is_admin_chat(update.effective_chat.id) or not ctx.args:
        return
    ok = hrm.reject_task(ctx.args[0])
    await update.message.reply_text("❌ 반려 완료" if ok else "대기 상태가 아님")


# ---------- 메시지 모니터링 ----------
async def on_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    if not msg or not msg.text:
        return
    user = msg.from_user
    handle = _handle(user)
    hrm.upsert_member(user.id, user.username, user.full_name)
    ACTIVITY[(user.id, handle)] += 1   # 대화수 집계
    chat = update.effective_chat
    if chat.type in ("group", "supergroup") and chat.id not in SEEN_GROUPS:
        hrm.touch_group(chat.id, chat.title)   # 채팅방 자동 등록
        SEEN_GROUPS.add(chat.id)
    text = msg.text

    # 1) 작업 지시 감지
    if completion.detect_assignment(text):
        assignee, desc = completion.parse_assignment(text)
        if assignee and desc:
            await _create_task(update, assignee, desc)
            return

    open_tasks = hrm.open_tasks_for_group(update.effective_chat.id)
    if not open_tasks:
        return

    # 1.5) 답변회신속도: 담당자의 첫 응답 시각 기록
    for t in open_tasks:
        if t.get("assignee") == handle and not t.get("acknowledged_at"):
            hrm.ack_task(t["task_id"])

    # 2) 완료/진행 신호 — 키워드 우선
    kw = completion.keyword_status(text)
    if kw == "in_progress":
        mine = [t for t in open_tasks if t["assignee"] == handle] or open_tasks
        hrm.mark_in_progress(mine[0]["task_id"])
        return
    if kw == "done":
        mine = [t for t in open_tasks if t["assignee"] == handle] or open_tasks
        await _resolve_completion(ctx, mine[0]["task_id"], config.KEYWORD_CONFIDENCE,
                                  reporter_chat=update.effective_chat.id, reply=msg)
        return

    # 3) AI 맥락 추론 (키워드 미감지 + AI 키 존재 시)
    for m in completion.ai_match_completion(text, open_tasks):
        conf = float(m.get("confidence", 0))
        if m.get("status") == "done" and conf >= 0.6:
            await _resolve_completion(ctx, m["task_id"], conf,
                                      reporter_chat=update.effective_chat.id, reply=None)
        elif m.get("status") == "in_progress" and conf >= 0.6:
            hrm.mark_in_progress(m["task_id"])


async def _resolve_completion(ctx, task_id, confidence, reporter_chat, reply):
    """하이브리드 핵심: 신뢰도 임계 이상이면 자동완료, 아니면 admin 승인 대기."""
    t = hrm.get_task(task_id)
    if not t or t.get("status") in ("done",):
        return
    if confidence >= config.AUTO_APPROVE_THRESHOLD:
        hrm.mark_done(task_id, confidence=confidence)
        if reply:
            await reply.reply_text(f"기록함 ✅ {task_id} 완료 (자동승인)")
    else:
        hrm.mark_pending_review(task_id, confidence=confidence)
        if reply:
            await reply.reply_text(f"📝 {task_id} 완료 보고 접수 — 관리자 승인 대기")
        if config.HRM_ADMIN_CHAT_ID:
            t2 = hrm.get_task(task_id)
            await ctx.bot.send_message(
                config.HRM_ADMIN_CHAT_ID, _review_text(t2),
                parse_mode="Markdown", reply_markup=_review_kb(task_id))


async def _create_task(update: Update, assignee: str, desc: str):
    chat = update.effective_chat
    due = now() + dt.timedelta(hours=config.DEFAULT_DUE_HOURS)
    tid = hrm.add_task(
        group_title=chat.title or "DM", group_id=chat.id,
        assigner=_handle(update.message.from_user),
        assignee=assignee.lstrip("@"), description=desc, due_at=due,
        source_msg_id=update.message.message_id)
    await update.message.reply_text(
        f"📌 작업 등록: {tid}\n담당 @{assignee.lstrip('@')} · 마감 {due.strftime('%m/%d %H:%M')}")


# ---------- 스케줄 ----------
async def daily_report(app: Application):
    # 대화수 flush
    counts = {k: v for k, v in ACTIVITY.items()}
    hrm.flush_activity(counts)
    ACTIVITY.clear()

    hrm.sweep_overdue()
    tasks = hrm.all_tasks()
    today = now().date().isoformat()
    todays = [t for t in tasks if str(t.get("created_at", "")).startswith(today)]
    done = sum(1 for t in todays if t["status"] == "done")
    pend = sum(1 for t in todays if t["status"] == "pending_review")
    missed = sum(1 for t in todays if t["status"] == "missed")
    openn = sum(1 for t in todays if t["status"] in ("open", "in_progress"))
    text = (f"🗓 *HRM 일일 요약* ({today})\n"
            f"등록 {len(todays)} · 완료 {done} · 승인대기 {pend} · "
            f"진행 {openn} · 마감초과 {missed}")
    if config.HRM_ADMIN_CHAT_ID:
        await app.bot.send_message(config.HRM_ADMIN_CHAT_ID, text, parse_mode="Markdown")


async def weekly_points(app: Application):
    wk = points.iso_week(now().date())
    rows = points.compute_weekly(hrm.all_tasks(), hrm.all_activity(),
                                 hrm.all_votes(), wk)
    if not rows:
        return
    hrm.write_points(wk, rows)
    top = "\n".join(
        f"{i+1}. @{r['username']} · {r['score']}점 "
        f"(완료 {r['completion_pct']}% / 준수 {r['ontime_pct']}% / 응답+{r['response_bonus']}) "
        f"+{r['weekly_points']}p"
        for i, r in enumerate(rows[:5]))
    if config.HRM_ADMIN_CHAT_ID:
        await app.bot.send_message(
            config.HRM_ADMIN_CHAT_ID,
            f"🏆 *{wk} 주간 챌린지*\n{top}", parse_mode="Markdown")


async def quarter_rollup(app: Application):
    q = points.quarter_of(now().date())
    qrows = points.compute_quarter(hrm.all_points(), q)
    if not qrows:
        return
    hrm.write_quarter(q, qrows)
    if config.HRM_ADMIN_CHAT_ID:
        top = "\n".join(f"{r['rank']}. @{r['username']} {r['total_points']}p"
                        for r in qrows[:5])
        await app.bot.send_message(
            config.HRM_ADMIN_CHAT_ID,
            f"💎 *{q} 분기 인센티브 순위*\n{top}", parse_mode="Markdown")


def setup_scheduler(app: Application):
    sched = AsyncIOScheduler(timezone=config.TIMEZONE)
    sched.add_job(daily_report, "cron", hour=21, minute=0, args=[app])
    sched.add_job(weekly_points, "cron", day_of_week="sun", hour=23, args=[app])
    sched.add_job(quarter_rollup, "cron", month="1,4,7,10", day=1, hour=0,
                  minute=30, args=[app])
    sched.start()


def main():
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("task", cmd_task))
    app.add_handler(CommandHandler("done", cmd_done))
    app.add_handler(CommandHandler("vote", cmd_vote))
    app.add_handler(CommandHandler("tasks", cmd_tasks))
    app.add_handler(CommandHandler("pending", cmd_pending))
    app.add_handler(CommandHandler("addgroup", cmd_addgroup))
    app.add_handler(CommandHandler("addmember", cmd_addmember))
    app.add_handler(CommandHandler("groups", cmd_groups))
    app.add_handler(CommandHandler("members", cmd_members))
    app.add_handler(CommandHandler("approve", cmd_approve))
    app.add_handler(CommandHandler("reject", cmd_reject))
    app.add_handler(CallbackQueryHandler(on_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    setup_scheduler(app)
    log.info("Emirard HRM bot started.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
