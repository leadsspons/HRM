<?php
/**
 * Emirard HRM — JSON API.
 *
 * Reads:
 *   GET  api.php?action=health
 *   GET  api.php?action=rows&tab=Tasks|Quarter|Points|Members|Groups|Activity|Votes
 * Writes (Sheets API mode + write_key):
 *   POST api.php?action=register_group   {name, invite_url, bot_token}
 *   POST api.php?action=register_member  {username, display_name, team}
 */
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');

$cfg = require __DIR__ . '/config.php';
require __DIR__ . '/lib/Sheets.php';

function out($data, int $code = 200): void
{
    http_response_code($code);
    echo json_encode($data, JSON_UNESCAPED_UNICODE);
    exit;
}

$ALLOWED_TABS = ['Tasks', 'Members', 'Groups', 'Points', 'Quarter', 'Activity', 'Votes'];
$action = $_GET['action'] ?? 'health';

try {
    $sheets = new Sheets($cfg);

    if ($action === 'health') {
        out(['ok' => true, 'mode' => $sheets->mode(),
             'sheet_configured' => $sheets->sheetConfigured()]);
    }

    if ($action === 'rows') {
        $tab = $_GET['tab'] ?? '';
        if (!in_array($tab, $ALLOWED_TABS, true)) {
            out(['ok' => false, 'error' => 'unknown tab'], 400);
        }
        if (!$sheets->sheetConfigured()) {
            out(['ok' => false, 'error' => 'sheet not configured'], 503);
        }
        $rows = $sheets->rows($tab);
        out(['ok' => true, 'tab' => $tab, 'count' => count($rows), 'rows' => $rows]);
    }

    // ---- writes ----
    if ($action === 'register_group' || $action === 'register_member') {
        if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
            out(['ok' => false, 'error' => 'POST required'], 405);
        }
        $writeKey = $cfg['write_key'] ?? '';
        $given = $_GET['key'] ?? ($_SERVER['HTTP_X_WRITE_KEY'] ?? '');
        if ($writeKey === '' || !hash_equals($writeKey, (string)$given)) {
            out(['ok' => false, 'error' => 'writes disabled or bad key'], 403);
        }
        $in = json_decode(file_get_contents('php://input'), true) ?: [];

        if ($action === 'register_group') {
            $name = trim($in['name'] ?? '');
            if ($name === '') out(['ok' => false, 'error' => 'name required'], 400);
            // Groups: name, invite_url, chat_id, bot_token, active, added_at
            $sheets->append('Groups', [
                $name, $in['invite_url'] ?? '', '', $in['bot_token'] ?? '',
                'TRUE', date('c'),
            ]);
            out(['ok' => true, 'registered' => 'group', 'name' => $name]);
        } else {
            $u = ltrim(trim($in['username'] ?? ''), '@');
            if ($u === '') out(['ok' => false, 'error' => 'username required'], 400);
            // Members: user_id, username, display_name, team, active
            $sheets->append('Members', [
                $u, $u, $in['display_name'] ?? '', $in['team'] ?? '', 'TRUE',
            ]);
            out(['ok' => true, 'registered' => 'member', 'username' => $u]);
        }
    }

    out(['ok' => false, 'error' => 'unknown action'], 400);

} catch (Throwable $e) {
    out(['ok' => false, 'error' => $e->getMessage()], 500);
}
