# 📑 Modes & Transitions

This document explains the three supported reporting modes of the `jacoco-report` GitHub Action, how they behave, and what happens when mode transitions occur across PR updates.

---

## 🎛️ Supported Modes

| Mode      | Description                                                                 |
|-----------|-----------------------------------------------------------------------------|
| `single`  | Default mode. Assumes a single JaCoCo XML report.                          |
| `multi`   | Automatically detects and merges multiple JaCoCo XML reports.             |
| `modules` | Aggregates reports under user-defined modules (via paths).                |

---

### 🔹 `single` Mode
- Simplest setup.
- Only one report file is expected (or first matching file used).
- Use for small projects or when one coverage file is generated per run.

### 🔹 `multi` Mode
- Automatically detects all matching `*.xml` files.
- Aggregates their results into a unified report.
- Suitable for monorepos or builds that output multiple reports in distinct folders.

### 🔹 `modules` Mode
- Groups JaCoCo reports into logical modules defined in the `modules` input.
- Supports module-specific thresholds via `modules-thresholds`.
- Allows per-module comments and better granularity for large codebases.

---

## 🔄 Mode Transitions

Mode transitions refer to changes in the selected reporting mode during the lifetime of a pull request — for example, when switching from `multi` to `modules`.

### 🔁 Transition Triggers
- Manual changes in the `comment-mode` input.
- Automatic detection logic based on the presence of `modules`.

### 🧠 Behavior
- The GitHub Action attempts to detect if a previous comment exists and whether it belongs to the same mode.
- If modes differ, it posts a new comment for the current mode (to avoid overwriting an incompatible format).
- This ensures clarity across updates, but can lead to multiple comments if modes fluctuate.

### 🧭 Tips
- Avoid switching modes mid-review unless needed.
- Prefer stable configuration across PR lifecycle.
- If you use `modules`, make sure the `modules` input is reliably set and matched.

---

## 📝 Example

```yaml
with:
  comment-mode: modules
  modules: |
    api:src/api
    core:src/core
  modules-thresholds: |
    api:85/60/100
    core:90/70/100
```

In this setup, two modules will be reported separately with their own thresholds.

---

See also:
- [Modules & Unknown Module](modules.md)
- [Threshold Format & Validation](thresholds.md)
