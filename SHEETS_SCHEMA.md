# HRM Google Sheets 스키마 (7 탭)

봇 첫 실행 시 없는 탭/헤더는 자동 생성됩니다 (`hrm.ensure_schema`).

## 1) Tasks — 작업 단일 원장
`task_id · group_title · group_id · assigner · assignee · description ·
created_at · due_at · status · acknowledged_at · completed_at · confidence · source_msg_id`
- `acknowledged_at` = 담당자 첫 응답 시각(답변회신속도 측정용)
- status: `open · in_progress · pending_review · done · missed`
- `pending_review` = 완료로 추정되나 admin 승인 대기 (completed_at 잠정 기록)

## 2) Members — 직원 마스터
`user_id · username · display_name · team · active`

## 2b) Groups — 채팅방 등록
`name · invite_url · chat_id · bot_token · active · added_at`
- `/addgroup`(그룹) 또는 admin.html→seed.py 로 등록. chat_id는 봇이 자동 채움.

## 3) Activity — 대화수(메시지) 일일 델타 (append-only, 주차로 합산)
`date · week · user_id · username · messages`

## 4) Votes — 커뮤니케이션 투표 (append-only)
`created_at · week · voter_id · votee_username`

## 5) Points — 주간 가중점수 집계
`week · user_id · username · assigned · completed · completion_pct ·
ontime_pct · votes · messages · response_min · base_score · response_bonus ·
score · weekly_points · awarded_at`

## 6) Quarter — 분기 누적 & 인센티브
`quarter · user_id · username · total_points · avg_score · rank · incentive`

## 7) Config — (선택) 런타임 설정. 비워도 .env로 동작.

## 데이터 흐름
```
그룹챗 메시지
  ├─ 작업 지시 감지 ─────────► Tasks(status=open)
  ├─ 메시지 카운트 ──(매일 flush)─► Activity
  ├─ /vote @동료 ───────────► Votes
  └─ 완료 신호(키워드/AI)
        ├─ 신뢰도≥임계 ─────► Tasks(status=done)        [자동승인]
        └─ 미만 ───────────► Tasks(status=pending_review) ─► admin ✅/❌
                                                            ├─승인►done
                                                            └─반려►in_progress
매주 일 23:00  Tasks+Activity+Votes ─► 가중점수 ─► Points ─► 상위자 +weekly_points
분기 첫날 00:30  Points ─► Quarter(누적 순위)
Dashboard ─► Quarter/Points/Tasks 읽어 시각화
```
