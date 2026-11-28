# Security Policy

## Reporting a vulnerability

Use [GitHub's private advisory form](https://github.com/komaksym/prc/security/advisories/new)
to report a suspected vulnerability directly to the maintainers.

Include the affected commit, reproduction steps, impact, and any relevant
logs. Remove GitHub tokens, private repository data, and personal information
before sending evidence. You should receive an initial response within seven
days.

## Supported versions

| Version | Supported |
| --- | --- |
| `main` | Yes |
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
