# Security Policy

## Supported Versions

Pulse is currently in early development.

Security fixes are applied to the latest released version and the current `main` branch. Older releases may not receive security updates.

## Reporting a Vulnerability

Please do not report security vulnerabilities through public GitHub issues.

If you believe you have found a security vulnerability in Pulse, report it privately by contacting:

**afrokid010404@gmail.com**

Please include, where possible:

- a description of the vulnerability;
- the affected component or configuration;
- steps to reproduce the issue;
- the potential impact;
- any suggested mitigation or fix.

Do not include API keys, access tokens, credentials, private podcast feeds, or other secrets in the report.

I will make a reasonable effort to acknowledge valid reports, investigate the issue, and coordinate a fix before public disclosure.

## Scope

Security reports are especially useful for issues involving:

- credential or secret exposure;
- Cloudflare Worker, D1, R2, or Vectorize access;
- unsafe handling of provider API keys;
- unauthorized access to podcast configuration or generated content;
- command execution or injection;
- dependency vulnerabilities with a demonstrated impact on Pulse;
- accidental exposure of private feed URLs or deployment configuration.

General bugs, feature requests, and reliability issues should be reported through GitHub Issues instead.