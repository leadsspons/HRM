"""환경설정 로더."""
import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
HRM_ADMIN_CHAT_ID = os.getenv("HRM_ADMIN_CHAT_ID", "")

GOOGLE_SA_KEYFILE = os.getenv("GOOGLE_SA_KEYFILE", "./service_account.json")
HRM_SHEET_ID = os.getenv("HRM_SHEET_ID", "")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
AI_MODEL = os.getenv("AI_MODEL", "claude-haiku-4-5-20251001")

# --- 인센티브 포인트(주간 가중점수 순위 상위자에게) ---
WEEKLY_POINTS = [int(x) for x in os.getenv("WEEKLY_POINTS", "10,6,3").split(",")]
MIN_SCORE_FOR_POINTS = float(os.getenv("MIN_SCORE_FOR_POINTS", "60"))

# --- 작업 기본값 ---
DEFAULT_DUE_HOURS = int(os.getenv("DEFAULT_DUE_HOURS", "24"))
TIMEZONE = os.getenv("TIMEZONE", "Asia/Dubai")

# --- 하이브리드 승인 ---
# 이 신뢰도 이상이면 admin 승인 없이 자동 완료. 미만이면 pending_review.
AUTO_APPROVE_THRESHOLD = float(os.getenv("AUTO_APPROVE_THRESHOLD", "0.9"))
# 키워드/명령(/done)으로 본인이 보고한 완료의 기본 신뢰도
KEYWORD_CONFIDENCE = float(os.getenv("KEYWORD_CONFIDENCE", "0.8"))

# --- 가중 점수 (합계 100 권장) ---
# 완료율·완료시간준수율을 가장 무겁게.
W_COMPLETION = float(os.getenv("W_COMPLETION", "35"))   # 완료율
W_ONTIME     = float(os.getenv("W_ONTIME", "30"))       # 완료시간준수율
W_VOTE       = float(os.getenv("W_VOTE", "20"))         # 커뮤니케이션 투표
W_ACTIVITY   = float(os.getenv("W_ACTIVITY", "15"))     # 대화수

WEIGHTS = {
    "completion": W_COMPLETION,
    "ontime": W_ONTIME,
    "vote": W_VOTE,
    "activity": W_ACTIVITY,
}

# --- 답변회신속도 가산점 ---
# 배정→첫 응답까지 평균 분. FAST 이내면 만점 보너스, SLOW 이상이면 0.
RESPONSE_BONUS_MAX = float(os.getenv("RESPONSE_BONUS_MAX", "10"))   # 최대 가산점
RESPONSE_FAST_MIN  = float(os.getenv("RESPONSE_FAST_MIN", "30"))    # 분
RESPONSE_SLOW_MIN  = float(os.getenv("RESPONSE_SLOW_MIN", "480"))   # 분(8h)

# --- 완료율 하한 게이트 ---
# 완료율이 이 값 미만이면 다른 지표가 좋아도 주간 포인트 0.
MIN_COMPLETION_FOR_POINTS = float(os.getenv("MIN_COMPLETION_FOR_POINTS", "70"))
