"""task 감지 및 완료 판정 (키워드 + 선택적 AI 맥락 추론)."""
from __future__ import annotations
import re

import config

# --- 작업 지시 감지 ---
ASSIGN_KEYWORDS = ["해줘", "해주세요", "부탁", "처리", "진행", "맡아", "해주실", "please", "todo", "to-do"]
MENTION_RE = re.compile(r"@(\w+)")


def detect_assignment(text: str) -> bool:
    """일반 메시지가 작업 지시인지 휴리스틱 판단."""
    if not text:
        return False
    low = text.lower()
    has_mention = bool(MENTION_RE.search(text))
    has_kw = any(k in low for k in ASSIGN_KEYWORDS)
    return has_mention and has_kw


def parse_assignment(text: str):
    """담당자 핸들과 작업 설명 추출."""
    m = MENTION_RE.search(text)
    assignee = m.group(1) if m else None
    desc = MENTION_RE.sub("", text).strip(" :,-").strip()
    return assignee, desc


# --- 완료 신호 감지 ---
DONE_KEYWORDS = ["완료", "끝냈", "끝났", "처리했", "done", "완성", "마무리", "finished", "complete", "✅", "☑️", "👍"]
PROGRESS_KEYWORDS = ["하는중", "진행중", "작업중", "보는중", "확인중", "wip", "in progress"]


def keyword_status(text: str) -> str | None:
    if not text:
        return None
    low = text.lower()
    if any(k in low for k in DONE_KEYWORDS):
        return "done"
    if any(k in low for k in PROGRESS_KEYWORDS):
        return "in_progress"
    return None


# --- AI 맥락 추론 (선택) ---
def ai_match_completion(message_text: str, open_tasks: list[dict]) -> list[dict]:
    """
    대화 메시지와 미완료 작업 목록을 LLM에 주고
    어떤 작업이 완료/진행으로 보이는지 판단.
    반환: [{"task_id":..., "status":"done|in_progress", "confidence":0~1}]
    ANTHROPIC_API_KEY가 없으면 빈 리스트 반환(키워드 폴백).
    """
    if not config.ANTHROPIC_API_KEY or not open_tasks:
        return []
    try:
        import anthropic, json
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        task_lines = "\n".join(
            f'- {t["task_id"]}: (담당 @{t["assignee"]}) {t["description"]}'
            for t in open_tasks)
        prompt = (
            "다음은 팀 그룹챗의 최근 메시지와, 현재 미완료 작업 목록입니다.\n"
            "메시지가 어떤 작업의 '완료(done)' 또는 '진행중(in_progress)'을 의미하는지 판단하세요.\n"
            "해당 없으면 빈 배열을 반환합니다. JSON 배열만 출력:\n"
            '[{"task_id":"...","status":"done|in_progress","confidence":0.0~1.0}]\n\n'
            f"[메시지]\n{message_text}\n\n[미완료 작업]\n{task_lines}"
        )
        resp = client.messages.create(
            model=config.AI_MODEL, max_tokens=500,
            messages=[{"role": "user", "content": prompt}])
        raw = resp.content[0].text.strip()
        raw = raw[raw.find("["): raw.rfind("]") + 1]
        return json.loads(raw)
    except Exception as e:
        print(f"[ai_match_completion] fallback: {e}")
        return []
