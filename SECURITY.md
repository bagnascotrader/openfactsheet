# Security policy

## Reporting a vulnerability

Please report security issues privately through GitHub's
**private vulnerability reporting** (repository → *Security* → *Report a
vulnerability*). Do not open a public issue for security problems.

Include a description, affected versions, and steps to reproduce. We aim to
acknowledge reports within 7 days.

## Scope and design commitments

- OpenFactsheet is **local-first**: core analysis never sends return data to a
  third party. Any future cloud or LLM integration will be opt-in and documented.
- Input parsing (CSV, Excel, pasted text) treats files as untrusted data; report
  parser crashes or resource-exhaustion issues as security bugs.
- HTML reports escape all user-supplied text (names, labels).
- Never commit private return histories or credentials; the repository's
  `.gitignore` excludes common secret files and a `data/private/` folder, and a
  `detect-secrets` pre-commit hook scans every commit.
