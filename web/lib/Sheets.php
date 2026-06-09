<?php
/**
 * Emirard HRM — Google Sheets data layer.
 *
 * Two read paths:
 *   - Sheets API v4 (service account JWT)  → private sheet, read + write
 *   - gviz JSON (published-to-web sheet)   → read only, no credentials
 *
 * The mode is chosen from config: 'auto' uses the API when a service_account.json
 * is present, otherwise falls back to gviz.
 */
class Sheets
{
    private $cfg;
    private $useApi;

    public function __construct(array $cfg)
    {
        $this->cfg = $cfg;
        $mode = $cfg['mode'] ?? 'auto';
        $hasKey = is_file($cfg['sa_keyfile'] ?? '');
        if ($mode === 'api')      $this->useApi = true;
        elseif ($mode === 'gviz') $this->useApi = false;
        else                      $this->useApi = $hasKey;   // auto
    }

    public function mode(): string { return $this->useApi ? 'api' : 'gviz'; }

    public function sheetConfigured(): bool
    {
        $id = $this->cfg['sheet_id'] ?? '';
        return $id && $id !== 'PUT_YOUR_SHEET_ID_HERE';
    }

    /* ---------------- public reads ---------------- */

    /** Return tab rows as a list of associative arrays (header-mapped). */
    public function rows(string $tab): array
    {
        $cached = $this->cacheGet($tab);
        if ($cached !== null) return $cached;

        $rows = $this->useApi ? $this->apiRows($tab) : $this->gvizRows($tab);
        $this->cacheSet($tab, $rows);
        return $rows;
    }

    /* ---------------- public writes (API mode only) ---------------- */

    /** Append one row (ordered values) to a tab. Returns true on success. */
    public function append(string $tab, array $values): bool
    {
        if (!$this->useApi) {
            throw new RuntimeException('Writes require Sheets API mode (service_account.json).');
        }
        $id = $this->cfg['sheet_id'];
        $url = "https://sheets.googleapis.com/v4/spreadsheets/$id/values/"
             . rawurlencode($tab) . ":append?valueInputOption=RAW&insertDataOption=INSERT_ROWS";
        $body = json_encode(['values' => [array_values($values)]]);
        $resp = $this->http('POST', $url, $body, [
            'Authorization: Bearer ' . $this->accessToken(),
            'Content-Type: application/json',
        ]);
        $this->cacheBust($tab);
        return $resp !== null;
    }

    /* ---------------- gviz path ---------------- */

    private function gvizRows(string $tab): array
    {
        $id = $this->cfg['sheet_id'];
        $url = "https://docs.google.com/spreadsheets/d/$id/gviz/tq?tqx=out:json&sheet="
             . rawurlencode($tab);
        $txt = $this->http('GET', $url);
        if ($txt === null) return [];
        $s = strpos($txt, '{');
        $e = strrpos($txt, '}');
        if ($s === false || $e === false) return [];
        $json = json_decode(substr($txt, $s, $e - $s + 1), true);
        if (!$json || empty($json['table'])) return [];
        $cols = array_map(function ($c) {
            return !empty($c['label']) ? $c['label'] : ($c['id'] ?? '');
        }, $json['table']['cols']);
        $out = [];
        foreach ($json['table']['rows'] as $r) {
            $row = [];
            foreach (($r['c'] ?? []) as $i => $cell) {
                $row[$cols[$i] ?? "c$i"] = $cell['v'] ?? null;
            }
            $out[] = $row;
        }
        return $out;
    }

    /* ---------------- Sheets API path ---------------- */

    private function apiRows(string $tab): array
    {
        $id = $this->cfg['sheet_id'];
        $url = "https://sheets.googleapis.com/v4/spreadsheets/$id/values/" . rawurlencode($tab);
        $txt = $this->http('GET', $url, null, [
            'Authorization: Bearer ' . $this->accessToken(),
        ]);
        if ($txt === null) return [];
        $json = json_decode($txt, true);
        $values = $json['values'] ?? [];
        if (count($values) < 1) return [];
        $header = $values[0];
        $out = [];
        for ($i = 1; $i < count($values); $i++) {
            $row = [];
            foreach ($header as $j => $name) {
                $row[$name] = $values[$i][$j] ?? null;
            }
            $out[] = $row;
        }
        return $out;
    }

