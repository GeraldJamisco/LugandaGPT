<?php
declare(strict_types=1);

session_name('lugandagpt_studio_php');
session_start();

$config = require __DIR__ . '/config.php';
$DB_PATH = $config['db_path'];
if (!is_file($DB_PATH)) {
    http_response_code(503);
    echo "<!doctype html><title>Translation Studio setup</title><main style='max-width:720px;margin:4rem auto;font-family:Segoe UI,Arial,sans-serif'><h1>Database not found</h1><p>Upload the Translation Studio SQLite database and set <code>db_path</code> in <code>php/config.php</code>.</p><p>Expected path: <code>" . htmlspecialchars($DB_PATH, ENT_QUOTES, 'UTF-8') . "</code></p></main>";
    exit;
}

try {
    $pdo = new PDO('sqlite:' . $DB_PATH);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
    $pdo->exec('PRAGMA foreign_keys = ON');
    $pdo->exec("CREATE TABLE IF NOT EXISTS reward_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipient_id INTEGER NOT NULL REFERENCES users(id),
        recipient_role TEXT NOT NULL CHECK (recipient_role IN ('translator','reviewer')),
        amount_usd REAL NOT NULL CHECK (amount_usd > 0),
        work_count INTEGER NOT NULL DEFAULT 0,
        note TEXT NOT NULL DEFAULT '',
        paid_at TEXT NOT NULL,
        created_by INTEGER REFERENCES users(id),
        created_at TEXT NOT NULL
    )");
} catch (Throwable $error) {
    http_response_code(500);
    echo "<h1>Database error</h1><p>The studio could not open the database.</p>";
    exit;
}

$CAPABILITIES = [
    'formal_comprehension' => 'Reading and understanding',
    'formal_generation' => 'Writing in Luganda',
    'rewriting_formal_luganda' => 'Making an English passage more formal',
    'question_answering' => 'Answering a question',
    'instruction_following' => 'Following instructions',
    'short_conversation' => 'Understanding a conversation',
];
$PURPOSES = [
    'formal_comprehension' => 'Read the English passage and answer or summarize it using only the information provided.',
    'formal_generation' => 'Write clear Luganda that meets the instruction and uses the right level of formality.',
    'rewriting_formal_luganda' => 'Keep the meaning while making the Luganda clearer and more formal.',
    'question_answering' => 'Answer the question in Luganda. If the information is missing, say so instead of guessing.',
    'instruction_following' => 'Follow every instruction, including language, length, format, tone, and content.',
    'short_conversation' => 'Use the earlier turns to answer the final turn naturally and consistently.',
];
$STATUS = [
    'not_started' => 'Not started',
    'in_progress' => 'In progress',
    'ready_for_review' => 'Ready for review',
    'needs_revision' => 'Returned for correction',
    'under_dispute' => 'Needs owner resolution',
    'reviewed' => 'Reviewed',
    'not_ready' => 'Not ready for dataset',
    'approved_for_dataset' => 'Approved for dataset preparation',
];
$DECISIONS = ['approved' => 'Approved', 'needs_revision' => 'Needs revision', 'cannot_assess' => 'Cannot assess yet'];
$ROLES = ['admin' => 'Administrator', 'translator' => 'Translator', 'reviewer' => 'Reviewer'];

