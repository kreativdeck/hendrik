<?php

declare(strict_types=1);


/*
|--------------------------------------------------------------------------
| Kontaktformular – Konfiguration
|--------------------------------------------------------------------------
|
| Diese Werte bei einem neuen Kundenprojekt anpassen.
|
*/

const CONTACT_RECIPIENT_EMAIL = 'kontakt@deinedomain.de';
const CONTACT_SENDER_EMAIL = 'website@deinedomain.de';
const CONTACT_SENDER_NAME = 'Website Kontaktformular';

const CONTACT_SUBJECT = 'Neue Nachricht über das Kontaktformular';


/*
|--------------------------------------------------------------------------
| Autoresponder – Konfiguration
|--------------------------------------------------------------------------
|
| Automatische Empfangsbestätigung an den Absender des Formulars.
|
*/

const AUTORESPONDER_ENABLED = true;

const AUTORESPONDER_SENDER_NAME = 'Ihr Unternehmen';
const AUTORESPONDER_SUBJECT = 'Vielen Dank für Ihre Nachricht';

const AUTORESPONDER_MESSAGE = "Vielen Dank für Ihre Nachricht.

Wir haben Ihre Nachricht erhalten und werden uns in Kürze bei Ihnen melden.
Mit freundlichen Grüßen
Ihr Unternehmen";


/*
|--------------------------------------------------------------------------
| Limits
|--------------------------------------------------------------------------
*/

const MAX_NAME_LENGTH = 120;
const MAX_EMAIL_LENGTH = 254;
const MAX_MESSAGE_LENGTH = 5000;
const MAX_REQUEST_SIZE = 32768;


/*
|--------------------------------------------------------------------------
| Response
|--------------------------------------------------------------------------
*/

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');


/*
|--------------------------------------------------------------------------
| Hilfsfunktionen
|--------------------------------------------------------------------------
*/

function respond(int $statusCode, string $message): never
{
    http_response_code($statusCode);

    echo json_encode(
        ['message' => $message],
        JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES
    );

    exit;
}


function getPostString(string $key): string
{
    $value = $_POST[$key] ?? '';

    if (!is_string($value)) {
        return '';
    }

    return trim(str_replace("\0", '', $value));
}


function textLength(string $value): int
{
    if (function_exists('mb_strlen')) {
        return mb_strlen($value, 'UTF-8');
    }

    return strlen($value);
}


function encodeMailHeader(string $value): string
{
    if (function_exists('mb_encode_mimeheader')) {
        return mb_encode_mimeheader(
            $value,
            'UTF-8',
            'B',
            "\r\n"
        );
    }

    return '=?UTF-8?B?' . base64_encode($value) . '?=';
}


/*
|--------------------------------------------------------------------------
| Request prüfen
|--------------------------------------------------------------------------
*/

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    header('Allow: POST');

    respond(
        405,
        'Nur POST-Anfragen sind erlaubt.'
    );
}


$contentLength = (int) ($_SERVER['CONTENT_LENGTH'] ?? 0);

if ($contentLength > MAX_REQUEST_SIZE) {
    respond(
        413,
        'Die Anfrage ist zu groß.'
    );
}


/*
|--------------------------------------------------------------------------
| Spam-Schutz – Honeypot
|--------------------------------------------------------------------------
|
| Das Formular enthält ein unsichtbares Feld:
|
| name="company_website"
|
| Normale Besucher lassen dieses Feld leer.
|
*/

$honeypot = getPostString('company_website');

if ($honeypot !== '') {
    /*
     * Bot nicht darüber informieren, dass er erkannt wurde.
     */

    respond(
        200,
        'Danke, deine Nachricht ist angekommen.'
    );
}


/*
|--------------------------------------------------------------------------
| Formulardaten
|--------------------------------------------------------------------------
*/

$name = getPostString('name');
$email = getPostString('email');
$message = getPostString('message');

$privacy = isset($_POST['privacy']);


/*
|--------------------------------------------------------------------------
| Pflichtfelder prüfen
|--------------------------------------------------------------------------
*/

if (
    $name === ''
    || $email === ''
    || $message === ''
    || !$privacy
) {
    respond(
        422,
        'Bitte alle Pflichtfelder ausfüllen.'
    );
}


/*
|--------------------------------------------------------------------------
| Feldlängen prüfen
|--------------------------------------------------------------------------
*/

if (textLength($name) > MAX_NAME_LENGTH) {
    respond(
        422,
        'Der Name ist zu lang.'
    );
}


