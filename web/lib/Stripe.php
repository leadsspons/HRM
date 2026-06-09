<?php
/**
 * Minimal Stripe layer — Checkout Sessions (subscription) + webhook verify.
 * No SDK required (uses cURL + REST). Provide keys in config.php['stripe'].
 */
class StripeClient
{
    private $cfg;
    public function __construct(array $stripeCfg) { $this->cfg = $stripeCfg; }

    public function configured(): bool
    {
        return !empty($this->cfg['secret_key']);
    }

    public function priceId(string $plan): string
    {
        return $this->cfg['prices'][$plan] ?? '';
    }

    /** Create a subscription Checkout Session and return the redirect URL. */
    public function createCheckoutSession(string $priceId, string $successUrl, string $cancelUrl, string $email = ''): string
    {
        $fields = [
            'mode'                 => 'subscription',
            'line_items[0][price]' => $priceId,
            'line_items[0][quantity]' => 1,
            'success_url'          => $successUrl,
            'cancel_url'           => $cancelUrl,
            'allow_promotion_codes'=> 'true',
            'billing_address_collection' => 'auto',
        ];
        if ($email !== '') $fields['customer_email'] = $email;

        $resp = $this->post('https://api.stripe.com/v1/checkout/sessions', $fields);
        $json = json_decode($resp, true);
        if (empty($json['url'])) {
            throw new RuntimeException('Stripe session failed: ' . ($json['error']['message'] ?? 'unknown'));
        }
        return $json['url'];
    }

    /** Verify a webhook signature (Stripe-Signature header). */
    public function verifyWebhook(string $payload, string $sigHeader): bool
    {
        $secret = $this->cfg['webhook_secret'] ?? '';
        if ($secret === '' || $sigHeader === '') return false;
        $t = ''; $v1 = '';
        foreach (explode(',', $sigHeader) as $part) {
            $kv = explode('=', trim($part), 2);
            if (count($kv) !== 2) continue;
            if ($kv[0] === 't')  $t = $kv[1];
            if ($kv[0] === 'v1') $v1 = $kv[1];
        }
        if ($t === '' || $v1 === '') return false;
        // reject if older than 5 minutes (replay protection)
        if (abs(time() - (int)$t) > 300) return false;
        $expected = hash_hmac('sha256', $t . '.' . $payload, $secret);
        return hash_equals($expected, $v1);
    }

    private function post(string $url, array $fields): string
    {
        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_POST           => true,
            CURLOPT_POSTFIELDS     => http_build_query($fields),
            CURLOPT_HTTPHEADER     => [
                'Authorization: Bearer ' . $this->cfg['secret_key'],
                'Content-Type: application/x-www-form-urlencoded',
            ],
            CURLOPT_TIMEOUT        => 20,
        ]);
        $out  = curl_exec($ch);
        $err  = curl_error($ch);
        curl_close($ch);
        if ($out === false) throw new RuntimeException('Stripe request failed: ' . $err);
        return $out;
    }
}
