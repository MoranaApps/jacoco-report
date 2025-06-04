# 📦 Modules & Unknown Module

This document explains how the `jacoco-report` GitHub Action uses **modules** to group JaCoCo reports, how to configure them, and what happens when a module is not detected.

---

## 🧩 What is a Module?

A **module** is a logical group representing a part of your codebase (e.g., `api`, `core`, `utils`).
Modules are typically defined by their path within the project and used to segment coverage analysis.

### 🔍 Why Use Modules?
- Split large codebases into manageable coverage reports
- Customize thresholds per module
- Generate per-module PR comments

---

## 🛠️ Defining Modules

Use the `modules` input to define module names and their associated paths:

```yaml
with:
  comment-mode: modules
  modules: |
    api:src/api
    core:src/core
```

This maps coverage reports located under `src/api` to the `api` module, and `src/core` to `core`.

> Paths must be exact prefixes or pattern-matching base folders used in report generation.

---

## 🎯 Module Thresholds

You can configure **per-module thresholds** using the `modules-thresholds` input:

```yaml
with:
  modules-thresholds: |
    api:85/60/100
    core:90/70/100
```

Threshold format:
- `overall/changed-average/per-file`
- Each part is a percentage (0–100)

---

## ❓ Unknown Module

When the Action cannot match a JaCoCo report to any user-defined module, it assigns it to the **`Unknown`** module.

### 🧠 Causes
- The report path doesn’t match any defined module path
- Missing or incorrect `modules` definition

### 💡 How to Fix
- Ensure all report paths are mapped in the `modules` input
- Use consistent folder structures and verify them during CI run

```yaml
modules: |
  core:src/core
  api:src/api
```

If a report file lives in `src/misc`, and no module is defined for it, it will be listed under `Unknown`.

---

## ✅ Tips
- Keep module names short and readable
- Ensure your paths match exactly where reports are created
- Use baseline paths per module if comparing historical runs

---

See also:
- [Modes & Transitions](modes-and-transitions.md)
- [Threshold Format & Validation](thresholds.md)