if (textLength($email) > MAX_EMAIL_LENGTH) {
    respond(
        422,
        'Die E-Mail-Adresse ist zu lang.'
    );
}


if (textLength($message) > MAX_MESSAGE_LENGTH) {
    respond(
        422,
        'Die Nachricht ist zu lang.'
    );
}


/*
|--------------------------------------------------------------------------
| Name normalisieren
|--------------------------------------------------------------------------
*/

$name = preg_replace(
    '/[\r\n\t]+/u',
    ' ',
    $name
) ?? $name;


/*
|--------------------------------------------------------------------------
| E-Mail-Adresse prüfen
|--------------------------------------------------------------------------
*/

if (
    str_contains($email, "\r")
    || str_contains($email, "\n")
    || !filter_var($email, FILTER_VALIDATE_EMAIL)
) {
    respond(
        422,
        'Bitte eine gültige E-Mail-Adresse angeben.'
    );
}


/*
|--------------------------------------------------------------------------
| Blanco-Konfiguration prüfen
|--------------------------------------------------------------------------
*/

if (
    !filter_var(CONTACT_RECIPIENT_EMAIL, FILTER_VALIDATE_EMAIL)
    || !filter_var(CONTACT_SENDER_EMAIL, FILTER_VALIDATE_EMAIL)
) {
    respond(
        500,
        'Das Kontaktformular ist noch nicht vollständig konfiguriert.'
    );
}


/*
|--------------------------------------------------------------------------
| Kontaktmail erstellen
|--------------------------------------------------------------------------
*/

$contactSubject = encodeMailHeader(CONTACT_SUBJECT);

$contactBody = implode(
    "\n",
    [
        'Neue Nachricht über das Kontaktformular',
        '',
        'Name:',
        $name,
        '',
        'E-Mail:',
        $email,
        '',
        'Nachricht:',
        $message,
        '',
        'Datenschutz bestätigt:',
        'Ja',
    ]
);


/*
|--------------------------------------------------------------------------
| Header für Kontaktmail
|--------------------------------------------------------------------------
*/

$contactSenderName = encodeMailHeader(CONTACT_SENDER_NAME);

$contactHeaders = [
    'MIME-Version: 1.0',
    'Content-Type: text/plain; charset=UTF-8',
    'Content-Transfer-Encoding: 8bit',
    'From: ' . $contactSenderName . ' <' . CONTACT_SENDER_EMAIL . '>',
    'Reply-To: ' . $email,
];


/*
|--------------------------------------------------------------------------
| Kontaktmail an Website-Betreiber senden
|--------------------------------------------------------------------------
*/

$contactSent = @mail(
    CONTACT_RECIPIENT_EMAIL,
    $contactSubject,
    $contactBody,
    implode("\r\n", $contactHeaders)
);


/*
|--------------------------------------------------------------------------
| Fehler beim Hauptversand
|--------------------------------------------------------------------------
*/

if (!$contactSent) {
    respond(
        500,
        'Die Nachricht konnte momentan nicht gesendet werden. Bitte versuche es später erneut.'
    );
}


/*
|--------------------------------------------------------------------------
| Autoresponder erstellen und an Besucher senden
|--------------------------------------------------------------------------
|
| WICHTIG:
|
| Empfänger des Autoresponders ist $email.
|
| Damit erhält der Besucher automatisch die Empfangsbestätigung.
|
*/

if (AUTORESPONDER_ENABLED) {
    $autoresponderSubject = encodeMailHeader(
        AUTORESPONDER_SUBJECT
    );

    $autoresponderSenderName = encodeMailHeader(
        AUTORESPONDER_SENDER_NAME
    );

    $autoresponderHeaders = [
        'MIME-Version: 1.0',
        'Content-Type: text/plain; charset=UTF-8',
        'Content-Transfer-Encoding: 8bit',
        'From: ' . $autoresponderSenderName . ' <' . CONTACT_SENDER_EMAIL . '>',
        'Reply-To: ' . CONTACT_RECIPIENT_EMAIL,
        'Auto-Submitted: auto-replied',
        'X-Auto-Response-Suppress: All',
    ];

    @mail(
        $email,
        $autoresponderSubject,
        AUTORESPONDER_MESSAGE,
        implode("\r\n", $autoresponderHeaders)
    );
}


/*
|--------------------------------------------------------------------------
| Erfolg
|--------------------------------------------------------------------------
*/

respond(
    200,
    'Danke, deine Nachricht ist angekommen.'
);