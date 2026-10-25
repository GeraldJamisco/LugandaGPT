<?php
// Local XAMPP default. On cPanel, change this to a path outside public_html
// or use the STUDIO_DB environment variable if your host supports it.
$defaultDb = dirname(__DIR__) . DIRECTORY_SEPARATOR . 'data' . DIRECTORY_SEPARATOR . 'studio' . DIRECTORY_SEPARATOR . 'studio.sqlite3';

return [
    'db_path' => getenv('STUDIO_DB') ?: $defaultDb,
    'app_name' => 'LugandaGPT Translation Studio',
    'session_name' => 'lugandagpt_studio_php',
];
