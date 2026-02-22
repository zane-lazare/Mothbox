# Fix FormatOptionsPanel PR Review Issues

**Issue**: #442 (PR #467 review feedback)
**Date**: 2026-02-22
**Status**: Design approved

## Review Issues Addressed

| # | Issue | Fix |
|---|-------|-----|
| 1 | `as never` casts bypass type safety | Remove all casts — `register('validate')` etc. already valid on the union Path type |
| 2 | `options` dep in useEffect fires every render | Remove `options` from dep array, use eslint-disable with justification |
| 3 | Stale options spread in format switch | Don't spread `options` into new format defaults — use clean defaults only |
| 4 | `getExportDefaults` reads localStorage every render | Cache GPS precision once with `useMemo` at component mount |
| 5 | `typeof FORMAT_VALUES[number]` parenthesization | Fix to `(typeof FORMAT_VALUES)[number]` in schema file |
| T1 | No format-switching test | Add test: rerender with new format, verify fields and onChange |
| T2 | No options override test across switch | Add test: verify gps_precision preserved via cached value |
| T3 | No `getExportDefaults` test | Add direct test in schema test file |