function h(?string $value): string { return htmlspecialchars((string)$value, ENT_QUOTES, 'UTF-8'); }
function now_iso(): string { return gmdate('Y-m-d\TH:i:s+00:00'); }
function format_dt(?string $value, string $fallback = 'Not recorded'): string {
    if (!$value) return $fallback;
    try { return (new DateTime($value))->format('d M Y, H:i'); } catch (Throwable $e) { return $value; }
}
function csrf(): string {
    if (empty($_SESSION['csrf'])) $_SESSION['csrf'] = bin2hex(random_bytes(32));
    return $_SESSION['csrf'];
}
function csrf_field(): string { return '<input type="hidden" name="csrf_token" value="' . h(csrf()) . '">'; }
function verify_csrf(): void {
    if (!hash_equals($_SESSION['csrf'] ?? '', $_POST['csrf_token'] ?? '')) {
        http_response_code(400); echo 'The form expired. Reload the page and try again.'; exit;
    }
}
function redirect(string $url): never { header('Location: ' . $url); exit; }
function flash(string $message): void { $_SESSION['flash'] = $message; }
function take_flash(): ?string { $message = $_SESSION['flash'] ?? null; unset($_SESSION['flash']); return $message; }
function pdo_query(PDO $pdo, string $sql, array $params = []): PDOStatement {
    $statement = $pdo->prepare($sql); $statement->execute($params); return $statement;
}
function db_user(PDO $pdo, int $id): ?array {
    $row = pdo_query($pdo, 'SELECT * FROM users WHERE id = ? AND active = 1', [$id])->fetch();
    return $row ?: null;
}
function current_user(PDO $pdo): ?array {
    return empty($_SESSION['user_id']) ? null : db_user($pdo, (int)$_SESSION['user_id']);
}
function require_role(?array $user, array $roles): void {
    if (!$user || !in_array($user['role'], $roles, true)) { http_response_code(403); echo 'You do not have permission to open this page.'; exit; }
}
function verify_password_php(string $password, string $saltB64, string $hashB64): bool {
    $salt = base64_decode($saltB64, true); if ($salt === false) return false;
    $actual = hash_pbkdf2('sha256', $password, $salt, 310000, 0, true);
    return hash_equals(base64_decode($hashB64, true) ?: '', $actual);
}
function next_public_id(PDO $pdo, string $role): string {
    $prefix = ['admin'=>'A','translator'=>'T','reviewer'=>'R'][$role] ?? 'U';
    $rows = pdo_query($pdo, 'SELECT public_id FROM users WHERE role = ?', [$role])->fetchAll();
    $used = [];
    foreach ($rows as $row) { $parts = explode('-', $row['public_id']); if (isset($parts[1])) $used[(int)$parts[1]] = true; }
    $n = 1; while (isset($used[$n])) $n++;
    return $prefix . '-' . str_pad((string)$n, 3, '0', STR_PAD_LEFT);
}
function create_user_php(PDO $pdo, string $username, string $display, string $role, string $password, ?int $actor): array {
    $username = trim($username); $display = trim($display);
    if (!preg_match('/^[A-Za-z0-9_.-]{3,40}$/', $username)) throw new RuntimeException('Username must be 3 to 40 characters using letters, numbers, dots, dashes, or underscores.');
    if ($display === '' || strlen($display) > 100) throw new RuntimeException('Display name is required and must be at most 100 characters.');
    if (!in_array($role, ['admin','translator','reviewer'], true)) throw new RuntimeException('Choose a valid role.');
    if (strlen($password) < 10) throw new RuntimeException('Password must be at least 10 characters.');
    if (pdo_query($pdo, 'SELECT 1 FROM users WHERE username = ? COLLATE NOCASE', [$username])->fetch()) throw new RuntimeException('That username already exists.');
    $salt = random_bytes(16);
    $hash = hash_pbkdf2('sha256', $password, $salt, 310000, 0, true);
    $public = next_public_id($pdo, $role);
    $now = now_iso();
    pdo_query($pdo, 'INSERT INTO users(username, display_name, public_id, role, password_salt, password_hash, active, created_at) VALUES (?,?,?,?,?,?,1,?)', [$username,$display,$public,$role,base64_encode($salt),base64_encode($hash),$now]);
    $id = (int)$pdo->lastInsertId();
    audit($pdo, $actor, 'user_created', 'user', (string)$id, ['username'=>$username,'role'=>$role,'public_id'=>$public]);
    return ['id'=>$id,'public_id'=>$public];
}
function audit(PDO $pdo, ?int $actor, string $action, string $type, string $id, array $details = []): void {
    pdo_query($pdo, 'INSERT INTO audit_events(actor_id, action, entity_type, entity_id, details_json, created_at) VALUES (?,?,?,?,?,?)', [$actor,$action,$type,$id,json_encode($details, JSON_UNESCAPED_UNICODE),now_iso()]);
}
function source_of(?array $item): array { return $item ? (json_decode($item['source_json'], true) ?: []) : []; }
function item_row(PDO $pdo, string $id): ?array { $row = pdo_query($pdo, 'SELECT * FROM items WHERE item_id = ?', [$id])->fetch(); return $row ?: null; }
function translation_row(PDO $pdo, string $id): ?array { $row = pdo_query($pdo, 'SELECT * FROM translations WHERE item_id = ?', [$id])->fetch(); return $row ?: null; }
function metadata_row(PDO $pdo, string $id): array {
    $row = pdo_query($pdo, 'SELECT * FROM training_metadata WHERE item_id = ?', [$id])->fetch();
    return $row ?: ['dataset_status'=>'not_ready','consent_status'=>'not_recorded','licence_status'=>'unresolved'];
}
function reviews_for(PDO $pdo, string $id, ?int $version = null): array {
    if ($version === null) return pdo_query($pdo, 'SELECT r.*, u.display_name AS reviewer_name, u.public_id AS reviewer_public_id FROM reviews r JOIN users u ON u.id = r.reviewer_id WHERE r.item_id = ? ORDER BY r.translation_version, r.created_at', [$id])->fetchAll();
    return pdo_query($pdo, 'SELECT r.*, u.display_name AS reviewer_name, u.public_id AS reviewer_public_id FROM reviews r JOIN users u ON u.id = r.reviewer_id WHERE r.item_id = ? AND r.translation_version = ? ORDER BY r.created_at', [$id,$version])->fetchAll();
}
function assignment(PDO $pdo, string $id, int $uid, string $type): bool { return (bool)pdo_query($pdo, 'SELECT 1 FROM assignments WHERE item_id = ? AND user_id = ? AND assignment_type = ?', [$id,$uid,$type])->fetch(); }
function progress_counts(PDO $pdo, int $uid, string $role): array {
    if ($role === 'translator') {
        $total = (int)pdo_query($pdo, "SELECT COUNT(*) c FROM assignments WHERE user_id = ? AND assignment_type = 'translation'", [$uid])->fetch()['c'];
        $rows = pdo_query($pdo, "SELECT COALESCE(t.status,'not_started') status, COUNT(*) c FROM assignments a LEFT JOIN translations t ON t.item_id=a.item_id WHERE a.user_id=? AND a.assignment_type='translation' GROUP BY COALESCE(t.status,'not_started')", [$uid])->fetchAll();
        $c = []; foreach ($rows as $r) $c[$r['status']] = (int)$r['c'];
        return ['total'=>$total,'waiting'=>$c['not_started']??0,'saved'=>$c['in_progress']??0,'returned'=>$c['needs_revision']??0,'ready'=>$c['ready_for_review']??0,'reviewed'=>$c['reviewed']??0,'disputed'=>$c['under_dispute']??0];
    }
    $total = (int)pdo_query($pdo, "SELECT COUNT(*) c FROM assignments WHERE user_id=? AND assignment_type='review'", [$uid])->fetch()['c'];
    $completed = (int)pdo_query($pdo, 'SELECT COUNT(DISTINCT r.item_id) c FROM reviews r JOIN translations t ON t.item_id=r.item_id AND t.version=r.translation_version WHERE r.reviewer_id=?', [$uid])->fetch()['c'];
    $pending = (int)pdo_query($pdo, "SELECT COUNT(*) c FROM assignments a JOIN translations t ON t.item_id=a.item_id WHERE a.user_id=? AND a.assignment_type='review' AND t.status='ready_for_review' AND NOT EXISTS (SELECT 1 FROM reviews r WHERE r.item_id=a.item_id AND r.reviewer_id=a.user_id AND r.translation_version=t.version)", [$uid])->fetch()['c'];
    return ['total'=>$total,'waiting'=>$pending,'completed'=>$completed];
}
function payment_history(PDO $pdo, int $uid, string $role): array {
    return pdo_query($pdo, 'SELECT * FROM reward_payments WHERE recipient_id=? AND recipient_role=? ORDER BY paid_at DESC, id DESC', [$uid,$role])->fetchAll();
}
function is_reward_eligible(PDO $pdo, string $id): bool {
    $t = translation_row($pdo, $id);
    if (!$t || $t['status'] !== 'reviewed' || (int)$t['resolution_required'] !== 0) return false;
    $v = (int)$t['version'];
    if (!pdo_query($pdo, 'SELECT 1 FROM translation_versions WHERE item_id=? AND version=?', [$id,$v])->fetch()) return false;
    $reviews = reviews_for($pdo, $id, $v);
    if (!$reviews) return false;
    $approved = false; $needs = false; $submitted = [];
    foreach ($reviews as $r) { $submitted[(int)$r['reviewer_id']] = true; if ($r['decision']==='approved') $approved=true; if ($r['decision']==='needs_revision') $needs=true; }
    if (!$approved) return false;
    $resolution = pdo_query($pdo, 'SELECT decision FROM resolutions WHERE item_id=? AND translation_version=? ORDER BY created_at DESC LIMIT 1', [$id,$v])->fetch();
    if ($needs && !($resolution && $resolution['decision']==='approved')) return false;
    $assigned = pdo_query($pdo, "SELECT user_id FROM assignments WHERE item_id=? AND assignment_type='review'", [$id])->fetchAll();
    foreach ($assigned as $a) { if (empty($submitted[(int)$a['user_id']])) return false; }
    return true;
}
function reward_summary(int $count): array {
    $accrued = round($count * 0.20, 2); $blocks = intdiv($count,10); $rem = $count % 10;
    return ['approved_count'=>$count,'per_approved_usd'=>0.20,'accrued_usd'=>$accrued,'payout_ready_usd'=>round($blocks*2,2),'block_size'=>10,'block_usd'=>2.0,'remainder'=>$rem,'next_needed'=>$count?10-$rem:10,'progress_percent'=>($count && $rem===0)?100:$rem*10];
}
function translator_reward(PDO $pdo, int $uid): array {
    $rows = pdo_query($pdo, 'SELECT item_id FROM translations WHERE translator_id=? ORDER BY updated_at', [$uid])->fetchAll();
    $items = [];
    foreach ($rows as $row) { if (is_reward_eligible($pdo,$row['item_id'])) { $items[]=$row['item_id']; } }
    $summary = reward_summary(count($items));
    $payments = payment_history($pdo, $uid, 'translator');
    $paid = round(array_sum(array_column($payments,'amount_usd')),2);
    $summary['kind']='translator'; $summary['approved_items']=$items; $summary['payments']=$payments; $summary['paid_usd']=$paid; $summary['available_usd']=round(max(0,$summary['accrued_usd']-$paid),2);
    return $summary;
}
function reviewer_reward(PDO $pdo, int $uid): array {
    $reviews = pdo_query($pdo, 'SELECT r.*, i.source_json FROM reviews r JOIN items i ON i.item_id=r.item_id WHERE r.reviewer_id=? ORDER BY r.created_at DESC, r.id DESC', [$uid])->fetchAll();
    $count = count($reviews); $accrued = round($count*0.10,2);
    $payments = payment_history($pdo,$uid,'reviewer'); $paid=round(array_sum(array_column($payments,'amount_usd')),2);
    return ['kind'=>'reviewer','review_count'=>$count,'per_review_usd'=>0.10,'accrued_usd'=>$accrued,'payout_ready_usd'=>$accrued,'paid_usd'=>$paid,'available_usd'=>round(max(0,$accrued-$paid),2),'payments'=>$payments,'reviews'=>$reviews];
}
function all_payables(PDO $pdo): array {
    $rows = pdo_query($pdo, "SELECT id, display_name, public_id, role FROM users WHERE role IN ('translator','reviewer') AND active=1 ORDER BY role, display_name")->fetchAll();
    $out=[];
    foreach ($rows as $row) { $reward = $row['role']==='translator' ? translator_reward($pdo,(int)$row['id']) : reviewer_reward($pdo,(int)$row['id']); $out[]=['user_id'=>(int)$row['id'],'display_name'=>$row['display_name'],'public_id'=>$row['public_id'],'role'=>$row['role'],'work_count'=>$reward['approved_count']??$reward['review_count']??0,'accrued_usd'=>$reward['accrued_usd'],'paid_usd'=>$reward['paid_usd'],'available_usd'=>$reward['available_usd'],'payments'=>$reward['payments']]; }
    return $out;
}
function record_payment_php(PDO $pdo, int $recipientId, string $role, float $amount, string $note, int $adminId): void {
    $recipient = db_user($pdo,$recipientId);
    if (!$recipient || $recipient['role'] !== $role) throw new RuntimeException('The selected account does not match that reward role.');
    $reward = $role==='translator' ? translator_reward($pdo,$recipientId) : reviewer_reward($pdo,$recipientId);
    $available = (float)$reward['available_usd'];
    if ($amount <= 0 || $amount > $available + 0.005) throw new RuntimeException('Payment cannot exceed the available amount.');
    $note = trim($note); if ($note === '') throw new RuntimeException('Add a payment note or reference.');
    $now = now_iso();
    pdo_query($pdo, 'INSERT INTO reward_payments(recipient_id,recipient_role,amount_usd,work_count,note,paid_at,created_by,created_at) VALUES (?,?,?,?,?,?,?,?)', [$recipientId,$role,$amount,$reward['approved_count']??$reward['review_count']??0,$note,$now,$adminId,$now]);
    audit($pdo,$adminId,'reward_payment_cleared','user',(string)$recipientId,['role'=>$role,'amount_usd'=>$amount,'note'=>$note]);
}
function save_translation_php(PDO $pdo, string $itemId, int $uid, string $context, array $turns, string $prompt, string $response, string $notes, bool $submit): array {
    $item = item_row($pdo,$itemId); if (!$item) throw new RuntimeException('Example not found.');
    if (!assignment($pdo,$itemId,$uid,'translation')) throw new RuntimeException('You are not assigned to translate this example.');
    $source = source_of($item); $existing = translation_row($pdo,$itemId);
    if ($existing && (int)$existing['translator_id'] !== $uid) throw new RuntimeException('This translation belongs to another translator.');
    if ($existing && in_array($existing['status'], ['ready_for_review','under_dispute','reviewed'], true)) throw new RuntimeException('This translation is locked because it is already submitted or reviewed.');
    $meta = metadata_row($pdo,$itemId); if (($meta['dataset_status']??'not_ready')==='approved_for_dataset') throw new RuntimeException('Ask an administrator to revoke dataset approval before editing.');
    if ($submit) {
        if ($source['source_context'] && trim($context)==='') throw new RuntimeException('Translate the background passage before submitting.');
        if (trim($prompt)==='' || trim($response)==='') throw new RuntimeException('Complete the user message and assistant reply before submitting.');
        if (count($turns)!==count($source['conversation_turns']??[])) throw new RuntimeException('Complete every earlier conversation turn.');
        foreach ($turns as $turn) if (trim($turn)==='') throw new RuntimeException('Complete every earlier conversation turn.');
    }
    $now=now_iso(); $version=$existing?(int)$existing['version']:1; $submitted=$existing['submitted_at']??null; $created=$existing['created_at']??$now; $prev=$existing['status']??'not_started';
    if ($submit) { if ($prev==='needs_revision' || $submitted) $version++; $status='ready_for_review'; $submitted=$now; } else { $status='in_progress'; }
    $turnsJson=json_encode(array_values($turns), JSON_UNESCAPED_UNICODE);
    if ($existing) pdo_query($pdo,'UPDATE translations SET context_lg=?,turns_lg=?,prompt_lg=?,response_lg=?,notes=?,status=?,version=?,resolution_required=0,resolution_reason=?,updated_at=?,submitted_at=? WHERE item_id=?',[$context,$turnsJson,$prompt,$response,$notes,$status,$version,'',$now,$submitted,$itemId]);
    else pdo_query($pdo,'INSERT INTO translations(item_id,translator_id,context_lg,turns_lg,prompt_lg,response_lg,notes,status,version,resolution_required,resolution_reason,created_at,updated_at,submitted_at) VALUES (?,?,?,?,?,?,?,?,?,0,\'\',?,?,?)',[$itemId,$uid,$context,$turnsJson,$prompt,$response,$notes,$status,$version,$created,$now,$submitted]);
    if ($submit) pdo_query($pdo,'INSERT INTO translation_versions(item_id,version,translator_id,context_lg,turns_lg,prompt_lg,response_lg,notes,submitted_at) VALUES (?,?,?,?,?,?,?,?,?)',[$itemId,$version,$uid,$context,$turnsJson,$prompt,$response,$notes,$now]);
    audit($pdo,$uid,$submit?'translation_submitted':'translation_saved','item',$itemId,['status'=>$status,'version'=>$version]);
    return translation_row($pdo,$itemId);
}
function refresh_review_state_php(PDO $pdo, string $itemId, int $version): string {
    $reviews = reviews_for($pdo,$itemId,$version); $hasA=false; $hasN=false;
    foreach ($reviews as $r) { if ($r['decision']==='approved') $hasA=true; if ($r['decision']==='needs_revision') $hasN=true; }
    $status='ready_for_review'; $rr=0; $reason='';
    if ($hasA && $hasN) { $status='under_dispute'; $rr=1; $reason='Two reviewers disagree. An administrator must resolve the record.'; }
    elseif ($hasN) $status='needs_revision'; elseif ($hasA) $status='reviewed';
    pdo_query($pdo,'UPDATE translations SET status=?,resolution_required=?,resolution_reason=?,updated_at=? WHERE item_id=? AND version=?',[$status,$rr,$reason,now_iso(),$itemId,$version]);
    return $status;
}
function submit_review_php(PDO $pdo, string $itemId, int $reviewerId, string $decision, string $comments, string $suggestion): void {
    if (!in_array($decision,['approved','needs_revision','cannot_assess'],true)) throw new RuntimeException('Choose a valid review decision.');
    if (!assignment($pdo,$itemId,$reviewerId,'review')) throw new RuntimeException('You are not assigned to review this example.');
    $t=translation_row($pdo,$itemId); if(!$t) throw new RuntimeException('There is no translation to review.');
    if ((int)$t['translator_id']===$reviewerId) throw new RuntimeException('You cannot review your own translation.');
    if (!in_array($t['status'],['ready_for_review','reviewed'],true)) throw new RuntimeException('This translation is not waiting for review.');
    if ($decision!=='approved' && trim($comments)==='') throw new RuntimeException('Explain your decision in the comments field.');
    $source=source_of(item_row($pdo,$itemId));
    if ($decision==='approved' && ($source['source_context']??null) && trim($t['context_lg'])==='') throw new RuntimeException('You cannot approve a translation with a missing background passage. Request revision.');
    if ($decision==='approved' && (trim($t['prompt_lg'])==='' || trim($t['response_lg'])==='')) throw new RuntimeException('You cannot approve a translation with missing messages. Request revision.');
    $version=(int)$t['version'];
    if (pdo_query($pdo,'SELECT 1 FROM reviews WHERE item_id=? AND reviewer_id=? AND translation_version=?',[$itemId,$reviewerId,$version])->fetch()) throw new RuntimeException('You have already reviewed this version.');
    pdo_query($pdo,'INSERT INTO reviews(item_id,reviewer_id,translation_version,decision,comments,suggested_correction,created_at) VALUES (?,?,?,?,?,?,?)',[$itemId,$reviewerId,$version,$decision,$comments,$suggestion,now_iso()]);
    refresh_review_state_php($pdo,$itemId,$version);
    audit($pdo,$reviewerId,'review_submitted','item',$itemId,['decision'=>$decision,'version'=>$version]);
}
function label(array $map, ?string $value): string { return $map[$value ?? ''] ?? (string)$value; }
function nav(string $current, ?array $user): string {
    if (!$user) return '';
    $out='<nav class="nav"><a href="index.php?page=home" class="'.($current==='home'?'active':'').'">Welcome</a>';
    if ($user['role']==='translator') { $out.='<a href="index.php?page=work" class="'.($current==='work'?'active':'').'">My work</a><a href="index.php?page=progress" class="'.($current==='progress'?'active':'').'">My progress</a><a href="index.php?page=rewards" class="'.($current==='rewards'?'active':'').'">Rewards</a>'; }
    if (in_array($user['role'],['reviewer','admin'],true)) $out.='<a href="index.php?page=review" class="'.($current==='review'?'active':'').'">Review</a>';
    if ($user['role']==='reviewer') $out.='<a href="index.php?page=rewards" class="'.($current==='rewards'?'active':'').'">Rewards</a>';
    if ($user['role']==='admin') $out.='<a href="index.php?page=admin" class="'.($current==='admin'?'active':'').'">Admin</a>';
    $out.='<span class="user-chip">'.h($user['display_name']).'</span><form method="post" action="index.php?page=logout" class="inline-form">'.csrf_field().'<button class="btn btn-quiet btn-small" type="submit">Sign out</button></form></nav>';
    return $out;
}
function layout(string $title, string $body, ?array $user, string $current=''): string {
    $flash = take_flash();
    $bodyClass = 'page-content';
    if ($current === 'login') {
        $bodyClass = 'page-login';
    } elseif ($current === 'home') {
        $bodyClass = (($user['role'] ?? '') === 'admin') ? 'page-admin-dashboard' : 'page-dashboard';
    } elseif (in_array($current, ['work', 'review'], true)) {
        $bodyClass = 'page-workspace';
    } elseif ($current === 'admin') {
        $bodyClass = 'page-admin';
    }
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="icon" type="image/svg+xml" href="assets/favicon.svg"><title>'.h($title).' | LugandaGPT Translation Studio</title><link rel="stylesheet" href="assets/studio.css?v=20261024b"></head><body class="'.h($bodyClass).'"><a class="skip-link" href="#main">Skip to main content</a><header class="site-header"><div class="header-inner"><a class="brand" href="index.php?page='.($user?'home':'login').'"><span class="brand-mark">L</span><span>LugandaGPT<small>Translation Studio</small></span></a>'.nav($current,$user).'</div></header><main id="main" class="shell">'.($flash?'<div class="notice" role="status">'.h($flash).'</div>':'').$body.'</main><footer class="footer"><p>Local project workspace. Do not share sign-in details.</p><p>LugandaGPT is early-stage research. Reviewed work is not training approval.</p></footer><script src="assets/studio.js?v=20261024b" defer></script></body></html>';
}
function error_box(string $message): string { return '<div class="error-box"><strong>'.h($message).'</strong></div>'; }
function capability_label_php(string $c): string { global $CAPABILITIES; return $CAPABILITIES[$c] ?? $c; }
function status_label_php(?string $s): string { global $STATUS; return $STATUS[$s ?? ''] ?? (string)$s; }
function decision_label_php(?string $s): string { global $DECISIONS; return $DECISIONS[$s ?? ''] ?? (string)$s; }
function role_label_php(?string $s): string { global $ROLES; return $ROLES[$s ?? ''] ?? (string)$s; }

