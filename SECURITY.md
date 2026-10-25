# Security Policy

## Reporting a vulnerability

Do not open a public issue for a suspected vulnerability. Contact the
maintainer privately through their [GitHub profile](https://github.com/komaksym)
to request a private reporting channel.

If GitHub shows a **Report a vulnerability** action on this repository's
Security tab, use that private advisory form.

Include the affected commit, reproduction steps, impact, and any relevant
logs. Remove GitHub tokens, private repository data, and personal information
before sending evidence. You should receive an initial response within seven
days.

## Supported versions

| Version | Supported |
| --- | --- |
| `main` and latest release | Yes |
| Older commits and local forks | Best effort |

## Security boundary

Prc reads untrusted pull request code, diffs, repository metadata, and board
files. Reports about token exposure, unsafe file handling, path traversal,
command execution, or untrusted HTML in generated output are in scope.

Fixture output demonstrates the renderer. It is not evidence about a live pull
request.

## Disclosure

Please allow time for a fix before public disclosure. When appropriate, the
maintainer will credit the reporter in the release notes unless the reporter
asks to remain anonymous.
