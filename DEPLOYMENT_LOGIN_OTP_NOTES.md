# V4Career login OTP and proxy deployment notes

## Login OTP recipient
The OTP recipient is resolved from `ADMIN_EMAIL` or `USER_EMAIL` in the server environment.
Set `ADMIN_EMAIL` to the company email address for admin OTP delivery (and `USER_EMAIL` for the user account if desired).
Do not change `SMTP_USERNAME`/`SMTP_FROM` unless changing the sending mailbox/provider; these are sender credentials, not the OTP recipient.
After changing environment values, redeploy/restart the service.

## Client IP behind Render
The app now uses Werkzeug ProxyFix and `request.remote_addr` for audit IP.
Set `TRUSTED_PROXY_HOPS=1` only after verifying the service has exactly one trusted proxy hop. Never trust arbitrary client-supplied forwarded headers.
IP-derived location remains approximate and may map Neyveli to Chennai or another nearby ISP region.

## Required Render variables
- `ADMIN_EMAIL=your-company-admin-email`
- `TRUSTED_PROXY_HOPS=1` (verified topology only)
- `IP_GEOLOCATION_ENABLED=true`