function page_login(?array $user, string $error = '', string $username = ''): void
{
    if ($user) redirect('index.php?page=home');
    $body = '<div class="login-page"><section class="login-brand-panel"><div><p class="eyebrow" style="color:#d9eee2">Private workspace</p><h1>Translation Studio</h1><p>We are building an AI assistant that understands and communicates naturally in Luganda. Your language work is the part that makes that possible.</p></div><div class="login-points"><div class="login-point"><span>1</span><p>Read the English source and its context.</p><br><p>Soma oluzungu nga bwelugabidwa n\'amakulu galwo</p></div><div class="login-point"><span>2</span><p>Write a natural Luganda translation and save it safely.</p><br><p>Wandika mu Luganda oluvunuddwa obulunji omale olusevinge</p></div><div class="login-point"><span>3</span><p>A second speaker reviews the work independently.</p></div></div><p class="login-note">Project work stays in this local workspace. No translation is sent to an external AI service.</p></section><section class="login-form-panel"><div class="card login-card"><p class="eyebrow">Sign in</p><h2>Welcome back</h2><p class="muted">Use the account Gerald created for you. There is no public registration.</p>' . ($error ? error_box($error) : '') . '<form method="post" action="index.php?page=login">' . csrf_field() . '<div class="field"><label for="username">Username</label><input id="username" name="username" value="' . h($username) . '" autocomplete="username" autocapitalize="none" required></div><div class="field"><label for="password">Password</label><input id="password" name="password" type="password" autocomplete="current-password" required></div><button class="btn btn-primary btn-wide" type="submit">Sign in</button></form></div></section></div>';
    echo layout('Sign in', $body, null, 'login');
}

function page_home(PDO $pdo, array $user): void
{
    global $STATUS;
    $html = '';
    if ($user['role'] === 'translator') {
        $c = progress_counts($pdo, (int)$user['id'], 'translator');
        $r = translator_reward($pdo, (int)$user['id']);
        $next = pdo_query($pdo, "SELECT a.item_id FROM assignments a LEFT JOIN translations t ON t.item_id=a.item_id WHERE a.user_id=? AND a.assignment_type='translation' AND COALESCE(t.status,'not_started') IN ('not_started','in_progress','needs_revision') ORDER BY a.item_id LIMIT 1", [(int)$user['id']])->fetch();
        $html .= '<section class="hero"><div class="hero-grid"><div><p class="eyebrow">LugandaGPT Translation Studio</p><h1>Welcome to LugandaGPT Translation Studio.</h1><p>We are building an AI assistant designed to understand and communicate naturally in Luganda. Your work helps us prepare and check examples that teach the system how to use the language correctly.</p><p>You will read an example in English, write its Luganda version, and save your work. Another speaker may review the translation to help us improve its accuracy and naturalness.</p><div class="button-row"><a class="btn btn-gold" href="' . ($next ? 'index.php?page=work_item&amp;item=' . h($next['item_id']) : 'index.php?page=work') . '">Start translating</a><a class="btn btn-secondary" href="index.php?page=work">Continue my work</a><a class="hero-link" href="index.php?page=progress">View my progress</a></div></div><aside class="hero-flow"><p class="eyebrow">How your work moves</p><div class="flow-step"><span>1</span><p>Read the English example and its context.</p></div><div class="flow-step"><span>2</span><p>Write the Luganda version and save it safely.</p></div><div class="flow-step"><span>3</span><p>A second speaker reviews it independently.</p></div><div class="flow-step"><span>4</span><p>You can see feedback and correct your work if needed.</p></div></aside></div></section>';
        $html .= '<h2>Your work at a glance</h2><div class="grid grid-4"><div class="progress-card"><strong>' . $c['waiting'] . '</strong><span>Waiting to be translated</span></div><div class="progress-card"><strong>' . $c['saved'] . '</strong><span>Saved translations</span></div><div class="progress-card"><strong>' . $c['returned'] . '</strong><span>Returned for correction</span></div><div class="progress-card"><strong>' . $c['ready'] . '</strong><span>Ready for review</span></div></div>';
        $html .= '<div class="reward-panel" style="margin-top:1rem"><div><p class="eyebrow">Your approved work reward</p><div class="reward-amount">$' . number_format((float)$r['available_usd'], 2) . '</div><p><strong>' . $r['approved_count'] . '</strong> approved translation' . ($r['approved_count'] === 1 ? '' : 's') . '. Each approved translation adds $0.20. Total cleared: $' . number_format((float)$r['paid_usd'], 2) . '.</p><div class="reward-track"><span style="width:' . $r['progress_percent'] . '%"></span></div><p class="small muted">' . $r['next_needed'] . ' more approved translation' . ($r['next_needed'] === 1 ? '' : 's') . ' to reach the next $2 reward.</p></div><div class="reward-note"><p class="eyebrow">How this works</p><p>Only translations approved by review count. Drafts and returned work do not count until approved.</p><a class="btn btn-secondary btn-small" href="index.php?page=rewards">See my rewards</a><p class="small muted" style="margin-top:.7rem">Payment is recorded separately by the project owner.</p></div></div>';
        $html .= '<div class="card" style="margin-top:1rem"><h2>What to do next</h2>' . ($next ? '<p>Continue with the next example in your assigned work.</p><a class="btn btn-primary" href="index.php?page=work_item&amp;item=' . h($next['item_id']) . '">Open the next example</a>' : '<p>No unfinished example right now. Check your progress or wait for review feedback.</p><a class="btn btn-secondary" href="index.php?page=progress">View my progress</a>') . '</div>';
    } elseif ($user['role'] === 'reviewer') {
        $c = progress_counts($pdo, (int)$user['id'], 'reviewer');
        $r = reviewer_reward($pdo, (int)$user['id']);
        $html .= '<section class="hero"><div class="hero-grid"><div><p class="eyebrow">LugandaGPT Translation Studio</p><h1>Welcome to LugandaGPT Translation Studio.</h1><p>Your review helps us check that translations are accurate, natural, and useful.</p><div class="button-row"><a class="btn btn-gold" href="index.php?page=review">Review translations</a><a class="btn btn-secondary" href="index.php?page=rewards">My rewards</a></div></div><aside class="hero-flow"><p class="eyebrow">How your work moves</p><div class="flow-step"><span>1</span><p>Read the English source and the full translation.</p></div><div class="flow-step"><span>2</span><p>Check meaning, register, and every constraint.</p></div><div class="flow-step"><span>3</span><p>Record a clear decision and comments.</p></div><div class="flow-step"><span>4</span><p>The owner resolves disagreements.</p></div></aside></div></section>';
        $html .= '<h2>Your review work at a glance</h2><div class="grid grid-3"><div class="progress-card"><strong>' . $c['waiting'] . '</strong><span>Waiting for your review</span></div><div class="progress-card"><strong>' . $c['completed'] . '</strong><span>Completed reviews</span></div><div class="progress-card"><strong>' . $c['total'] . '</strong><span>Assigned to you</span></div></div>';
        $html .= '<div class="reward-panel" style="margin-top:1rem"><div><p class="eyebrow">Your review reward</p><div class="reward-amount">$' . number_format((float)$r['available_usd'], 2) . '</div><p><strong>' . $r['review_count'] . '</strong> completed review' . ($r['review_count'] === 1 ? '' : 's') . ' at $0.10 each. Available since the last cleared payment.</p><p class="small muted">Total earned: $' . number_format((float)$r['accrued_usd'], 2) . '. Total paid: $' . number_format((float)$r['paid_usd'], 2) . '.</p></div><div class="reward-note"><p class="eyebrow">Payment</p>' . ($r['payments'] ? '<p><span class="badge badge-green">Payment cleared</span></p>' : '<p>No payment has been cleared yet.</p>') . '<a class="btn btn-secondary btn-small" href="index.php?page=rewards">See my rewards</a></div></div>';
        $html .= '<div class="card" style="margin-top:1rem"><h2>How review works</h2><p>Open an assigned translation, compare it with the English source, and record a decision. You can approve it, ask for revision, or say that you cannot assess it yet. Your comments are kept in the review history.</p><a class="btn btn-primary" href="index.php?page=review">Open review work</a></div>';
    } else {
        $items = (int)pdo_query($pdo, 'SELECT COUNT(*) c FROM items')->fetch()['c'];
        $pilot = (int)pdo_query($pdo, "SELECT COUNT(*) c FROM items WHERE collection='pilot'")->fetch()['c'];
        $eval = (int)pdo_query($pdo, "SELECT COUNT(*) c FROM items WHERE collection='evaluation'")->fetch()['c'];
        $ready = (int)pdo_query($pdo, "SELECT COUNT(*) c FROM translations WHERE status='ready_for_review'")->fetch()['c'];
        $reviewed = (int)pdo_query($pdo, "SELECT COUNT(*) c FROM translations WHERE status='reviewed'")->fetch()['c'];
        $html .= '<p class="eyebrow">Project owner workspace</p><h1>Translation Studio administration</h1><p class="muted">Manage people, assignments, reviews, rewards, and payments.</p><div class="grid grid-4"><div class="progress-card"><strong>' . $pilot . '</strong><span>Pilot examples</span></div><div class="progress-card"><strong>' . $eval . '</strong><span>Evaluation items</span></div><div class="progress-card"><strong>' . $ready . '</strong><span>Ready for review</span></div><div class="progress-card"><strong>' . $reviewed . '</strong><span>Reviewed translations</span></div></div><div class="card" style="margin-top:1rem"><h2>Administration</h2><div class="button-row"><a class="btn btn-secondary" href="index.php?page=admin_users">People</a><a class="btn btn-secondary" href="index.php?page=admin_assign">Assign work</a><a class="btn btn-secondary" href="index.php?page=admin_items">All examples</a><a class="btn btn-secondary" href="index.php?page=admin_payments">Reward payments</a><a class="btn btn-quiet" href="index.php?page=admin_audit">Audit history</a></div><p class="small muted" style="margin-top:1rem">' . $items . ' source examples imported. Training export remains in the validated Python tooling.</p></div>';
    }
    echo layout('Welcome', $html, $user, 'home');
}

