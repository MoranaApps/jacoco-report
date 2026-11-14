# #276: rozpracováno, čeká na rozhodnutí

Stav k 2026-11-13:

- Větev `refactor/276-pylint-fail-on-any-message` je vytvořená z aktuálního `master` (ab2b7d7). Zatím na ní nejsou žádné změny.
- Issue #276 je zastaralé. Před implementací je potřeba odsouhlasit jeho nové znění a dvě rozhodnutí (A, B).

## Co v issue nesedí (ověřeno pylintem 4.0.5)

| Issue říká | Skutečnost |
|---|---|
| 4 globální disable | Jsou jen 3: `too-many-branches`, `too-many-statements`, `too-many-public-methods`. `too-many-arguments` už vrátilo #271. |
| 2× `line-too-long` | Zbývá jen 1, na `jacoco_report/evaluator/coverage_evaluator.py:321` (komentář). |
| `too-many-locals` (`run()` 47, `validate_inputs()` 21) | Už neexistuje, vyřešily ho #272–#275. |
| `too-many-instance-attributes` (`CoverageEvaluator` 17/15) | Stále platí. |
| — | Po odstranění disable se objeví `too-many-public-methods` (`ActionInputs` 29/20, `action_inputs.py:173`) a `too-many-branches` (`JaCoCoReport._collect_baseline_reports()` 15/12, `jacoco_report.py:363`). `too-many-statements` nehlásí nic. |
| „CI: fail on pylint's exit code“ | Nestačí. `.pylintrc` má `fail-under=9.5`, takže pylint vrací 0 i při hlášených problémech. Je potřeba `fail-under=10`. |
| Lokální `# pylint: disable` pro `ActionInputs` | Odporuje pravidlu „žádný inline disable“ v `CONTEXT.md:139` a `.github/copilot-instructions.md:47`. |

## Rozhodnutí, která jsou potřeba

**A) `ActionInputs`, 29 veřejných metod (limit 20)**

- **a) (doporučuji)** Lokální `# pylint: disable=too-many-public-methods` přímo na třídě s důvodem (jedna metoda na každý vstup, záměrně). Pravidlo v `CONTEXT.md` a v `.github/copilot-instructions.md` se upraví tak, aby odůvodněnou výjimku na úrovni třídy povolovalo.
- b) Globálně nastavit `max-public-methods=30`. Nevýhoda: bez povšimnutí pak projdou i jiné třídy s 21–30 metodami.

**B) `CoverageEvaluator`, 17 atributů instance (limit 15)**

- **a) (doporučuji)** Refaktor bez změny veřejných atributů a konstruktoru:
  - zrušit `_group_thresholds_lookup`, protože duplikuje fallback logiku prahů z `evaluate_group()`. `_set_thresholds()` a `evaluate_group()` pak použijí stejnou pomocnou funkci, takže se prahy skupiny počítají jen na jednom místě;
  - sloučit `_global_min_coverage_overall` a `_global_min_coverage_changed_files` do jedné n-tice `_global_thresholds` (stejný tvar jako `_report_thresholds_default`).
- b) Odůvodněný lokální disable: třída drží vstupy i veřejné výsledky, které čte `PRCommentGenerator` a `main.py`.

Omezení, která musí každá varianta dodržet:

- `report_group_order` musí zůstat zapisovatelný atribut. `tests/unit/generator/test_pr_comment_generator.py:398` ho nastavuje na skutečném `CoverageEvaluator`, takže ho nejde převést na property.
- `evaluate_group(evaluated, group)` si musí ponechat signaturu s `ReportGroup`, protože ho tak volá `tests/unit/evaluator/test_coverage_evaluator.py:219`.

**Bez rozhodování:**

- `_collect_baseline_reports()`: větev pro skupiny se přesune do vlastní metody, stejně jako v #274/#275.
- Dlouhý řádek s komentářem se zalomí.

## Návrh nového znění issue (při A=a, B=a)

```markdown
Part of #254.

## Problem

- `.pylintrc` disables `too-many-branches`, `too-many-statements` and `too-many-public-methods` globally, so new violations pass silently. (`too-many-arguments` was re-enabled in #271.)
- `fail-under=9.5`: pylint exits 0 while the score stays ≥ 9.5, and CI only checks that score. Two messages pass unnoticed today: `line-too-long` (`coverage_evaluator.py:321`) and `too-many-instance-attributes` (`CoverageEvaluator`, 17/15).
- Removing the disables surfaces two more: `too-many-public-methods` (`ActionInputs`, 29/20) and `too-many-branches` (`JaCoCoReport._collect_baseline_reports()`, 15/12).

## Fix

- Remove the three global disables and the tech-debt comment block.
- `ActionInputs` (one getter per input by design): local `# pylint: disable=too-many-public-methods` on the class with that reason. No split. Allow such a justified class-level exception in the "no inline disable" rule (`CONTEXT.md`, `.github/copilot-instructions.md`).
- `CoverageEvaluator`: drop `_group_thresholds_lookup` (one place resolves a group's thresholds) and hold the two global minimums in one tuple; public attributes unchanged.
- `_collect_baseline_reports()`: extract the per-group branch into its own method.
- Wrap the long comment line.
- `.pylintrc`: `fail-under=10`, so pylint exits non-zero on any message. CI: run pylint and use its exit code; drop the score-parsing step. Update the 9.5 mentions (`DEVELOPER.md`, `AGENTS.md`, `CONTEXT.md`).

## Acceptance criteria

- [ ] `pylint $(git ls-files '*.py')` exits 0 with no messages.
- [ ] pylint exits non-zero when one warning is added (locally and in CI, tried once).

## Depends on

#270–#275 (all closed).

Debt ref: JR-06 (4/4), JR-17 (score gate; the matrix part was done in #238).
```

## Místa, kterých se změna dotkne

- `.pylintrc`:
  - z `disable=` odebrat `too-many-branches`, `too-many-statements` a `too-many-public-methods`;
  - smazat blok komentářů „Tech-debt suppressions“;
  - nastavit `fail-under=10`.
- `.github/workflows/static_analysis_and_tests.yml:66-82`: krok „Analyze code with Pylint“ bude jen spouštět `pylint "${py_files[@]}"`; krok „Check Pylint score“ odpadne.
- `jacoco_report/action_inputs.py:173`, `jacoco_report/evaluator/coverage_evaluator.py`, `jacoco_report/jacoco_report.py:363`.
- Dokumentace se zmínkou o skóre 9.5 nebo o zákazu inline disable:
  - `DEVELOPER.md:161`, `DEVELOPER.md:173`;
  - `AGENTS.md:69` (sekce „This project“);
  - `CONTEXT.md:139`, `CONTEXT.md:223`;
  - `.github/copilot-instructions.md:47`.

## Další kroky

1. Rozhodnout A a B a schválit znění issue. Pak issue aktualizovat přes `gh issue edit 276`.
2. Implementovat na větvi postupem test-first a ověřit pomocí `make check`.
3. Spustit context check: `bash .claude/skills/context-md/check.sh`.
4. Připravit text commitu, název a popis PR (bez commitu).
5. Akceptační kritérium s CI ověřit ručně: v PR dočasně přidat jedno varování a zkontrolovat, že job selže.

Tento soubor necommitovat. Není v `.gitignore`, po dokončení ho smažte.
