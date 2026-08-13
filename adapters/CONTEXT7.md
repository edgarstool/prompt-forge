# Context7 Adapter (policy only in local v0.1)

Local pipeline does **not** call Context7 network APIs yet.

`context_policy` only decides:

- whether the composed prompt must require Context7 / official docs
- why that decision was made

Network adapter wiring is intentionally out of EDG-342 scope.
