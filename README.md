# Emirard HRM Completion Dashboard Challenge

텔레그램 그룹챗의 작업 지시/완료를 자동 추적해 Google Sheets(HRM)에 적재하고,
**가중 점수**(완료율·완료시간준수율·커뮤니케이션 투표·대화수)로 주간 순위를 매겨
인센티브 포인트를 누적, 분기말에 인센티브를 지급하는 시스템입니다.

```
Telegram 봇 ──► Google Sheets (HRM) ──► Dashboard
 감지·하이브리드 승인·집계    단일 원장        리더보드·지표분해·승인큐
```

## 웹 서비스 배포
`web/` 폴더를 PHP 서버 도큐먼트 루트에 올리면 서비스 페이지(`index.php`),
JSON API(`api.php`), 모든 대시보드가 한 번에 구동됩니다. 자세한 내용은 `web/README_PHP.md`.

## 구성 파일
| 파일 | 역할 |
|---|---|
| `bot.py` | 메시지 모니터링, 명령어, **하이브리드 승인**, 스케줄(일/주/분기) |
| `hrm.py` | Google Sheets 7개 탭 읽기/쓰기, 승인 상태전이 |
| `completion.py` | 작업 지시 감지 + 완료 판정(키워드 + AI 맥락) |
| `points.py` | **가중 점수** 4지표 계산, 주간/분기 집계 |
| `config.py` | 환경설정·가중치·임계값 로더 |
| `dashboard.html` | 라이브 대시보드 (브라우저에서 Google Sheet gviz 연동) |
| `artifact_dashboard.html` | Cowork 영구 아티팩트용 (라이트 모드, 샘플 시드) |
| `admin.html` | 관리자 콘솔 — 채팅방·임직원 등록 → seed.json 내보내기 |
| `employee_tracker.html` | 매니저용 — 직원별·일자별 due time·정시달성·할당 작업 수 |
| `user_challenge.html` | 유저용 — 포디움·배지·스트릭·활동피드로 경쟁/동기부여 |
| `guide_en.html` / `guide_ko.html` | 봇 토큰·초대 URL 발급 가이드(영/국) |
| `seed.py` | seed.json 을 시트의 Groups·Members 탭에 일괄 등록 |
| `SCORING.md` | 가중치·포인트 정책 상세 |
| `SHEETS_SCHEMA.md` | 시트 탭/컬럼 정의 |

---

## 설치 (단계별)

### 1. BotFather 봇 토큰
1. @BotFather → `/newbot` → **토큰** 복사
2. `/setprivacy` → **Disable** ⚠️ (그룹 일반 메시지를 읽으려면 필수)
3. 봇을 각 그룹챗에 초대하고 **관리자**로 지정

### 2. Google 서비스계정 + 시트
1. Google Cloud Console → **Sheets API** 사용 설정
2. 서비스 계정 키(JSON) 다운로드 → `service_account.json`
3. 새 Google Sheet 생성 → 서비스계정 이메일을 **편집자로 공유**
4. URL의 `/d/`~`/edit` 사이가 **HRM_SHEET_ID** (탭은 자동 생성)

### 3. HRM admin 채팅 ID
승인 알림·요약을 받을 곳. `https://api.telegram.org/bot<토큰>/getUpdates` 로 chat.id 확인.
⚠️ 인라인 승인 버튼은 **이 채팅에서만** 작동(관리자 전용).

### 4. 설정 & 실행
```bash
cp .env.example .env        # 토큰, SHEET_ID, admin chat, 가중치 등
pip install -r requirements.txt
python bot.py               # 24h 가동은 systemd/pm2/docker 권장
```
`ANTHROPIC_API_KEY`를 넣으면 대화 맥락 기반 완료 추론이 켜집니다(없으면 키워드만).

### 5. 대시보드
- **실시간**: 시트를 *웹에 게시* → `dashboard.html`의 `CONFIG.sheetId`에 ID 입력 → 브라우저로 열기
- **Cowork 영구 보기**: 사이드바 아티팩트 `emirard-hrm-completion-challenge` (현재 샘플 시드)

