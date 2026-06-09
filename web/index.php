<?php
$cfg = require __DIR__ . '/config.php';
require __DIR__ . '/lib/Sheets.php';
$mode = 'unknown'; $configured = false; $err = '';
try { $s = new Sheets($cfg); $mode = $s->mode(); $configured = $s->sheetConfigured(); }
catch (Throwable $e) { $err = $e->getMessage(); }
$statusOk = $configured;
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Workidoki HRM · Completion Dashboard Challenge</title>
<style>
  :root{color-scheme:light;--bg:#f6f8fc;--panel:#fff;--line:#e1e7f2;--txt:#1c2335;--mut:#6b7592;
    --acc:#3b5bdb;--good:#10b981;--bad:#ef4444;--gold:#d99e00;--purple:#7c3aed;--blue:#3b82f6;--fire:#f97316;}
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--txt);padding:30px}
  .wrap{max-width:1040px;margin:0 auto}
  .hero{background:linear-gradient(120deg,#3b5bdb,#7c3aed);color:#fff;border-radius:20px;padding:30px 30px;margin-bottom:22px}
  .hero h1{font-size:26px;margin-bottom:6px}.hero p{opacity:.92;font-size:14px;max-width:640px}
  .status{display:inline-flex;align-items:center;gap:8px;margin-top:14px;background:rgba(255,255,255,.16);
    padding:7px 14px;border-radius:999px;font-size:13px}
  .dot{width:9px;height:9px;border-radius:50%}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}
  a.card{display:block;text-decoration:none;color:inherit;background:var(--panel);border:1px solid var(--line);
    border-radius:16px;padding:20px;box-shadow:0 1px 3px rgba(20,30,60,.05);transition:transform .12s,box-shadow .12s}
  a.card:hover{transform:translateY(-3px);box-shadow:0 8px 24px rgba(20,30,60,.1)}
  .ic{font-size:26px}
  .card h2{font-size:17px;margin:10px 0 4px;display:flex;align-items:center;gap:8px}
  .card p{color:var(--mut);font-size:13px;line-height:1.5}
  .c-lead h2{color:var(--gold)} .c-emp h2{color:var(--blue)} .c-team h2{color:var(--fire)}
  .c-admin h2{color:var(--purple)} .c-guide h2{color:var(--good)} .c-price h2{color:#2056f0}
  .tag{font-size:11px;color:var(--mut);border:1px solid var(--line);border-radius:999px;padding:2px 9px;margin-left:auto}
  footer{color:var(--mut);font-size:12px;text-align:center;margin-top:26px;line-height:1.7}
  code{background:#eef2fa;padding:1px 6px;border-radius:5px;font-size:12px}
</style>
</head>
<body>
<div class="wrap">
  <div class="hero">
    <img src="workidoki-logo.png" alt="Workidoki" style="height:38px;margin-bottom:14px;filter:brightness(0) invert(1)">
    <h1>🏆 HRM Completion Dashboard Challenge</h1>
    <p>Telegram tasks → Google Sheets (HRM) → live dashboards. Track completion, on-time delivery,
       response speed and peer votes — then turn it into a quarterly incentive challenge.</p>
    <div class="status">
      <span class="dot" style="background:<?= $statusOk ? '#34d399' : '#fca5a5' ?>"></span>
      <?php if ($statusOk): ?>
        Data source: <b style="margin:0 4px">&nbsp;<?= htmlspecialchars($mode) ?></b> · sheet connected
      <?php else: ?>
        Sheet not configured — edit <code>web/config.php</code> (sheet_id)
      <?php endif; ?>
    </div>
  </div>

  <div class="grid">
    <a class="card c-price" href="pricing.php">
      <div class="ic">💳</div><h2>Pricing &amp; Subscribe <span class="tag">start</span></h2>
      <p>Subscribe your company — Starter, Pro or Enterprise monthly plans.</p></a>
    <a class="card c-lead" href="dashboard.html">
      <div class="ic">🏆</div><h2>Challenge Leaderboard <span class="tag">all</span></h2>
      <p>Quarter standings, weighted score breakdown, approval queue and score trends.</p></a>
    <a class="card c-emp" href="employee_tracker.html">
      <div class="ic">📋</div><h2>Employee Tracker <span class="tag">manager</span></h2>
      <p>Per-employee, per-day due times, on-time status and task load matrix.</p></a>
    <a class="card c-team" href="user_challenge.html">
      <div class="ic">🔥</div><h2>Team Challenge <span class="tag">staff</span></h2>
      <p>Podium, badges, streaks and a live feed of what everyone is working on.</p></a>
    <a class="card c-admin" href="admin.html">
      <div class="ic">⚙️</div><h2>Admin Console <span class="tag">setup</span></h2>
      <p>Register chat rooms and employees, export a seed file, or write via the API.</p></a>
    <a class="card c-guide" href="guides.html">
      <div class="ic">📘</div><h2>Help &amp; Guides <span class="tag">EN / KO</span></h2>
      <p>Token &amp; invite URL, FTP sub-accounts, and server backups — EN/KO.</p></a>
  </div>

  <footer>
    JSON API: <code>api.php?action=health</code> · <code>api.php?action=rows&amp;tab=Quarter</code><br>
    Dashboards auto-detect the API when served here; otherwise they show sample data.
  </footer>
</div>
</body>
</html>
