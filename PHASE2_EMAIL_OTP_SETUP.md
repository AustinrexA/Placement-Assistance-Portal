# Phase 2 — Email OTP (built on the newly uploaded ZIP)

## SMTP environment
Keep the private `.env` out of Git. Configure these variables locally and in Render:
`ADMIN_EMAIL`, `USER_EMAIL`, `SMTP_HOST=smtp.gmail.com`, `SMTP_PORT=587`,
`SMTP_USERNAME` (sending Gmail), `SMTP_PASSWORD` (Gmail App Password),
`SMTP_FROM` (same sender Gmail), `SMTP_USE_TLS=true`,
`OTP_TTL_SECONDS=300`, `OTP_RESEND_SECONDS=60`, `OTP_MAX_ATTEMPTS=5`.

Existing `ADMIN_USERNAME` and `USER_USERNAME` settings are used to map the configured email to the role. Role is never supplied by the login form.

## Flow
1. Login form accepts email only; `/login` sends OTP.
2. `/verify-otp` verifies code, expiry, and attempt limit.
3. `/resend-otp` enforces cooldown.
4. Role is resolved from server configuration; successful login sets authenticated session and preserves the existing login audit write.
5. `/logout` clears session.

## Deploy
Set the environment variables in Render Dashboard → V4Career service → Environment, then redeploy. Never commit SMTP credentials.


## Password login (restored)
Password login and Email OTP are both available on `/login`. Configure account passwords in `.env`:
- `ADMIN_PASSWORD=...`
- `USER_PASSWORD=...`

For production, prefer password hashes:
- `ADMIN_PASSWORD_HASH=...`
- `USER_PASSWORD_HASH=...`
Generate a hash in Python with `from werkzeug.security import generate_password_hash; print(generate_password_hash("your-password"))`.
If a hash is configured, it takes precedence over the plain password variable. Keep these secrets out of Git.