function page_work_list(PDO $pdo, array $user): void
{
    $rows = pdo_query($pdo, "SELECT i.*, t.status translation_status, t.version translation_version, t.resolution_required FROM assignments a JOIN items i ON i.item_id=a.item_id LEFT JOIN translations t ON t.item_id=i.item_id WHERE a.user_id=? AND a.assignment_type='translation' ORDER BY i.item_id", [(int)$user['id']])->fetchAll();
    $c = progress_counts($pdo, (int)$user['id'], 'translator');
    $body = '<p class="eyebrow">Your assigned work</p><h1>My translation work</h1><p class="muted">Choose one example at a time. Read the English source, write the Luganda version, and save your progress.</p><div class="grid grid-4"><div class="progress-card"><strong>' . $c['waiting'] . '</strong><span>Waiting to be translated</span></div><div class="progress-card"><strong>' . $c['saved'] . '</strong><span>Saved translations</span></div><div class="progress-card"><strong>' . $c['returned'] . '</strong><span>Returned for correction</span></div><div class="progress-card"><strong>' . $c['ready'] . '</strong><span>Ready for review</span></div></div>';
    if (!$rows) { $body .= '<div class="card empty"><h2>No work has been assigned yet</h2><p>The project administrator will assign translation examples to you.</p></div>'; }
    else {
        $body .= '<div class="list" style="margin-top:1rem">';
        foreach ($rows as $n => $row) {
            $source = source_of($row);
            $status = $row['translation_status'] ?: 'not_started';
            $body .= '<article class="list-item"><div><p class="eyebrow" style="margin-bottom:.25rem">Example ' . ($n+1) . ' of ' . count($rows) . '</p><h3>' . h(capability_label_php($source['primary_capability'] ?? '')) . '</h3><p>' . h(mb_strimwidth($source['source_prompt'] ?? '', 0, 180, '...')) . '</p><div class="item-meta"><span class="badge">' . h(status_label_php($status)) . '</span>' . (!empty($source['source_context']) ? '<span class="badge">Has a background passage</span>' : '') . (!empty($source['conversation_turns']) ? '<span class="badge">Conversation</span>' : '') . ((int)$row['resolution_required'] ? '<span class="badge badge-red">Owner resolution needed</span>' : '') . '</div></div><div class="item-actions"><a class="btn btn-primary btn-small" href="index.php?page=work_item&amp;item=' . h($row['item_id']) . '">' . ($status === 'not_started' ? 'Open' : 'Continue') . '</a></div></article>';
        }
        $body .= '</div>';
    }
    echo layout('My translation work', $body, $user, 'work');
}

function page_work_item(PDO $pdo, array $user, string $id, ?string $error = null, ?array $form = null): void
{
    global $PURPOSES;
    $item = item_row($pdo, $id); if (!$item) { page_error(404, 'Example not found.'); return; }
    if ($user['role'] === 'translator' && !assignment($pdo, $id, (int)$user['id'], 'translation')) { page_error(403, 'This example is not assigned to you.'); return; }
    $source = source_of($item); $translation = translation_row($pdo, $id); $meta = metadata_row($pdo, $id); $reviews = reviews_for($pdo, $id);
    $turns = $translation ? (json_decode($translation['turns_lg'], true) ?: []) : [];
    if ($form === null) $form = ['context_lg'=>$translation['context_lg'] ?? '', 'turns'=>$turns, 'prompt_lg'=>$translation['prompt_lg'] ?? '', 'response_lg'=>$translation['response_lg'] ?? '', 'notes'=>$translation['notes'] ?? ''];
    $status = $translation['status'] ?? 'not_started';
    $editable = $user['role'] === 'translator' && in_array($status, ['not_started','in_progress','needs_revision'], true) && ($meta['dataset_status'] ?? 'not_ready') !== 'approved_for_dataset';
    $body = '<p class="eyebrow">Example</p><h1>' . h(capability_label_php($source['primary_capability'] ?? '')) . '</h1><p class="muted">' . h($PURPOSES[$source['primary_capability'] ?? ''] ?? '') . '</p>' . ($error ? error_box($error) : '');
    if (!$editable) $body .= '<div class="callout"><strong>This translation is not open for editing.</strong> It is ' . h(status_label_php($status)) . '. A reviewer or administrator must return it for correction before it can be edited.</div>';
    $body .= '<div class="review-layout"><div><section class="card"><h2>1. Read the English example</h2><p class="eyebrow">What you are asked to do</p><p class="instruction">' . h($source['source_prompt'] ?? '') . '</p>';
    if (!empty($source['source_context'])) $body .= '<div class="soft-card" style="margin-top:1rem"><p class="eyebrow">Background passage</p><p class="context">' . h($source['source_context']) . '</p></div>';
    else $body .= '<p class="small muted" style="margin-top:1rem">There is no extra background passage for this example.</p>';
    if (!empty($source['conversation_turns'])) { $body .= '<div style="margin-top:1.2rem"><p class="eyebrow">Earlier conversation</p>'; foreach ($source['conversation_turns'] as $turn) $body .= '<div class="turn ' . ($turn['role']==='user'?'turn-user':'turn-assistant') . '"><div class="speaker">' . ($turn['role']==='user'?'Earlier request':'Earlier reply') . '</div><div class="turn-text">' . h($turn['content']) . '</div></div>'; $body .= '</div>'; }
    $body .= '<details class="details"><summary>Show the English meaning guide</summary><p class="small muted" style="margin-top:.6rem">This is an English reference or rubric. It is not a Luganda translation.</p><p class="reference-text">' . h($source['reference_answer_or_rubric']['content'] ?? '') . '</p></details></section>';
    $body .= '<section class="card" style="margin-top:1rem"><h2>2. Understand the expected result</h2><p class="eyebrow">The assistant reply should</p><ul class="notice-list">'; foreach (($source['expected_response_criteria'] ?? []) as $criterion) $body .= '<li>' . h($criterion) . '</li>'; $body .= '</ul>'; if (!empty($source['required_constraints'])) { $body .= '<p class="eyebrow" style="margin-top:1rem">Important constraints</p><ul class="notice-list">'; foreach ($source['required_constraints'] as $constraint) $body .= '<li>' . h($constraint) . '</li>'; $body .= '</ul>'; } $body .= '</section>';
    $body .= '<section class="card" style="margin-top:1rem"><h2>3. Write in Luganda</h2><div class="callout callout-green"><strong>You are preparing both sides of the conversation.</strong> Translate the user\'s request into Luganda, then write the assistant\'s Luganda reply. These are two different messages.</div>';
    if ($editable) {
        $body .= '<div class="notice" id="recovery-banner" hidden><strong>Unsaved text from earlier on this device is available.</strong><div class="button-row"><button class="btn btn-secondary btn-small" type="button" data-recover-draft>Restore unsaved text</button><button class="btn btn-quiet btn-small" type="button" data-discard-draft>Discard this copy</button></div></div>';
        $body .= '<form method="post" action="index.php?page=work_item&amp;item=' . h($id) . '" data-dirty-form data-autosave-url="index.php?page=autosave&amp;item=' . h($id) . '" data-item-id="' . h($id) . '" data-user-id="' . (int)$user['id'] . '">' . csrf_field() . '<p class="small muted">This page saves a draft automatically while you type.</p>';
        if (!empty($source['source_context'])) $body .= '<div class="field"><label for="context_lg">Background passage in Luganda <span class="badge badge-gold">Required</span></label><p class="hint">Translate the passage above. The assistant needs it to answer the user\'s question.</p><textarea id="context_lg" name="context_lg" class="editor" lang="lg" spellcheck="true">' . h($form['context_lg']) . '</textarea></div>';
        if (!empty($source['conversation_turns'])) { $body .= '<div class="field"><label>Translate the earlier conversation</label>'; foreach ($source['conversation_turns'] as $i => $turn) { $body .= '<div class="soft-card" style="margin-bottom:.8rem"><p class="speaker">' . ($turn['role']==='user'?'Earlier request':'Earlier reply') . '</p><p class="small context">' . h($turn['content']) . '</p><label for="turn_' . $i . '">Luganda for this turn</label><textarea id="turn_' . $i . '" name="turn_' . $i . '" class="editor" lang="lg" spellcheck="true">' . h($form['turns'][$i] ?? '') . '</textarea></div>'; } $body .= '</div>'; }
        $body .= '<div class="field"><label for="prompt_lg">User message in Luganda</label><p class="hint">Translate the final English request above. This is what the user will say to the assistant.</p><textarea id="prompt_lg" name="prompt_lg" class="editor" lang="lg" spellcheck="true">' . h($form['prompt_lg']) . '</textarea></div><div class="field"><label for="response_lg">Assistant reply in Luganda</label><p class="hint">Write the answer the assistant should give. Use natural Luganda, not the English reference answer.</p><textarea id="response_lg" name="response_lg" class="editor" lang="lg" spellcheck="true">' . h($form['response_lg']) . '</textarea></div><div class="field"><label for="notes">Translation notes <span class="muted">(optional)</span></label><textarea id="notes" name="notes" style="min-height:100px">' . h($form['notes']) . '</textarea></div><div class="form-actions"><button class="btn btn-primary" type="submit" name="action" value="save">Save progress</button><button class="btn btn-secondary" type="submit" name="action" value="save_next">Save and next example</button><button class="btn btn-gold" type="submit" name="action" value="submit">Mark as ready for review</button><span class="saved-indicator" data-save-state>No unsaved changes</span></div></form>';
    } else {
        if (!empty($source['source_context'])) { $body .= '<div class="field"><p class="eyebrow">Background passage in Luganda</p>' . (trim($form['context_lg']) !== '' ? '<div class="translation-text">' . h($form['context_lg']) . '</div>' : '<div class="error-box"><strong>Background passage missing.</strong> This required passage was not translated. Ask a reviewer or administrator to return the example for correction.</div>') . '</div>'; }
        if (!empty($source['conversation_turns'])) { $body .= '<div class="field"><p class="eyebrow">Earlier conversation in Luganda</p>'; foreach ($source['conversation_turns'] as $i => $turn) $body .= '<div class="soft-card" style="margin-bottom:.8rem"><p class="speaker">' . ($turn['role']==='user'?'Earlier request':'Earlier reply') . '</p><div class="translation-text">' . h($form['turns'][$i] ?? 'Not translated.') . '</div></div>'; $body .= '</div>'; }
        $body .= '<div class="field"><p class="eyebrow">User message in Luganda</p><div class="translation-text">' . h($form['prompt_lg'] ?: 'Not translated.') . '</div></div><div class="field"><p class="eyebrow">Assistant reply in Luganda</p><div class="translation-text">' . h($form['response_lg'] ?: 'Not translated.') . '</div></div>';
    }
    $body .= '</section>';
    if ($reviews) { $body .= '<section class="card" style="margin-top:1rem"><h2>Review feedback</h2>'; foreach ($reviews as $review) $body .= '<div class="soft-card" style="margin-bottom:.7rem"><span class="badge">' . h(decision_label_php($review['decision'])) . '</span> <span class="small muted">' . h($review['reviewer_name']) . ' · ' . h(format_dt($review['created_at'])) . ' · version ' . (int)$review['translation_version'] . '</span>' . ($review['comments'] ? '<p style="margin-top:.6rem">' . h($review['comments']) . '</p>' : '') . '</div>'; $body .= '</section>'; }
    $body .= '</div><aside class="review-side"><div class="card"><h2>Save and navigate</h2><p><span class="badge">' . h(status_label_php($status)) . '</span></p><div class="button-row"><a class="btn btn-secondary btn-small" href="index.php?page=work">Back to my work</a></div></div><div class="card" style="margin-top:1rem"><h2>About this task</h2><p class="small">' . h($PURPOSES[$source['primary_capability'] ?? ''] ?? '') . '</p></div></aside></div>';
    echo layout('Translate example', $body, $user, 'work');
}

