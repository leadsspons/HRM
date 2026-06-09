<?php $sid = $_GET['session_id'] ?? ''; ?>
<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Workidoki · Subscription confirmed</title>
<style>
  body{font-family:'Segoe UI',system-ui,sans-serif;background:#f6f8fc;color:#1c2335;
    display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0;padding:24px}
  .box{background:#fff;border:1px solid #e1e7f2;border-radius:18px;padding:40px;text-align:center;max-width:480px;box-shadow:0 10px 30px rgba(20,30,60,.08)}
  img{height:30px;margin-bottom:18px}
  .ic{font-size:48px}
  h1{font-size:22px;margin:10px 0 6px;color:#16a34a}
  p{color:#6b7592;font-size:14px;line-height:1.6}
  a{display:inline-block;margin-top:20px;background:#2056f0;color:#fff;text-decoration:none;font-weight:700;padding:11px 22px;border-radius:11px}
  code{background:#eef2fa;padding:1px 6px;border-radius:5px;font-size:11px;color:#6b7592}
</style></head>
<body><div class="box">
  <img src="workidoki-logo.png" alt="Workidoki"><div class="ic">🎉</div>
  <h1>You're subscribed!</h1>
  <p>Thanks for subscribing to Workidoki. Your team's completion challenge is ready to roll.
     A receipt has been emailed to you by Stripe.</p>
  <?php if ($sid): ?><p style="margin-top:10px"><code><?= htmlspecialchars($sid) ?></code></p><?php endif; ?>
  <a href="index.php">Go to dashboards →</a>
</div></body></html>
