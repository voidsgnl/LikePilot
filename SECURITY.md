# Security Policy

## Supported versions

Security fixes are currently made against the latest code on the `main` branch. There are no separately maintained release branches yet.

## Reporting a vulnerability

Please do not report exploitable vulnerabilities in public issues, discussions, or pull requests.

Use GitHub's private vulnerability reporting feature for this repository if it is enabled. Otherwise, contact the maintainer privately through the GitHub profile associated with this repository.

Include:
- A concise description of the vulnerability and its potential impact.
- The affected version or commit, component, and configuration.
- Reproduction steps or a minimal proof of concept.
- Any suggested mitigation, if known.

Do not include real credentials, session cookies, access tokens, personal data, or other users' information in a report. Allow the maintainer reasonable time to investigate and prepare a fix before public disclosure.

## Security expectations

LikePilot can access browser sessions and store account-related credentials and runtime data. Treat its runtime directory, backups, browser profiles, and logs as sensitive. Keep the dashboard bound to localhost unless a separately secured deployment architecture is in place. The built-in numeric vault is not suitable as the sole authentication control for an internet-facing service.

Only use LikePilot with accounts and services you are authorized to access. Users are responsible for complying with applicable laws and the terms of connected services.
