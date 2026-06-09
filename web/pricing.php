<?php
$cfg = require __DIR__ . '/config.php';
require __DIR__ . '/lib/Stripe.php';
$stripe = new StripeClient($cfg['stripe']);
$ready = $stripe->configured();
$notice = $_GET['notice'] ?? '';

$plans = [
  ['id'=>'starter','name'=>'Starter','price'=>'$29','accent'=>'#64748b','popular'=>false,
   'features'=>['1 Telegram group','Up to 15 employees','Weekly completion challenge','All dashboards','Email support']],
  ['id'=>'pro','name'=>'Pro','price'=>'$79','accent'=>'#2056f0','popular'=>true,
   'features'=>['Up to 10 groups','Up to 100 employees','Response-speed bonus','Hybrid approvals + peer voting','Priority support']],
  ['id'=>'enterprise','name'=>'Enterprise','price'=>'$199','accent'=>'#7c3aed','popular'=>false,
   'features'=>['Unlimited groups & employees','JSON API access','Custom score weights','SSO & onboarding','Dedicated support']],
];
?>
<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Workidoki · Pricing</title>
<style>
  :root{color-scheme:light;--bg:#f6f8fc;--panel:#fff;--line:#e1e7f2;--txt:#1c2335;--mut:#6b7592;--blue:#2056f0;--good:#16a34a;}
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--txt);padding:30px}
  .wrap{max-width:1040px;margin:0 auto}
  .top{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:10px;margin-bottom:8px}
  .top img{height:30px}
  .home{font-size:12.5px;text-decoration:none;color:var(--blue);border:1px solid var(--line);padding:6px 11px;border-radius:8px;background:#fff}
  h1{font-size:27px;text-align:center;margin-top:18px}
  .sub{color:var(--mut);font-size:14px;text-align:center;margin:6px 0 24px}
  .notice{max-width:680px;margin:0 auto 22px;background:#fffbeb;border:1px solid #fde68a;color:#92400e;border-radius:11px;padding:12px 15px;font-size:13px;text-align:center}
  .grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
  .card{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:26px 22px;position:relative;display:flex;flex-direction:column}
  .card.pop{border:2px solid var(--blue);box-shadow:0 12px 30px rgba(32,86,240,.14)}
  .tagpop{position:absolute;top:-12px;left:50%;transform:translateX(-50%);background:var(--blue);color:#fff;font-size:11px;font-weight:700;padding:4px 12px;border-radius:999px}
  .pname{font-size:15px;font-weight:700}
  .pprice{font-size:38px;font-weight:800;margin:8px 0 2px}
  .pprice small{font-size:15px;color:var(--mut);font-weight:600}
  ul{list-style:none;margin:16px 0 22px;padding:0;flex:1}
  li{font-size:13.5px;padding:7px 0;border-bottom:1px dashed var(--line);display:flex;gap:8px;align-items:flex-start}
  li::before{content:"✓";color:var(--good);font-weight:800}
  .btn{display:block;text-align:center;text-decoration:none;font-weight:700;font-size:14px;padding:12px;border-radius:11px;color:#fff;background:var(--blue)}
  .btn.alt{background:#1c2335}
  footer{color:var(--mut);font-size:12px;text-align:center;margin-top:26px;line-height:1.7}
  @media(max-width:820px){.grid{grid-template-columns:1fr}}
</style></head>
<body><div class="wrap">
  <div class="top">
    <img src="workidoki-logo.png" alt="Workidoki">
    <a class="home" href="index.php">← Home</a>
  </div>
  <h1>Plans for every team</h1>
  <div class="sub">Turn your Telegram task chatter into a measurable completion challenge. Cancel anytime.</div>

  <?php if ($notice === 'not_configured' || !$ready): ?>
    <div class="notice">⚙️ Billing isn't connected yet. The site owner needs to add Stripe keys &amp; price IDs in <b>config.php</b> (see README_PHP.md). Buttons below will work once configured.</div>
  <?php endif; ?>

  <div class="grid">
    <?php foreach ($plans as $p): ?>
      <div class="card <?= $p['popular'] ? 'pop' : '' ?>">
        <?php if ($p['popular']): ?><div class="tagpop">MOST POPULAR</div><?php endif; ?>
        <div class="pname" style="color:<?= $p['accent'] ?>"><?= $p['name'] ?></div>
        <div class="pprice"><?= $p['price'] ?><small>/mo</small></div>
        <ul>
          <?php foreach ($p['features'] as $f): ?><li><?= htmlspecialchars($f) ?></li><?php endforeach; ?>
        </ul>
        <a class="btn <?= $p['popular'] ? '' : 'alt' ?>" href="subscribe.php?plan=<?= $p['id'] ?>">Subscribe</a>
      </div>
    <?php endforeach; ?>
  </div>

  <footer>
    Secure checkout by <b>Stripe</b> · You can change or cancel your plan anytime.<br>
    Prices in USD, billed monthly. Taxes may apply.
  </footer>
</div></body></html>
