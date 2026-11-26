## Summary

<!-- What does this change, and why is it needed? -->

## Related issue

<!-- Link the issue, or explain why none is needed. -->

## Verification

<!-- List the exact commands run and their results. -->

- [ ] `make lint`
- [ ] `make typecheck`
- [ ] `make test`

## Scope checklist

- [ ] Added or updated tests for behavior changes.
- [ ] Updated relevant documentation.
- [ ] Added an entry under **Unreleased** in `CHANGELOG.md`.
- [ ] Kept the core standard-library-only; optional dependencies stay in extras.
- [ ] Removed secrets, generated databases, caches, and build artifacts.
- [ ] No off-machine data transfer was added without explicit documentation.

## Compatibility

<!-- Describe public API, CLI, API, file-format, or Python-version impact.
     Breaking changes need a migration path and maintainer agreement. -->
