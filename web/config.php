<?php
// Emirard HRM web service config.
// Edit these or set the equivalent environment variables.
return [
    // Google Sheet ID (the /d/<ID>/edit part of the URL)
    'sheet_id'   => getenv('HRM_SHEET_ID') ?: '1WprXIaGWSmirAiFm6Ql9y0OBS8D2MA57NPErcnaSBiA',

    // Data mode:
    //   'auto' = use Sheets API if service_account.json exists, else gviz
    //   'api'  = force Google Sheets API (private sheet, read + write)
    //   'gviz' = force gviz (sheet must be "Published to web", read-only)
    'mode'       => getenv('HRM_MODE') ?: 'gviz',

    // Service account JSON key (for 'api' mode, enables writes & private read)
    'sa_keyfile' => getenv('GOOGLE_SA_KEYFILE') ?: __DIR__ . '/service_account.json',

    // Seconds to cache reads (reduces API calls)
    'cache_ttl'  => 30,

    // Optional shared secret required for write endpoints (?key=...). Empty = no writes via web.
    'write_key'  => getenv('HRM_WRITE_KEY') ?: '',

    // Stripe subscription billing
    'stripe' => [
        'secret_key'      => getenv('STRIPE_SECRET_KEY')      ?: '',   // sk_live_... or sk_test_...
        'publishable_key' => getenv('STRIPE_PUBLISHABLE_KEY') ?: '',   // pk_live_... or pk_test_...
        'webhook_secret'  => getenv('STRIPE_WEBHOOK_SECRET')  ?: '',   // whsec_...
        // Stripe Dashboard → Products → create 3 recurring prices, paste their IDs:
        'prices' => [
            'starter'    => getenv('STRIPE_PRICE_STARTER')    ?: '',   // price_...
            'pro'        => getenv('STRIPE_PRICE_PRO')        ?: '',
            'enterprise' => getenv('STRIPE_PRICE_ENTERPRISE') ?: '',
        ],
        // Public base URL of this site (for redirect after checkout)
        'site_url' => getenv('SITE_URL') ?: '',
    ],
];