### 6. 채팅방·임직원 등록 (두 가지 방법)
**A. 텔레그램 명령 (즉시)**
- 그룹 안에서 `/addgroup` → 그 채팅방이 chat_id와 함께 등록.
- admin 채팅에서 `/addmember @user "이름" 팀` → 임직원 등록.

**B. 관리자 대시보드 (일괄)**
1. `admin.html` 을 브라우저로 열어 채팅방(이름/URL/토큰)과 임직원을 입력.
2. **seed.json 내보내기** → 파일을 `emirard-hrm-bot` 폴더에 저장.
3. `python seed.py` → Google Sheet의 `Groups`·`Members` 탭에 일괄 반영.

> 봇 하나로 여러 그룹을 운영하면 토큰은 비워두세요(`.env`의 기본 봇 사용).
> 그룹별 별도 봇을 쓸 때만 토큰을 채웁니다. chat_id는 봇이 메시지를 보면 자동 채워집니다.

---

## 사용법 (그룹챗)
| 동작 | 입력 |
|---|---|
| 작업 지시(자동) | `@sara 오늘 광고 리포트 정리 해줘` |
| 작업 지시(명령) | `/task @sara 광고 리포트 정리` |
| 완료 보고 | `완료했습니다 ✅` 또는 `/done <task_id>` |
| 진행중 | `지금 작업중이에요` |
| 커뮤니케이션 투표 | `/vote @동료` |
| 열린 작업 | `/tasks` |
| 승인 대기(admin) | `/pending` · 버튼 또는 `/approve <id>` `/reject <id>` |
| 채팅방 등록 | `/addgroup`(그룹 안) · `/groups` 목록 |
| 임직원 등록(admin) | `/addmember @user "이름" 팀` · `/members` 목록 |

## 하이브리드 완료 승인 (정확도 ↑)
1. 봇이 완료를 감지하면 **신뢰도**를 매깁니다.
2. `신뢰도 ≥ AUTO_APPROVE_THRESHOLD`(기본 0.9) → 즉시 `done` 자동완료.
3. 미만 → `pending_review`로 두고 **admin 채팅에 ✅/❌ 버튼** 전송.
   - ✅ 승인 → `done` 확정 (완료시간준수 판정은 보고 시점 기준).
   - ❌ 반려 → `in_progress` 복귀.
4. `완료시간준수율`은 잠정 `completed_at ≤ due_at` 으로 계산되므로,
   승인이 늦어도 담당자의 실제 보고 시점이 기준입니다.

## 가중 점수 (요약, 상세는 SCORING.md)
| 지표 | 가중치 |
|---|---|
| 완료율 | 35% |
| 완료시간준수율 | 30% |
| 커뮤니케이션 투표 | 20% |
| 대화수 | 15% |
| ⚡ 답변회신속도 | 가산점(+) |

답변회신속도는 가중점수 위에 더해지는 **보너스**입니다(배정→첫 응답 평균시간, 30분 내 +10 ~ 8h 0).
**완료율 하한 게이트**: 완료율이 `MIN_COMPLETION_FOR_POINTS`(기본 70%) 미만이면 점수가 높아도 주간 포인트 0.
`.env`의 `W_*`, `WEEKLY_POINTS`, `MIN_SCORE_FOR_POINTS`, `RESPONSE_*`, 임계값으로 코드 수정 없이 조정.

## 자동 스케줄 (TIMEZONE 기준)
- **매일 21:00** — 대화수 flush + 일일 요약 + 마감초과 `missed` 처리
- **매주 일 23:00** — 주간 가중점수 → `Points` → 상위자 인센티브 포인트
- **분기 첫날 00:30** — `Quarter` 누적 → 최종 순위

## 한계
- 자동 완료판정은 100%가 아니므로 하이브리드 승인을 권장합니다.
- 투표·대화수는 코호트 상대 정규화라 소규모 팀에서 한 명이 독식 시 튈 수 있음 → SCORING.md 참고해 가중치 조정.
- 봇 privacy mode를 끄지 않으면 일반 대화를 못 읽습니다.