    private function accessToken(): string
    {
        $cacheFile = sys_get_temp_dir() . '/emirard_hrm_token.json';
        if (is_file($cacheFile)) {
            $t = json_decode(file_get_contents($cacheFile), true);
            if ($t && ($t['exp'] ?? 0) > time() + 60) return $t['token'];
        }
        $sa = json_decode(file_get_contents($this->cfg['sa_keyfile']), true);
        if (!$sa || empty($sa['client_email']) || empty($sa['private_key'])) {
            throw new RuntimeException('Invalid service_account.json');
        }
        $now = time();
        $header = $this->b64(json_encode(['alg' => 'RS256', 'typ' => 'JWT']));
        $claim = $this->b64(json_encode([
            'iss'   => $sa['client_email'],
            'scope' => 'https://www.googleapis.com/auth/spreadsheets',
            'aud'   => 'https://oauth2.googleapis.com/token',
            'iat'   => $now,
            'exp'   => $now + 3600,
        ]));
        $sig = '';
        openssl_sign("$header.$claim", $sig, $sa['private_key'], 'sha256');
        $jwt = "$header.$claim." . $this->b64($sig);
        $resp = $this->http('POST', 'https://oauth2.googleapis.com/token', http_build_query([
            'grant_type' => 'urn:ietf:params:oauth:grant-type:jwt-bearer',
            'assertion'  => $jwt,
        ]), ['Content-Type: application/x-www-form-urlencoded']);
        $tok = json_decode($resp ?? '', true);
        if (empty($tok['access_token'])) {
            throw new RuntimeException('OAuth token request failed');
        }
        @file_put_contents($cacheFile, json_encode([
            'token' => $tok['access_token'],
            'exp'   => $now + (int)($tok['expires_in'] ?? 3600),
        ]));
        return $tok['access_token'];
    }

    private function b64(string $s): string
    {
        return rtrim(strtr(base64_encode($s), '+/', '-_'), '=');
    }

    /* ---------------- HTTP ---------------- */

    private function http(string $method, string $url, ?string $body = null, array $headers = []): ?string
    {
        if (function_exists('curl_init')) {
            $ch = curl_init($url);
            curl_setopt_array($ch, [
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_CUSTOMREQUEST  => $method,
                CURLOPT_HTTPHEADER     => $headers,
                CURLOPT_TIMEOUT        => 15,
                CURLOPT_FOLLOWLOCATION => true,
            ]);
            if ($body !== null) curl_setopt($ch, CURLOPT_POSTFIELDS, $body);
            $out = curl_exec($ch);
            $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
            curl_close($ch);
            return ($out !== false && $code < 400) ? $out : null;
        }
        // fallback: stream context
        $opts = ['http' => [
            'method'  => $method,
            'header'  => implode("\r\n", $headers),
            'content' => $body,
            'timeout' => 15,
            'ignore_errors' => true,
        ]];
        $out = @file_get_contents($url, false, stream_context_create($opts));
        return $out === false ? null : $out;
    }

    /* ---------------- tiny file cache ---------------- */

    private function cacheFile(string $tab): string
    {
        return sys_get_temp_dir() . '/emirard_hrm_' . preg_replace('/\W+/', '_', $tab) . '.json';
    }
    private function cacheGet(string $tab)
    {
        $ttl = (int)($this->cfg['cache_ttl'] ?? 0);
        if ($ttl <= 0) return null;
        $f = $this->cacheFile($tab);
        if (is_file($f) && (time() - filemtime($f)) < $ttl) {
            return json_decode(file_get_contents($f), true);
        }
        return null;
    }
    private function cacheSet(string $tab, array $rows): void
    {
        @file_put_contents($this->cacheFile($tab), json_encode($rows));
    }
    private function cacheBust(string $tab): void
    {
        @unlink($this->cacheFile($tab));
    }
}