function page_progress(PDO $pdo, array $user): void
{
    $rows = pdo_query($pdo, "SELECT i.*, t.status translation_status, t.resolution_required FROM assignments a JOIN items i ON i.item_id=a.item_id LEFT JOIN translations t ON t.item_id=i.item_id WHERE a.user_id=? AND a.assignment_type='translation' ORDER BY i.item_id", [(int)$user['id']])->fetchAll();
    $c = progress_counts($pdo, (int)$user['id'], 'translator'); $r = translator_reward($pdo,(int)$user['id']);
    $body = '<p class="eyebrow">Your work record</p><h1>My progress</h1><p class="muted">Saving a translation does not approve it. A reviewer may ask for changes.</p><div class="grid grid-4"><div class="progress-card"><strong>' . $c['waiting'] . '</strong><span>Waiting</span></div><div class="progress-card"><strong>' . $c['saved'] . '</strong><span>Saved</span></div><div class="progress-card"><strong>' . $c['returned'] . '</strong><span>Returned</span></div><div class="progress-card"><strong>' . $c['ready'] . '</strong><span>Ready for review</span></div></div><div class="reward-panel" style="margin-top:1rem"><div><p class="eyebrow">Approved work reward</p><div class="reward-amount">$' . number_format((float)$r['available_usd'],2) . '</div><p>' . $r['approved_count'] . ' approved translations. Total cleared: $' . number_format((float)$r['paid_usd'],2) . '.</p></div><div class="reward-note"><a class="btn btn-secondary btn-small" href="index.php?page=rewards">See my rewards</a></div></div>';
    if ($rows) { $body .= '<div class="list" style="margin-top:1rem">'; foreach ($rows as $row) { $source=source_of($row); $status=$row['translation_status']?:'not_started'; $body .= '<article class="list-item"><div><h3>' . h(capability_label_php($source['primary_capability'] ?? '')) . '</h3><p>' . h(mb_strimwidth($source['source_prompt'] ?? '',0,160,'...')) . '</p><span class="badge">' . h(status_label_php($status)) . '</span></div><div class="item-actions"><a class="btn btn-secondary btn-small" href="index.php?page=work_item&amp;item=' . h($row['item_id']) . '">Open</a></div></article>'; } $body .= '</div>'; } else $body .= '<div class="card empty"><h2>No assigned work yet</h2></div>';
    echo layout('My progress',$body,$user,'progress');
}

function page_review_list(PDO $pdo, array $user): void
{
    if ($user['role'] === 'admin') $rows = pdo_query($pdo, "SELECT i.*, t.status translation_status, t.version translation_version, t.resolution_required, u.public_id translator_public_id FROM items i JOIN translations t ON t.item_id=i.item_id LEFT JOIN users u ON u.id=t.translator_id ORDER BY i.item_id")->fetchAll();
    else $rows = pdo_query($pdo, "SELECT i.*, t.status translation_status, t.version translation_version, t.resolution_required FROM assignments a JOIN items i ON i.item_id=a.item_id JOIN translations t ON t.item_id=i.item_id WHERE a.user_id=? AND a.assignment_type='review' ORDER BY i.item_id", [(int)$user['id']])->fetchAll();
    $c = progress_counts($pdo, (int)$user['id'], 'reviewer');
    $body = '<p class="eyebrow">Independent language review</p><h1>Review translations</h1><p class="muted">Compare each Luganda translation with the English source. Record a decision and keep your comments specific.</p><div class="grid grid-3"><div class="progress-card"><strong>' . $c['waiting'] . '</strong><span>Waiting for your review</span></div><div class="progress-card"><strong>' . $c['completed'] . '</strong><span>Completed reviews</span></div><div class="progress-card"><strong>' . $c['total'] . '</strong><span>Assigned to you</span></div></div>';
    if (!$rows) $body .= '<div class="card empty"><h2>No review work assigned</h2></div>';
    else {
        $body .= '<div class="list" style="margin-top:1rem">';
        foreach ($rows as $row) {
            $source=source_of($row); $my=null;
            if ($user['role']==='reviewer') { foreach (reviews_for($pdo,$row['item_id'],(int)$row['translation_version']) as $r) if ((int)$r['reviewer_id']===(int)$user['id']) $my=$r; }
            $body .= '<article class="list-item"><div><h3>' . h(capability_label_php($source['primary_capability'] ?? '')) . '</h3><p>' . h(mb_strimwidth($source['source_prompt'] ?? '',0,180,'...')) . '</p><div class="item-meta"><span class="badge">' . h(status_label_php($row['translation_status'])) . '</span>' . ((int)$row['resolution_required']?'<span class="badge badge-red">Owner resolution needed</span>':'') . '</div></div><div class="item-actions">';
            if ($my) { $tone = $my['decision']==='approved'?'badge-green':($my['decision']==='needs_revision'?'badge-red':'badge-gold'); $body .= '<span class="badge ' . $tone . '">Reviewed · ' . h(decision_label_php($my['decision'])) . '</span><a class="btn btn-secondary btn-small" href="index.php?page=review_item&amp;item=' . h($row['item_id']) . '">View review</a>'; }
            else $body .= '<a class="btn btn-primary btn-small" href="index.php?page=review_item&amp;item=' . h($row['item_id']) . '">Open review</a>';
            $body .= '</div></article>';
        }
        $body .= '</div>';
    }
    echo layout('Review work',$body,$user,'review');
}

