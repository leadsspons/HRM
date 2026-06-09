<?php
// Stripe webhook endpoint — point your Stripe Dashboard webhook here:
//   https://YOUR-SITE/webhook.php   (events: checkout.session.completed, customer.subscription.*)
$cfg = require __DIR__ . '/config.php';
require __DIR__ . '/lib/Stripe.php';

$payload = file_get_contents('php://input');
$sig = $_SERVER['HTTP_STRIPE_SIGNATURE'] ?? '';
$stripe = new StripeClient($cfg['stripe']);

if (!$stripe->verifyWebhook($payload, $sig)) {
    http_response_code(400);
    exit('Invalid signature');
}

$event = json_decode($payload, true);
$type  = $event['type'] ?? '';
$obj   = $event['data']['object'] ?? [];

$dir = __DIR__ . '/data';
@mkdir($dir, 0775, true);
$store = $dir . '/subscribers.json';
$subs = is_file($store) ? (json_decode(file_get_contents($store), true) ?: []) : [];

if (in_array($type, ['checkout.session.completed', 'customer.subscription.created', 'customer.subscription.updated'], true)) {
    $id = $obj['id'] ?? uniqid('sub_', true);
    $subs[$id] = [
        'type'     => $type,
        'customer' => $obj['customer'] ?? '',
        'email'    => $obj['customer_details']['email'] ?? ($obj['customer_email'] ?? ''),
        'status'   => $obj['status'] ?? 'active',
        'updated'  => date('c'),
    ];
} elseif ($type === 'customer.subscription.deleted') {
    $id = $obj['id'] ?? '';
    if (isset($subs[$id])) $subs[$id]['status'] = 'canceled';
}

file_put_contents($store, json_encode($subs, JSON_PRETTY_PRINT));
http_response_code(200);
echo 'ok';
