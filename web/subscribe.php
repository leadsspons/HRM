<?php
$cfg = require __DIR__ . '/config.php';
require __DIR__ . '/lib/Stripe.php';

$plan  = $_GET['plan'] ?? '';
$valid = ['starter', 'pro', 'enterprise'];
if (!in_array($plan, $valid, true)) { http_response_code(400); exit('Invalid plan.'); }

$stripe = new StripeClient($cfg['stripe']);
$base = $cfg['stripe']['site_url'] ?:
        ((isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off' ? 'https' : 'http') . '://' . $_SERVER['HTTP_HOST']);

if (!$stripe->configured() || $stripe->priceId($plan) === '') {
    header('Location: pricing.php?notice=not_configured');
    exit;
}
try {
    $url = $stripe->createCheckoutSession(
        $stripe->priceId($plan),
        $base . '/success.php?session_id={CHECKOUT_SESSION_ID}',
        $base . '/pricing.php',
        $_GET['email'] ?? ''
    );
    header('Location: ' . $url);
    exit;
} catch (Throwable $e) {
    http_response_code(500);
    echo 'Payment error: ' . htmlspecialchars($e->getMessage());
}