function page_review_item(PDO $pdo, array $user, string $id, ?string $error = null, ?array $form = null): void
{
    global $PURPOSES;
    $item=item_row($pdo,$id); if(!$item){page_error(404,'Example not found.');return;}
    if($user['role']==='reviewer' && !assignment($pdo,$id,(int)$user['id'],'review')){page_error(403,'This example is not assigned to you for review.');return;}
    $t=translation_row($pdo,$id); if(!$t){page_error(404,'There is no translation to review.');return;}
    $source=source_of($item); $reviews=reviews_for($pdo,$id); $my=null;
    foreach($reviews as $r) if((int)$r['reviewer_id']===(int)$user['id'] && (int)$r['translation_version']===(int)$t['version']) $my=$r;
    $canReview=$user['role']==='reviewer' && assignment($pdo,$id,(int)$user['id'],'review') && in_array($t['status'],['ready_for_review','reviewed'],true) && !$my && (int)$t['translator_id']!==(int)$user['id'];
    $body='<p class="eyebrow">Independent review</p><h1>'.h(capability_label_php($source['primary_capability']??'')).'</h1><p class="muted">'.h($PURPOSES[$source['primary_capability']??'']??'').'</p>'.($error?error_box($error):'');
    if($user['role']==='admin') $body.='<div class="callout callout-green"><strong>Administrator view.</strong> Reviewers submit decisions. Administrators resolve disagreements.</div>';
    elseif($my) $body.='<div class="notice"><strong>You already submitted a review for this version.</strong> Your decision and comments are shown below.</div>';
    $body.='<div class="review-layout"><div><section class="card"><h2>1. Read the English source</h2><p class="eyebrow">The request</p><p class="instruction">'.h($source['source_prompt']??'').'</p>';
    if(!empty($source['source_context'])) $body.='<div class="soft-card" style="margin-top:1rem"><p class="eyebrow">Background passage</p><p class="context">'.h($source['source_context']).'</p></div>';
    if(!empty($source['conversation_turns'])){ $body.='<div style="margin-top:1.2rem"><p class="eyebrow">Earlier conversation</p>'; foreach($source['conversation_turns'] as $turn) $body.='<div class="turn '.($turn['role']==='user'?'turn-user':'turn-assistant').'"><div class="speaker">'.($turn['role']==='user'?'Earlier request':'Earlier reply').'</div><div class="turn-text">'.h($turn['content']).'</div></div>'; $body.='</div>'; }
    $body.='<details class="details"><summary>Show the English meaning guide</summary><p class="small muted" style="margin-top:.6rem">This is an English reference or rubric, not a Luganda answer.</p><p class="reference-text">'.h($source['reference_answer_or_rubric']['content']??'').'</p></details></section>';
    $body.='<section class="card" style="margin-top:1rem"><h2>2. Read the Luganda translation</h2>';
    if(!empty($source['source_context'])){ if(trim($t['context_lg'])!=='') $body.='<div class="field"><p class="eyebrow">Background passage in Luganda</p><div class="translation-text">'.h($t['context_lg']).'</div></div>'; else $body.='<div class="error-box"><strong>Required background passage missing.</strong> Request revision unless there is a documented reason to accept it.</div>'; }
    if(!empty($source['conversation_turns'])){ $turns=json_decode($t['turns_lg'],true)?:[]; $body.='<div class="field"><p class="eyebrow">Earlier conversation in Luganda</p>'; foreach($source['conversation_turns'] as $i=>$turn) $body.='<div class="soft-card" style="margin-bottom:.8rem"><p class="speaker">'.($turn['role']==='user'?'Earlier request':'Earlier reply').'</p><div class="translation-text">'.h($turns[$i]??'Not translated.').'</div></div>'; $body.='</div>'; }
    $body.='<div class="field"><p class="eyebrow">User message in Luganda</p><div class="translation-text">'.h($t['prompt_lg']).'</div></div><div class="field"><p class="eyebrow">Assistant reply in Luganda</p><div class="translation-text">'.h($t['response_lg']).'</div></div>';
    if($t['notes']) $body.='<div class="field"><p class="eyebrow">Translator notes</p><p class="context">'.h($t['notes']).'</p></div>';
    $body.='</section><section class="card" style="margin-top:1rem"><h2>3. Check the expected result</h2><ul class="notice-list">'; foreach(($source['expected_response_criteria']??[]) as $criterion) $body.='<li>'.h($criterion).'</li>'; $body.='</ul>'; if(!empty($source['required_constraints'])){ $body.='<p class="eyebrow" style="margin-top:1rem">Constraints</p><ul class="notice-list">'; foreach($source['required_constraints'] as $constraint) $body.='<li>'.h($constraint).'</li>'; $body.='</ul>'; } $body.='</section>';
    if($reviews){ $body.='<section class="card" style="margin-top:1rem"><h2>Review history</h2>'; foreach($reviews as $review) $body.='<div class="soft-card" style="margin-bottom:.7rem"><span class="badge">'.h(decision_label_php($review['decision'])).'</span> <span class="small muted">'.h($review['reviewer_name']).' · version '.(int)$review['translation_version'].' · '.h(format_dt($review['created_at'])).'</span>'.($review['comments']?'<p style="margin-top:.5rem">'.h($review['comments']).'</p>':'').'</div>'; $body.='</section>'; }
    $body.='</div><aside class="review-side"><div class="card"><h2>Your review decision</h2>';
    if($my) $body.='<p><strong>Your recorded decision:</strong> '.h(decision_label_php($my['decision'])).'</p>';
    elseif($canReview){ $form=$form?:['decision'=>'','comments'=>'','suggested_correction'=>'']; $body.='<p>Approval means the translation is acceptable for the next stage. It is not training authorization.</p><form method="post" action="index.php?page=review_item&amp;item='.h($id).'" data-dirty-form>'.csrf_field().'<div class="field"><label for="decision">Decision</label><select id="decision" name="decision" data-review-decision required><option value="">Choose a decision</option><option value="approved"'.($form['decision']==='approved'?' selected':'').'>Approved</option><option value="needs_revision"'.($form['decision']==='needs_revision'?' selected':'').'>Needs revision</option><option value="cannot_assess"'.($form['decision']==='cannot_assess'?' selected':'').'>Cannot assess yet</option></select></div><div class="field"><label for="comments">Comments and explanation</label><p class="hint" data-comment-hint>Please explain your decision. Required for revision or cannot assess.</p><textarea id="comments" name="comments" class="editor" lang="lg">'.h($form['comments']).'</textarea></div><div class="field"><label for="suggested_correction">Suggested correction <span class="muted">(optional)</span></label><textarea id="suggested_correction" name="suggested_correction" style="min-height:130px" lang="lg">'.h($form['suggested_correction']).'</textarea></div><button class="btn btn-primary" type="submit">Submit review</button><span class="saved-indicator" data-save-state>No unsaved changes</span></form>'; }
    else $body.='<p>This translation is not currently open for your review. An administrator may need to return it for correction or resolve a disagreement.</p>';
    $body.='</div><div class="card" style="margin-top:1rem"><h2>Current state</h2><p><span class="badge">'.h(status_label_php($t['status'])).'</span></p><a class="btn btn-secondary btn-small" href="index.php?page=review">Back to review work</a></div></aside></div>';
    echo layout('Review translation',$body,$user,'review');
}

function page_rewards(PDO $pdo, array $user): void
{
    $r=$user['role']==='reviewer'?reviewer_reward($pdo,(int)$user['id']):translator_reward($pdo,(int)$user['id']);
    $isReviewer=$user['role']==='reviewer';
    $body='<p class="eyebrow">'.($isReviewer?'Review rewards':'Approved work').'</p><h1>My rewards</h1><p class="muted">'.($isReviewer?'Reviewers earn $0.10 for each completed review. Available earnings start again after a cleared payment.':'The project owner has set $0.20 per approved translation and a $2 reward at every 10 approved translations.').'</p><div class="reward-panel"><div><p class="eyebrow">Available since last payment</p><div class="reward-amount">$'.number_format((float)$r['available_usd'],2).'</div><p>'.($isReviewer?$r['review_count'].' completed review'.($r['review_count']===1?'':'s').' at $0.10 each.':$r['approved_count'].' approved translation'.($r['approved_count']===1?'':'s').' at $0.20 each.').'</p><p class="small muted">Total earned: $'.number_format((float)$r['accrued_usd'],2).'. Total cleared: $'.number_format((float)$r['paid_usd'],2).'.</p></div><div class="reward-note"><p class="eyebrow">Payment</p>'.($r['payments']?'<p><span class="badge badge-green">Payment cleared</span> Latest payment '.h(format_dt($r['payments'][0]['paid_at'])).'.</p>':'<p>No payment has been cleared yet.</p>').'<p class="small muted">This is an estimate and does not process money. The owner confirms payment separately.</p><a class="btn btn-secondary btn-small" href="index.php?page='.($isReviewer?'review':'work').'">Back to my work</a></div></div>';
    if($r['payments']){ $body.='<div class="card" style="margin-top:1rem"><h2>Cleared payments</h2><div class="list">'; foreach($r['payments'] as $payment) $body.='<div class="list-item"><div><h3>$'.number_format((float)$payment['amount_usd'],2).' cleared</h3><p class="small muted">'.h(format_dt($payment['paid_at'])).' · '.h($payment['note']).'</p></div><span class="badge badge-green">Cleared</span></div>'; $body.='</div></div>'; }
    $body.='<div class="card" style="margin-top:1rem"><h2>How the reward works</h2><p>'.($isReviewer?'Each submitted review adds $0.10.':'Each approved translation adds $0.20. Every 10 approved translations reaches $2.').' A cleared payment does not delete work history. New work starts a new available balance.</p></div>';
    echo layout('My rewards',$body,$user,'rewards');
}

function page_admin_users(PDO $pdo, array $user, ?string $error = null, ?array $form = null): void
{
    $users=pdo_query($pdo,'SELECT id,username,display_name,public_id,role,active,created_at FROM users ORDER BY role,display_name')->fetchAll();
    $body='<p class="eyebrow">Administration</p><h1>People and permissions</h1><p class="muted">Create local accounts. There is no public registration.</p>'.($error?error_box($error):'').'<div class="grid grid-2"><div class="card"><h2>Create an account</h2><form method="post" action="index.php?page=admin_users">'.csrf_field().'<div class="field"><label for="display_name">Display name</label><input id="display_name" name="display_name" value="'.h($form['display_name']??'').'" required></div><div class="field"><label for="username">Username</label><input id="username" name="username" value="'.h($form['username']??'').'" required></div><div class="field"><label for="role">Role</label><select id="role" name="role" required><option value="">Choose a role</option><option value="translator">Translator</option><option value="reviewer">Reviewer</option><option value="admin">Administrator</option></select></div><div class="field"><label for="password">Temporary password</label><input id="password" name="password" type="password" minlength="10" required></div><button class="btn btn-primary" type="submit">Create account</button></form></div><div class="card"><h2>Current accounts</h2><div class="list">';
    foreach($users as $person) $body.='<div class="soft-card"><div class="item-meta"><span class="badge">'.h(role_label_php($person['role'])).'</span><span class="badge">'.h($person['public_id']).'</span></div><p style="margin-top:.5rem"><strong>'.h($person['display_name']).'</strong> <span class="muted small">@'.h($person['username']).'</span></p></div>';
    $body.='</div></div></div>';
    echo layout('People',$body,$user,'admin');
}

