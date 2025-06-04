# 🎯 Threshold Format & Validation

This document explains how to use thresholds in the `jacoco-report` GitHub Action to control when PRs should fail or pass based on code coverage results.

---

## 🧮 Why Use Thresholds?

Thresholds allow you to:
- Prevent merging code with insufficient coverage
- Customize tolerance levels per module or file
- Control evaluation for changed files vs full project

---

## 📐 Threshold Types

You can set thresholds globally or per module.

### 🔹 Global Thresholds
These apply across the entire project.
```yaml
with:
  min-coverage-overall: 85
  min-coverage-changed-files: 70
  min-coverage-per-changed-file: 50
```

### 🔸 Module Thresholds
Use `modules-thresholds` to define rules per module:
```yaml
with:
  modules-thresholds: |
    api:85/60/100
    core:90/70/100
```

Each line format:
- `module-name: overall/changed-files-average/per-file`
- All values are percentages (0–100)

---

## ⚠️ `fail-on-threshold`

This input determines whether to fail the job based on unmet thresholds.
It accepts:

- `true`: Fail if **any** threshold is not met
- `false`: Never fail based on thresholds
- List of keys:
  - `overall`
  - `changed-files-average`
  - `per-changed-file`

### ✅ Examples
```yaml
fail-on-threshold: true
```
```yaml
fail-on-threshold: |
  overall
  per-changed-file
```

---

## 🛠 Threshold Evaluation Order

1. **Overall** project coverage is checked
2. **Changed files** (average)
3. **Each changed file** individually
4. If in `modules` mode: checks are repeated per module

---

## 🧪 Common Pitfalls

| Issue                          | Fix                                                                 |
|--------------------------------|----------------------------------------------------------------------|
| Thresholds not respected       | Ensure correct numeric values (0–100)                                |
| Action doesn’t fail PR         | Check `fail-on-threshold` is set to `true` or includes correct keys |
| Module thresholds ignored      | Ensure `comment-mode` is set to `modules` and module names match    |

---

See also:
- [Modules](modules.md)
- [Modes & Transitions](modes-and-transitions.md)
