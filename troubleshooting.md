# 🛠 Troubleshooting Guide

This guide helps you resolve common issues when using the `jacoco-report` GitHub Action.

---

## ❌ No Coverage Found

### 🔍 Symptoms
- Output shows `No JaCoCo XML reports found`.

### ✅ Fixes
- Ensure the `paths` input matches actual report file locations.
- Use absolute or glob paths: `**/jacoco.xml`, `**/reports/**/*.xml`
- Validate that the coverage tool (e.g., Gradle or Maven) is producing the report before the action runs.

---

## ❓ Unknown Module Appears

### 🔍 Symptoms
- One or more reports show up under `Unknown`.

### ✅ Fixes
- Define matching entries in `modules` input.
- Ensure the report file paths start with one of the listed module paths.
- Double-check spelling and slashes in path names.

---

## 🟡 Mode Unexpected / Misaligned

### 🔍 Symptoms
- Mode used in comment output does not match what you configured.

### ✅ Fixes
- Explicitly set `comment-mode: single | multi | modules`.
- Avoid relying only on auto-detection if results are inconsistent.

---

## 🚫 Action Doesn’t Fail PR Despite Low Coverage

### 🔍 Symptoms
- Coverage is below thresholds, but job still passes.

### ✅ Fixes
- Ensure `fail-on-threshold` is set to `true` or includes relevant keys.
- Check actual threshold values (must be valid percentages).
- Module thresholds only apply in `modules` mode.

---

## 🧪 YAML Errors / Misconfiguration

### 🔍 Symptoms
- GitHub fails to parse workflow or errors occur at runtime.

### ✅ Fixes
- Use `|` for multi-line values (e.g. `modules`, `modules-thresholds`).
- Ensure proper indentation under `with:` block.
- Validate your YAML with online linters if needed.

---

## 🧾 Debugging Tips

Enable debug mode for more verbose logging:
```yaml
with:
  debug: true
```
Or set this in your GitHub workflow environment:
```yaml
env:
  ACTIONS_RUNNER_DEBUG: true
```

This outputs additional internal logs that may help isolate issues.

---

See also:
- [README](../README.md)
- [Thresholds](thresholds.md)
- [Modules](modules.md)
- [Modes](modes-and-transitions.md)