function page_admin_assign(PDO $pdo, array $user, ?string $error = null): void
{
    $translators=pdo_query($pdo,"SELECT id,display_name,public_id FROM users WHERE role='translator' AND active=1 ORDER BY display_name")->fetchAll();
    $reviewers=pdo_query($pdo,"SELECT id,display_name,public_id FROM users WHERE role='reviewer' AND active=1 ORDER BY display_name")->fetchAll();
    $unassigned=(int)pdo_query($pdo,"SELECT COUNT(*) c FROM items i LEFT JOIN assignments a ON a.item_id=i.item_id AND a.assignment_type='translation' WHERE a.id IS NULL")->fetch()['c'];
    $ready=(int)pdo_query($pdo,"SELECT COUNT(*) c FROM translations WHERE status='ready_for_review'")->fetch()['c'];
    $translationCard = '<div class="card"><h2>Assign translation work</h2>';
    if ($translators) {
        $translationCard .= '<form method="post" action="index.php?page=admin_assign">' . csrf_field() . '<input type="hidden" name="assignment_type" value="translation"><div class="field"><label>Translator</label><select name="user_id" required><option value="">Choose</option>';
        foreach ($translators as $p) $translationCard .= '<option value="' . $p['id'] . '">' . h($p['display_name']) . ' · ' . h($p['public_id']) . '</option>';
        $translationCard .= '</select></div><div class="field"><label>How many</label><input type="number" name="limit" min="1" max="200" value="10" required></div><button class="btn btn-primary" type="submit">Assign translation work</button></form><p class="small muted" style="margin-top:.6rem">' . $unassigned . ' examples have no translator.</p>';
    } else { $translationCard .= '<p>Create a translator first.</p>'; }
    $translationCard .= '</div>';
    $reviewCard = '<div class="card"><h2>Assign review work</h2>';
    if ($reviewers) {
        $reviewCard .= '<form method="post" action="index.php?page=admin_assign">' . csrf_field() . '<input type="hidden" name="assignment_type" value="review"><div class="field"><label>Reviewer</label><select name="user_id" required><option value="">Choose</option>';
        foreach ($reviewers as $p) $reviewCard .= '<option value="' . $p['id'] . '">' . h($p['display_name']) . ' · ' . h($p['public_id']) . '</option>';
        $reviewCard .= '</select></div><div class="field"><label>How many</label><input type="number" name="limit" min="1" max="200" value="10" required></div><button class="btn btn-primary" type="submit">Assign review work</button></form><p class="small muted" style="margin-top:.6rem">' . $ready . ' translations are waiting for review.</p>';
    } else { $reviewCard .= '<p>Create a reviewer first.</p>'; }
    $reviewCard .= '</div>';
    $body = '<p class="eyebrow">Administration</p><h1>Assign work</h1><p class="muted">Assign translators to unassigned examples and reviewers to submitted translations.</p>' . ($error ? error_box($error) : '') . '<div class="grid grid-2">' . $translationCard . $reviewCard . '</div>';
    echo layout('Assign work',$body,$user,'admin');
}

function page_admin_items(PDO $pdo, array $user): void
{
    $rows=pdo_query($pdo,"SELECT i.*, t.status translation_status, t.resolution_required, m.dataset_status, u.display_name translator_name, u.public_id translator_public_id FROM items i LEFT JOIN translations t ON t.item_id=i.item_id LEFT JOIN training_metadata m ON m.item_id=i.item_id LEFT JOIN users u ON u.id=t.translator_id ORDER BY i.item_id")->fetchAll();
    $body='<p class="eyebrow">Administration</p><h1>All examples</h1><p class="muted">Pilot and evaluation items are shown separately. This view is for administrators only.</p><div class="table-wrap"><table><thead><tr><th>Example</th><th>Collection</th><th>Task</th><th>Translator</th><th>Translation</th><th>Dataset</th><th></th></tr></thead><tbody>';
    foreach($rows as $row){$source=source_of($row);$body.='<tr><td><strong>'.h($row['item_id']).'</strong><br><span class="small muted">'.h(mb_strimwidth($source['source_prompt']??'',0,80,'...')).'</span></td><td>'.h($row['collection']).'</td><td>'.h(capability_label_php($source['primary_capability']??'')).'</td><td>'.($row['translator_public_id']?h($row['translator_name']).'<br><span class="small muted">'.h($row['translator_public_id']).'</span>':'<span class="muted">Unassigned</span>').'</td><td><span class="badge">'.h(status_label_php($row['translation_status']?:'not_started')).'</span>'.((int)$row['resolution_required']?'<br><span class="badge badge-red">Resolution needed</span>':'').'</td><td>'.h(status_label_php($row['dataset_status']?:'not_ready')).'</td><td><a class="btn btn-secondary btn-small" href="index.php?page=admin_item&amp;item='.h($row['item_id']).'">Inspect</a></td></tr>';}
    $body.='</tbody></table></div>';
    echo layout('All examples',$body,$user,'admin');
}

function page_admin_item(PDO $pdo, array $user, string $id, ?string $error = null): void
{
    global $PURPOSES;
    $item=item_row($pdo,$id); if(!$item){page_error(404,'Example not found.');return;}
    $source=source_of($item);$t=translation_row($pdo,$id);$reviews=reviews_for($pdo,$id);$meta=metadata_row($pdo,$id);
    $body='<p class="eyebrow">Administration · '.h($id).'</p><h1>'.h(capability_label_php($source['primary_capability']??'')).'</h1>'.($error?error_box($error):'').'<div class="item-meta"><span class="badge">'.h($item['collection']).'</span><span class="badge">'.h($source['proposed_split']??'No split').'</span><span class="badge">'.h(status_label_php($t['status']??'not_started')).'</span><span class="badge">Dataset: '.h(status_label_php($meta['dataset_status']??'not_ready')).'</span></div><div class="grid grid-2" style="margin-top:1rem"><div class="card"><h2>English source</h2><p class="eyebrow">Request</p><p class="context">'.h($source['source_prompt']??'').'</p>'.(!empty($source['source_context'])?'<p class="eyebrow" style="margin-top:1rem">Background</p><p class="context">'.h($source['source_context']).'</p>':'').'</div><div class="card"><h2>Translation</h2>'.($t?'<p class="eyebrow">User message</p><div class="translation-text">'.h($t['prompt_lg']).'</div><p class="eyebrow" style="margin-top:.7rem">Assistant reply</p><div class="translation-text">'.h($t['response_lg']).'</div>': '<p class="muted">No translation has been saved.</p>').'</div></div>';
    if($t && $t['resolution_required']){$body.='<div class="card" style="margin-top:1rem"><h2>Resolve disagreement</h2><form method="post" action="index.php?page=admin_item&amp;item='.h($id).'">'.csrf_field().'<input type="hidden" name="action" value="resolve"><div class="field"><label>Resolution</label><select name="decision" required><option value="">Choose</option><option value="approved">Approve the translation</option><option value="needs_revision">Return it for revision</option></select></div><div class="field"><label>Reason</label><textarea name="notes" required></textarea></div><button class="btn btn-primary" type="submit">Record resolution</button></form></div>';}
    if($t && in_array($t['status'],['ready_for_review','under_dispute','reviewed'],true)){ $body.='<div class="card" style="margin-top:1rem"><h2>Return to the translator for correction</h2><p>Use this when required text is missing, such as the Luganda background passage, or the submission needs another pass.</p><form method="post" action="index.php?page=admin_item&amp;item='.h($id).'">'.csrf_field().'<input type="hidden" name="action" value="return_translation"><div class="field"><label>What needs correction?</label><textarea name="reason" required></textarea></div><button class="btn btn-secondary" type="submit">Return for correction</button></form></div>'; }
    $body.='<div class="card" style="margin-top:1rem"><h2>Review history</h2>'; if($reviews){foreach($reviews as $review) $body.='<div class="soft-card" style="margin-bottom:.7rem"><span class="badge">'.h(decision_label_php($review['decision'])).'</span> <span class="small muted">'.h($review['reviewer_name']).' · version '.(int)$review['translation_version'].' · '.h(format_dt($review['created_at'])).'</span>'.($review['comments']?'<p style="margin-top:.5rem">'.h($review['comments']).'</p>':'').'</div>';}else $body.='<p class="muted">No reviews yet.</p>'; $body.='</div>';
    echo layout('Inspect example',$body,$user,'admin');
}

function page_admin_payments(PDO $pdo, array $user, ?string $error = null): void
{
    $payables=all_payables($pdo);
    $body='<p class="eyebrow">Administration</p><h1>Reward payments</h1><p class="muted">Mark a payment as cleared after the payment is actually completed. This records the amount and resets the available balance for new work. It does not move money.</p>'.($error?error_box($error):'');
    if(!$payables){$body.='<div class="card empty"><h2>No reward accounts yet</h2></div>';}
    else {foreach($payables as $p){$body.='<div class="card" style="margin-bottom:1rem"><div class="item-meta"><span class="badge">'.h(role_label_php($p['role'])).'</span><span class="badge">'.h($p['public_id']).'</span>'.($p['available_usd']>0?'<span class="badge badge-green">$'.number_format((float)$p['available_usd'],2).' available</span>':'<span class="badge">No available balance</span>').'</div><h2>'.h($p['display_name']).'</h2><p class="small muted">'.$p['work_count'].' '.($p['role']==='translator'?'approved translations':'completed reviews').'. Total earned $'.number_format((float)$p['accrued_usd'],2).'. Total cleared $'.number_format((float)$p['paid_usd'],2).'.</p>'; if($p['payments']){$body.='<details class="details"><summary>Payment history</summary>'; foreach($p['payments'] as $payment) $body.='<p class="small">$'.number_format((float)$payment['amount_usd'],2).' · '.h(format_dt($payment['paid_at'])).' · '.h($payment['note']).'</p>'; $body.='</details>';} if($p['available_usd']>0){$body.='<form method="post" action="index.php?page=admin_payments" class="filter-row" style="margin-top:1rem">'.csrf_field().'<input type="hidden" name="recipient_id" value="'.$p['user_id'].'"><input type="hidden" name="role" value="'.h($p['role']).'"><div><label>Amount to clear</label><input type="number" name="amount" min="0.01" step="0.01" value="'.number_format((float)$p['available_usd'],2,'.','').'" required></div><div><label>Payment note or reference</label><input name="note" required></div><div style="align-self:end"><button class="btn btn-primary" type="submit">Mark payment cleared</button></div></form>';} $body.='</div>';}}
    echo layout('Reward payments',$body,$user,'admin');
}

function page_admin_audit(PDO $pdo, array $user): void
{
    $rows=pdo_query($pdo,'SELECT e.*, u.display_name actor_name FROM audit_events e LEFT JOIN users u ON u.id=e.actor_id ORDER BY e.id DESC LIMIT 200')->fetchAll();
    $body='<p class="eyebrow">Administration</p><h1>Audit history</h1><div class="table-wrap"><table><thead><tr><th>Time</th><th>Account</th><th>Action</th><th>Record</th></tr></thead><tbody>';
    foreach($rows as $row) $body.='<tr><td>'.h(format_dt($row['created_at'])).'</td><td>'.h($row['actor_name']??'System').'</td><td>'.h($row['action']).'</td><td>'.h($row['entity_type'].' '.$row['entity_id']).'</td></tr>';
    $body.='</tbody></table></div>';
    echo layout('Audit history',$body,$user,'admin');
}

function page_error(int $status, string $message): void
{
    http_response_code($status);
    $user=null; $body='<div class="narrow"><div class="card"><p class="eyebrow">Request status '.$status.'</p><h1>'.($status===403?'Permission required':($status===404?'Page not found':'Something needs attention')).'</h1><p>'.h($message).'</p><a class="btn btn-primary" href="index.php?page=home">Go back</a></div></div>';
    echo layout('Problem',$body,$user,'');
}

function bulk_assign_translation_php(PDO $pdo, int $uid, int $limit, int $actor): int
{
    $rows=pdo_query($pdo,"SELECT i.item_id FROM items i LEFT JOIN assignments a ON a.item_id=i.item_id AND a.assignment_type='translation' WHERE a.id IS NULL ORDER BY i.item_id LIMIT ?",[$limit])->fetchAll();
    $count=0; foreach($rows as $row){pdo_query($pdo,"INSERT INTO assignments(item_id,user_id,assignment_type,created_by,created_at) VALUES (?,?,'translation',?,?)",[$row['item_id'],$uid,$actor,now_iso()]); $count++;}
    if($count) audit($pdo,$actor,'translation_assigned','assignment','bulk',['user_id'=>$uid,'count'=>$count]);
    return $count;
}
function bulk_assign_review_php(PDO $pdo, int $uid, int $limit, int $actor): int
{
    $rows=pdo_query($pdo,"SELECT i.item_id FROM items i JOIN translations t ON t.item_id=i.item_id WHERE t.status='ready_for_review' AND t.translator_id<>? AND NOT EXISTS (SELECT 1 FROM assignments a WHERE a.item_id=i.item_id AND a.user_id=? AND a.assignment_type='review') AND NOT EXISTS (SELECT 1 FROM reviews r WHERE r.item_id=i.item_id AND r.reviewer_id=? AND r.translation_version=t.version) ORDER BY i.item_id LIMIT ?",[$uid,$uid,$uid,$limit])->fetchAll();
    $count=0; foreach($rows as $row){pdo_query($pdo,"INSERT INTO assignments(item_id,user_id,assignment_type,created_by,created_at) VALUES (?,?,'review',?,?)",[$row['item_id'],$uid,$actor,now_iso()]); $count++;}
    if($count) audit($pdo,$actor,'review_assigned','assignment','bulk',['user_id'=>$uid,'count'=>$count]);
    return $count;
}
function page_admin_home(PDO $pdo, array $user): void
{
    page_home($pdo,$user);
}

$user = current_user($pdo);
$page = $_GET['page'] ?? ($user ? 'home' : 'login');
$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';

if ($page === 'login') {
    if ($method === 'POST') {
        verify_csrf();
        $username = trim($_POST['username'] ?? '');
        $password = $_POST['password'] ?? '';
        $row = pdo_query($pdo, 'SELECT * FROM users WHERE username = ? COLLATE NOCASE AND active = 1', [$username])->fetch();
        if ($row && verify_password_php($password, $row['password_salt'], $row['password_hash'])) {
            $_SESSION['user_id'] = (int)$row['id']; audit($pdo,(int)$row['id'],'login','session',substr(session_id(),0,8)); redirect('index.php?page=home');
        }
        page_login(null, 'The username or password was not recognized.', $username); exit;
    }
    page_login($user); exit;
}

if ($page === 'logout') {
    if ($method === 'POST') { verify_csrf(); if ($user) audit($pdo,(int)$user['id'],'logout','session',substr(session_id(),0,8)); session_destroy(); redirect('index.php?page=login'); }
    redirect('index.php?page=home');
}

if (!$user) { redirect('index.php?page=login'); }

if ($method === 'POST' && $page !== 'login') verify_csrf();

if ($page === 'work_item' && $method === 'POST') {
    require_role($user,['translator']);
    $id = $_GET['item'] ?? '';
    $turns = [];
    $item = item_row($pdo,$id);
    if ($item) { $source=source_of($item); foreach(($source['conversation_turns']??[]) as $i=>$turn) $turns[] = $_POST['turn_'.$i] ?? ''; }
    $form=['context_lg'=>$_POST['context_lg']??'','turns'=>$turns,'prompt_lg'=>$_POST['prompt_lg']??'','response_lg'=>$_POST['response_lg']??'','notes'=>$_POST['notes']??''];
    try {
        save_translation_php($pdo,$id,(int)$user['id'],$form['context_lg'],$turns,$form['prompt_lg'],$form['response_lg'],$form['notes'],($_POST['action']??'save')==='submit');
        if (($_POST['action']??'')==='save_next') { $next=pdo_query($pdo,"SELECT a.item_id FROM assignments a LEFT JOIN translations t ON t.item_id=a.item_id WHERE a.user_id=? AND a.assignment_type='translation' AND a.item_id>? AND COALESCE(t.status,'not_started') IN ('not_started','in_progress','needs_revision') ORDER BY a.item_id LIMIT 1",[(int)$user['id'],$id])->fetch(); redirect('index.php?page=work_item&item='.($next['item_id']??$id)); }
        flash('Progress saved.');
        redirect('index.php?page=work_item&item='.$id);
    } catch (Throwable $error) { page_work_item($pdo,$user,$id,$error->getMessage(),$form); exit; }
}

if ($page === 'autosave' && $method === 'POST') {
    require_role($user,['translator']);
    header('Content-Type: application/json; charset=utf-8');
    $id=$_GET['item']??''; $turns=[]; $item=item_row($pdo,$id);
    if($item){$source=source_of($item);foreach(($source['conversation_turns']??[]) as $i=>$turn)$turns[]=$_POST['turn_'.$i]??'';}
    try { $t=save_translation_php($pdo,$id,(int)$user['id'],$_POST['context_lg']??'',$turns,$_POST['prompt_lg']??'',$response=$_POST['response_lg']??'',$notes=$_POST['notes']??'',false); echo json_encode(['status'=>'saved','saved_at'=>$t['updated_at'],'translation_status'=>$t['status']]); }
    catch(Throwable $error){http_response_code(409);echo json_encode(['status'=>'error','message'=>$error->getMessage()]);}
    exit;
}

if ($page === 'review_item' && $method === 'POST') {
    require_role($user,['reviewer']);
    $id=$_GET['item']??'';
    $form=['decision'=>$_POST['decision']??'','comments'=>$_POST['comments']??'','suggested_correction'=>$_POST['suggested_correction']??''];
    try { submit_review_php($pdo,$id,(int)$user['id'],$form['decision'],$form['comments'],$form['suggested_correction']); flash('Review recorded.'); redirect('index.php?page=review_item&item='.$id); }
    catch(Throwable $error){ page_review_item($pdo,$user,$id,$error->getMessage(),$form); exit; }
}

if ($page === 'admin_users' && $method === 'POST') {
    require_role($user,['admin']);
    try { create_user_php($pdo,$_POST['username']??'',$_POST['display_name']??'',$_POST['role']??'',$_POST['password']??'',(int)$user['id']); flash('User created.'); redirect('index.php?page=admin_users'); }
    catch(Throwable $error){ page_admin_users($pdo,$user,$error->getMessage(),$_POST); exit; }
}

if ($page === 'admin_assign' && $method === 'POST') {
    require_role($user,['admin']);
    $type=$_POST['assignment_type']??''; $uid=(int)($_POST['user_id']??0); $limit=max(1,min(200,(int)($_POST['limit']??10)));
    try { if($type==='translation') $count=bulk_assign_translation_php($pdo,$uid,$limit,(int)$user['id']); elseif($type==='review') $count=bulk_assign_review_php($pdo,$uid,$limit,(int)$user['id']); else throw new RuntimeException('Choose translation or review work.'); flash('Assigned '.$count.' items.'); redirect('index.php?page=admin_assign'); }
    catch(Throwable $error){ page_admin_assign($pdo,$user,$error->getMessage()); exit; }
}

if ($page === 'admin_item' && $method === 'POST') {
    require_role($user,['admin']);
    $id=$_GET['item']??''; $action=$_POST['action']??'';
    try {
        if($action==='return_translation'){
            $t=translation_row($pdo,$id); if(!$t) throw new RuntimeException('No translation exists.');
            $reason=trim($_POST['reason']??''); if($reason==='') throw new RuntimeException('Explain what needs correction.');
            pdo_query($pdo,"UPDATE translations SET status='needs_revision',resolution_required=0,resolution_reason=?,updated_at=? WHERE item_id=?",[$reason,now_iso(),$id]);
            audit($pdo,(int)$user['id'],'translation_returned_for_correction','item',$id,['reason'=>$reason]); flash('Returned for correction.'); redirect('index.php?page=admin_item&item='.$id);
        }
        if($action==='resolve'){
            $t=translation_row($pdo,$id); if(!$t) throw new RuntimeException('No translation exists.');
            $decision=$_POST['decision']??''; $notes=trim($_POST['notes']??''); if(!in_array($decision,['approved','needs_revision'],true)||$notes==='') throw new RuntimeException('Choose a resolution and explain it.');
            pdo_query($pdo,'INSERT INTO resolutions(item_id,translation_version,admin_id,decision,notes,created_at) VALUES (?,?,?,?,?,?)',[$id,(int)$t['version'],(int)$user['id'],$decision,$notes,now_iso()]);
            pdo_query($pdo,'UPDATE translations SET status=?,resolution_required=0,resolution_reason=\'\',updated_at=? WHERE item_id=?',[$decision==='approved'?'reviewed':'needs_revision',now_iso(),$id]);
            audit($pdo,(int)$user['id'],'disagreement_resolved','item',$id,['decision'=>$decision]); flash('Disagreement resolved.'); redirect('index.php?page=admin_item&item='.$id);
        }
        throw new RuntimeException('Unknown item action.');
    } catch(Throwable $error){ page_admin_item($pdo,$user,$id,$error->getMessage()); exit; }
}

if ($page === 'admin_payments' && $method === 'POST') {
    require_role($user,['admin']);
    try { record_payment_php($pdo,(int)($_POST['recipient_id']??0),$_POST['role']??'',(float)($_POST['amount']??0),$_POST['note']??'',(int)$user['id']); flash('Payment cleared and recorded.'); redirect('index.php?page=admin_payments'); }
    catch(Throwable $error){ page_admin_payments($pdo,$user,$error->getMessage()); exit; }
}

switch ($page) {
    case 'home': page_home($pdo,$user); break;
    case 'work': require_role($user,['translator']); page_work_list($pdo,$user); break;
    case 'work_item': page_work_item($pdo,$user,$_GET['item']??''); break;
    case 'progress': require_role($user,['translator']); page_progress($pdo,$user); break;
    case 'review': require_role($user,['reviewer','admin']); page_review_list($pdo,$user); break;
    case 'review_item': require_role($user,['reviewer','admin']); page_review_item($pdo,$user,$_GET['item']??''); break;
    case 'rewards': require_role($user,['translator','reviewer']); page_rewards($pdo,$user); break;
    case 'admin': require_role($user,['admin']); page_admin_home($pdo,$user); break;
    case 'admin_users': require_role($user,['admin']); page_admin_users($pdo,$user); break;
    case 'admin_assign': require_role($user,['admin']); page_admin_assign($pdo,$user); break;
    case 'admin_items': require_role($user,['admin']); page_admin_items($pdo,$user); break;
    case 'admin_item': require_role($user,['admin']); page_admin_item($pdo,$user,$_GET['item']??''); break;
    case 'admin_payments': require_role($user,['admin']); page_admin_payments($pdo,$user); break;
    case 'admin_audit': require_role($user,['admin']); page_admin_audit($pdo,$user); break;
    default: page_error(404,'Page not found.');
}
