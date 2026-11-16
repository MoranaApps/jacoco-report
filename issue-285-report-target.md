# Issue #285: `report-target`, jak se akce chová a jak má reagovat

Podklad pro implementaci v další session. Soubor je untracked a necommituje se.

- Issue: <https://github.com/MoranaApps/jacoco-report/issues/285> (epic #284, cíl v3.5.0)
- Branch: `feat/285-report-target` (lokální, z `origin/master` e1943f6), bez commitu
- Odsouhlaseno 2026-11-16:
  1. Text issue se přepíše. #266 je hotové, takže dlouhý komentář se ořízne. Summary je místo pro celý report.
  2. Akceptační kritérium pro self-test se nahradí (sekce G).
  3. Poznámka o oříznutí komentáře v režimu `both` odkazuje na job summary.
  4. `summary` nikdy nevolá comment API. Starý komentář na PR zůstane, `update-comment` se ignoruje a do logu jde info.
  5. Summary nad 1 MiB se ořízne. Do job logu jde **celé tělo** a poznámka v summary na log odkazuje.
  6. Výchozí hodnota inputu je `comment`, takže při ní akce `GITHUB_STEP_SUMMARY` vůbec nečte.
  7. Výchozí hodnota zůstává `comment`. Summary je volitelný druhý kanál, ne nový standard.
  8. Rámec pro docs i issue: `report-target` je nová možnost, kam dát výstup. `summary` je zajímavé tím, že
     workflow nepotřebuje právo zápisu. **PR z forku ani Dependabota v docs nezmiňovat.**
  9. Výsledek jobu se nemění: nesplněné thresholdy a provozní chyby dál job shodí (sekce „Výsledek jobu").
  10. Neplatná hodnota `report-target` shodí validaci stejně jako ostatní inputy (D4).
  11. Stávající zmínky o PR z forku a Dependabotu se v rámci #285 odstraní z README a z hintu pro 403
      (E → „Co a kde se dokumentuje", body 4–6). Žádné follow-up issue nevzniká.

## Pojmy

- „Summary" znamená v celém souboru **job summary** běhu workflow (`$GITHUB_STEP_SUMMARY`), **ne** popis (body) PR.
  Zobrazuje se na stránce běhu (Actions → běh → Summary, pod grafem jobů). Z PR se tam dostaneš přes check → Details.
  Akce popis PR nikdy nečte ani nemění.
- Kód nepředpokládá, že je summary soubor prázdný, protože do něj jen připisuje (append). Runner ho pro každý krok
  založí prázdný a Run krok akce do něj zapíše jednou, takže limit 1 MiB se týká jen tohoto zápisu.
- `report-target`: nový input s hodnotami `comment` (výchozí), `summary` a `both`.
- `GITHUB_STEP_SUMMARY` **není input**. Runner ho nastaví sám pro každý krok jako cestu k souboru. Chybí jen
  mimo runner (lokální `make run`, testy) nebo na GHES starším než 3.6.
- Summary patří jednomu běhu a jednomu kroku. Každý běh začíná s prázdným summary, takže v něm není co mazat,
  na rozdíl od komentáře, který zůstává na PR mezi běhy. Runner navíc soubor předchozího kroku smaže, takže
  pozdější krok ho nepřečte. GitHub nemá API pro čtení summary.
- Limit komentáře je 65 536 znaků (`len()`, `MAX_COMMENT_LENGTH`). Limit summary je 1 MiB, tj. 1 048 576
  **bajtů UTF-8**: runner měří velikost souboru. Když se do něj obsah nevejde, GitHub summary kroku zahodí a vytvoří
  error anotaci. Výsledek jobu se tím nemění.
- Odkaz na běh: `{GITHUB_SERVER_URL}/{GITHUB_REPOSITORY}/actions/runs/{GITHUB_RUN_ID}`, tedy stejné URL jako ve footeru.
  Na stránce běhu je vidět job summary i job log. Bez run id nebo repository zůstane text bez odkazu.

## Základní pravidla

1. Výchozí `comment` se chová stejně jako dnes: komentáře mají stejný text a akce dělá stejná API volání.
2. Summary dostane stejný markdown jako komentář pro dané `comment-level`. Ořízne se jen na limit summary,
   nikdy na limit komentáře. Jedinou výjimkou je D1.
3. `summary` nevolá comment API, tedy žádné GET, POST, PATCH ani DELETE na komentáře. Jediné volání API je načtení
   změněných souborů PR (GET), které proběhne u všech hodnot `report-target`.
4. Pořadí je summary, potom komentář. Poznámka o oříznutí komentáře tak ví, jestli se summary podařilo zapsat.
5. Problém se summary (chybí proměnná, selže zápis) nemění výsledek jobu ani outputy. Akce jen vypíše `::warning::`,
   stejně jako dnes při selhaném komentáři.
6. Outputy akce a vyhodnocení thresholdů na `report-target` nezávisí.

## `comment-level` v obou kanálech

`comment-level` určuje, **co** report obsahuje: které tabulky a které řádky. `report-target` určuje, **kam** se
report pošle. Obě nastavení jsou na sobě nezávislá. Kanál komentáře i kanál summary dostanou stejný obsah a liší se jen limitem, na který se ořezává, a textem poznámky
o oříznutí. Název `comment-level` zůstává, protože je součástí kontraktu v3. Docs musí říct, že platí pro oba kanály.

| `comment-level` | Obsah reportu | Kanál komentáře (`comment`/`both`) | Kanál summary (`summary`/`both`) |
|-----------------|---------------|------------------------------------|----------------------------------|
| `none` | žádný report | komentář nevznikne. S `update-comment: true` se starý komentář smaže (A4, dnešní chování) | nic se nezapíše (B3) |
| `minimal` | jen globální tabulka | komentář s globální tabulkou | stejná globální tabulka |
| `full` | všechny tabulky a řádky | komentář, oříznutý nad 65 536 znaků | stejný obsah, oříznutý až nad 1 MiB |
| `changed`, `failed`, `failed-or-changed` | tabulky jen s řádky podle filtru | komentář, oříznutý nad 65 536 znaků | stejný obsah, oříznutý až nad 1 MiB |

**Výchozí hodnota `comment-level` je `full`.** `none` neznamená „nenastaveno", je to výslovná volba „žádný report".
Proto se nenahrazuje výchozí hodnotou a platí pro oba kanály. Kdo `comment-level` nenastaví, dostane `full`, takže
`report-target: summary` bez `comment-level` zapíše do summary plný report.

Kombinace stojící za zmínku:
- **`summary` + `none`:** report se nikam nezapíše. Akce jen vyhodnotí thresholdy, nastaví outputy a případně
  shodí job. Je to stejný režim jako dnešní `none` + `update-comment: false`, jen bez ohledu na `update-comment`.
  Konfigurace je platná, nevaruje se.
- **`both` + `none`:** komentářový kanál se chová jako dnes (smazání starého komentáře při `update-comment: true`)
  a summary zůstane prázdné.
- **`comment` + cokoli:** beze změny proti dnešku.

## Výsledek jobu

`report-target` mění jen to, kam report jde, ne to, kdy akce selže.

| Situace | Výsledek jobu |
|---------|---------------|
| nesplněné thresholdy (`fail-on-threshold`) | **failed**, beze změny a pro všechny targety |
| provozní chyba (D3: událost není `pull_request`, chybí číslo PR, nejsou XML, nejdou načíst změněné soubory) | **failed**, beze změny |
| neplatný input, včetně `report-target` (D4) | **failed** |
| komentář nejde zapsat (např. 403) | warning, job OK, beze změny |
| summary nejde zapsat (B5, B6) | warning, job OK |
| summary oříznuté nad 1 MiB (B4) | warning, job OK |

S `summary` a tokenem bez práva zápisu tedy nevznikne žádná chyba 403 ani warning. Thresholdy dál shazují job
jako dnes.

## A. Kanál komentáře

| #  | `report-target` | `comment-level` | `update-comment` | Komentář s title existuje | Reakce |
|----|-----------------|-----------------|------------------|---------------------------|--------|
| A1 | `comment`/`both` | ≠ `none` | `true`  | ne  | vytvoří komentář (dnešní chování) |
| A2 | `comment`/`both` | ≠ `none` | `true`  | ano | aktualizuje ho (dnešní chování) |
| A3 | `comment`/`both` | ≠ `none` | `false` | –   | přidá nový komentář a komentáře nečte (dnešní chování) |
| A4 | `comment`/`both` | `none`   | `true`  | ano | smaže ho (dnešní chování) |
| A5 | `comment`/`both` | `none`   | `true`  | ne  | jen přečte komentáře (dnešní chování) |
| A6 | `comment`/`both` | `none`   | `false` | –   | žádné volání comment API (dnešní chování) |
| A7 | `summary` | libovolné | libovolné | libovolné | žádné volání comment API. Komentář z dřívějších běhů zůstane beze změny. Jedno INFO za běh: `report-target is 'summary': no PR comment is created, updated or removed (update-comment is ignored).` |

**Důsledek A7:** kdo přejde z `comment` na `summary`, tomu na otevřených PR zůstane poslední komentář a už se
nebude aktualizovat. Do `docs/inputs/report-target.md` přidat poznámku, že takový komentář je potřeba smazat ručně.

## B. Kanál summary

| #  | Situace | Reakce |
|----|---------|--------|
| B1 | `report-target: comment` | do summary se nic nezapisuje a `GITHUB_STEP_SUMMARY` se nečte |
| B2 | `summary`/`both`, `comment-level` ≠ `none`, tělo do 1 MiB | připíše (append) celé tělo, tedy necut verzi komentáře |
| B3 | `summary`/`both`, `comment-level: none` | nic nezapíše |
| B4 | `summary`/`both`, tělo nad 1 MiB | ořízne řádky od konce stejným algoritmem jako u komentáře; celé tělo jde do job logu (viz níže) |
| B5 | `GITHUB_STEP_SUMMARY` není nastavené nebo je prázdné | `::warning::` (viz níže), job OK |
| B6 | zápis selže (`OSError`) | `logger.error` s výjimkou a stejný `::warning::` jako B5, job OK |

**B4 podrobně:**
- Používá stejné pořadí řezu i binární hledání jako komentář. Měří se v bajtech UTF-8.
- Do summary se přidá poznámka: `… N rows omitted (GitHub's 1 MiB job summary limit), the full report is in the [job log](<run URL>).`
- Do job logu jde jeden `warning` (velikost těla, limit, počet vynechaných řádků), pak jedno `info` s **celým necut tělem**
  (`Full report (job summary was cut):` + tělo). Vynechané řádky se zvlášť nelogují, protože jsou obsažené v těle.
  Záznam jde přes `WorkflowCommandSafeFormatter`, protože tělo obsahuje názvy souborů z PR.
- Když se zbytek nevejde ani bez řádků, uplatní se stejná pojistka jako u komentáře: tvrdé oříznutí na limit
  (v bajtech, nikdy uprostřed znaku UTF-8) a druhý `warning`.

**B5 text warningu:**
`report-target '<value>' writes to the job summary, but GITHUB_STEP_SUMMARY is not set (not a GitHub Actions runner, or GHES older than 3.6). The report was not written to the job summary.`

## C. Oříznutí komentáře (65 536 znaků)

| #  | Situace | Poznámka v komentáři |
|----|---------|----------------------|
| C1 | `comment` | beze změny: `… N rows omitted (GitHub's 65,536-character comment limit), see the job log.` |
| C2 | `both`, summary zapsané (B2/B4) | `… N rows omitted (GitHub's 65,536-character comment limit), see the [job summary](<run URL>).` |
| C3 | `both`, summary nezapsané (B5/B6) | jako C1 |
| C4 | `summary` | komentář nevzniká, summary má celé tělo (B2/B4) |

V C1 až C3 se vynechané řádky logují stejně jako dnes. Celé tělo se loguje jen u B4.

## D. Zvláštní průchody během

| #  | Situace | Reakce |
|----|---------|--------|
| D1 | skip-unchanged odfiltruje **všechny** reporty (`_handle_all_reports_filtered`) | viz níže |
| D2 | skip-unchanged odfiltruje **část** reportů | summary má stejný obsah jako komentář, tedy bez řádků nezměněných reportů |
| D3 | provozní chyba: událost není `pull_request`, chybí číslo PR, nejsou XML, nepodaří se načíst změněné soubory | dnes bez komentáře a job selže; summary: nic |
| D4 | neplatná hodnota `report-target` | chyba validace `'report-target' must be one of: 'comment', 'summary', 'both'.`, exit 1, stejně jako ostatní inputy |
| D5 | prázdná hodnota (`report-target: ''`) | bere se jako `comment` |

**D1 podrobně:**
- **Komentář:**
  - u `comment` a `both` se nic nemění: komentář nevznikne a starý se při `update-comment: true` smaže;
  - u `summary` se komentář **nemaže** (pravidlo 3, A7), takže `_delete_stale_comment_if_update_enabled` se přeskočí
    a zaloguje se INFO z A7.
- **Summary** (`summary`/`both`, `comment-level` ≠ `none`):
  - sekce zůstane a dostane krátkou zprávu, protože v novém summary není co mazat a prázdné summary by nevysvětlilo, proč report chybí;
  - obsah: `**<title>**`, odstavec `All reports are unchanged: skip-unchanged removed every report, so there are no coverage rows to show.` a stejný footer jako v komentáři;
  - u `comment-level: none` se nezapíše nic (B3).
- Footer tedy musí jít sestavit i bez evaluátoru. `_get_metadata_footer` čte jen `ActionInputs` a URL serveru,
  takže ho lze vytáhnout na úroveň modulu.

**D4:**
- Hodnota se nejdřív ořízne (`strip`) a převede na malá písmena (`lower`), stejně jako `global-overall-scope`.
- Chyba se řadí hned za chybu `comment-level` (`validate_inputs()`, test
  `test_validate_inputs_logs_errors_in_validation_order`).
- `_log_configuration` zaloguje hodnotu.

## E. Práva tokenu

### Pozadí

- Komentář potřebuje token s právem zápisu (`issues: write`). Summary žádné API nepotřebuje, protože jde o zápis
  do souboru na runneru. Změněné soubory PR akce čte vždy, na to stačí `contents: read` + `pull-requests: read`.
- Docs nerozebírají, proč token právo zápisu nemá (konfigurace workflow, repa nebo organizace, omezení GitHubu).
  Popisují jen, jaká práva který target potřebuje.

### Co akce udělá

| #  | Konfigurace | Výsledek |
|----|-------------|----------|
| E1 | `comment`/`both`, token bez zápisu | jako dnes: zápis vrátí 403, akce vypíše hint (#257) a warning, thresholdy a outputy fungují. V `both` je summary zapsané. |
| E2 | `summary` (jakékoli `update-comment`) | žádné volání comment API, funguje i bez práva zápisu, bez 403 a bez warningu. |

### Co a kde se dokumentuje

Rámec: `report-target` je nová možnost, kam dát výstup. `summary` je zajímavé tím, že workflow nepotřebuje právo
zápisu. **PR z forku ani Dependabota nezmiňovat** v README, `docs/inputs/`, hintech v logu ani v textu issue.
Stávající zmínky se v rámci #285 odstraní (body 4–6).

1. **`docs/inputs/report-target.md` → sekce „Permissions":**
   - `comment` a `both` potřebují `issues: write`;
   - `summary` vystačí s `contents: read` + `pull-requests: read`;
   - příklad YAML s minimálními právy.
2. **`README.md` → Requirements, odrážka „GitHub Token" (ř. 22):**
   - právo zápisu (`issues: write`) je potřeba jen pro komentář;
   - bez něj komentář selže, ale kontrola thresholdů běží dál (tahle informace se přesouvá z ř. 25);
   - s `report-target: summary` stačí čtení.
3. **`README.md` → Key features:** nová odrážka o job summary (výstup do job summary místo komentáře nebo vedle něj,
   bez práva zápisu).
4. **Čistka `README.md` ř. 25 („Supported event"):**
   - odstranit větu o forku a Dependabotu i větu „If you need fork or Dependabot PRs…";
   - nový text: ``**Supported event**: `pull_request` only. If you need another event, please [open an issue](https://github.com/MoranaApps/jacoco-report/issues) describing your setup.``
5. **Čistka `README.md` → Troubleshooting „403" (ř. 234–235):** větu
   `Fork PRs and Dependabot PRs get a read-only token, so the comment can't be posted.` nahradit
   ``To get the report without write permission, use `report-target: summary`.``
6. **Čistka hintu `HINT_FORBIDDEN` (`utils/github.py:36-37`):** větu
   `On fork PRs and Dependabot PRs the token is read-only, so the comment can't be posted.` nahradit
   `` `report-target: summary` shows the report without write permission. ``
   - Testy kontrolují jen podřetězec `token lacks a permission` (`tests/unit/utils/test_github.py:721`).
   - Id parametru `403-post-fork-pr` je interní a zůstává.
7. **Nemění se** `DEVELOPER.md` ř. 251 a 267 a komentáře ve workflow. Popisují CI tohoto repa (fork PR přispěvatelů),
   ne použití akce. Do `DEVELOPER.md` u ř. 267 se jen doplní nový běh self-testu se `summary`.

## F. Mimo rozsah

- `name` a `description` v `action.yml` se nemění („JaCoCo Report to PR Comment", identita na Marketplace).
- Nepřibydou žádné nové outputy.
- Provozní chyby (D3) se do summary nepíšou.
- Starý komentář se při přechodu na `summary` automaticky neuklízí (A7).
- Bezpečnost: obsah summary je stejný jako obsah komentáře (názvy jsou už `_single_line`). Runner summary
  soubor neparsuje na workflow příkazy, takže nevzniká nové riziko injection.

## G. Testy

- **Unit, `ActionInputs`:**
  - výchozí hodnota, každá platná hodnota, velikost písmen a mezery, prázdná hodnota;
  - neplatná hodnota → chyba validace a `exit 1`;
  - pořadí chyby ve validaci.
- **Unit, `action.yml`:** `INPUT_REPORT_TARGET` je v `env` Run kroku (`test_run_step_env_maps_every_input_with_the_real_reader`).
- **Unit, generátor:** řádky A1–A7 a B1–B6 s mockem `GitHub`.
  - A7 pro obě hodnoty `update-comment`: nevolá se žádná comment metoda (`get_comments`, `add_comment`, `update_comment`, `delete_comment`) a INFO se zaloguje.
- **Unit, oříznutí:**
  - summary dostane celé tělo, i když je komentář oříznutý (`MAX_COMMENT_LENGTH` snížený);
  - B4 se sníženým limitem summary: poznámka, odkaz, celé tělo v logu, měření v bajtech (vícebajtové znaky, např. ✅);
  - C1–C3 (text poznámky a odkaz).
- **Unit, zápis do summary:** append, UTF-8, chybějící proměnná, `OSError`.
- **Unit, `utils/github.py`:** hint pro 403 obsahuje `report-target: summary`.
- **Unit, `JaCoCoReport`, D1:**
  - `summary`: žádné mazání ani při `update-comment: true` a summary obsahuje zprávu;
  - `both`: mazání jako dnes a zpráva v summary;
  - `comment-level: none`: summary prázdné.
- **Offline integrace (`tests/integration/`):** celý průchod s `GITHUB_STEP_SUMMARY` v `tmp_path`. Summary obsahuje title. U `summary` neproběhne žádné volání comment API.
- **Self-test** (`.github/workflows/static_analysis_and_tests.yml`, job `self-test`, read-only token):
  - Nový krok `uses: ./` s `report-target: summary`, `comment-level: full`, výchozím `update-comment` a vlastním
    title (např. `Self-test job summary`). Neproběhne žádné volání comment API.
  - Ověří `outcome == success` a stejné outputy jako první běh.
  - Obsah summary se kontroluje jen ručně v UI běhu, kvůli izolaci kroků (viz Pojmy).
- **`make check`** musí projít s coverage aspoň 80 %.

## H. Poznámky k implementaci

- `action.yml`: input `report-target` (default `'comment'`, popis) a `INPUT_REPORT_TARGET: ${{ inputs.report-target }}` v `env` Run kroku.
- `utils/constants.py`: `REPORT_TARGET`. `utils/enums.py`: `ReportTargetEnum` (`comment`, `summary`, `both`), vedle `CommentLevelEnum`.
- `action_inputs.py`:
  - `get_report_target()` (prázdná hodnota → `comment`);
  - `_validate_report_target()` hned za `_validate_comment_level()`;
  - přidat řádek v `_log_configuration`.
- `utils/gh_action.py`: funkce pro zápis summary, která vrací `bool`.
  - Nic netiskne; warning vypíše volající přes `print_action_warning`.
  - Soubor je vyjmutý z AST guardu `test_no_direct_output.py`.
- `pr_comment_generator.py`:
  - `_fit_to_comment_limit` a `_render_body` parametrizovat limitem, měřením (`len` / bajty UTF-8), textem poznámky
    a tím, co se loguje (vynechané řádky u komentáře, celé tělo u summary).
  - `_get_comment_content` ať vrátí části (head, sections, footer), aby šlo složit tělo komentáře i tělo summary.
  - `generate()`:
    - řídí pořadí summary → komentář;
    - u `summary` končí před jakýmkoli čtením komentářů a zaloguje INFO z A7;
    - footer pro zprávu D1 vytáhnout na úroveň modulu.
- `jacoco_report.py`:
  - `run()` je na limitu `too-many-locals`, takže novou logiku dát do helperu.
  - `_handle_all_reports_filtered`: u `summary` přeskočit `_delete_stale_comment_if_update_enabled` a zalogovat INFO z A7.
    U `summary`/`both` (a `comment-level` ≠ `none`) zapsat zprávu D1.
  - Warningy B5 a B6 vypisuje volající generátoru.
- `utils/github.py`: `HINT_FORBIDDEN` podle E → „Co a kde se dokumentuje", bod 6.
- Dokumentace (rámec a zákaz zmínek podle E):
  - nový `docs/inputs/report-target.md`:
    - tabulka A/B/C/D1 v lidské podobě;
    - tabulka `comment-level` × kanál a věta, že výchozí hodnota je `full`;
    - tabulka „Výsledek jobu", limit 1 MiB a důsledek A7;
    - sekce „Permissions" (E);
  - tabulka inputů v `README.md`;
  - `README.md`: body 2–5 v E → „Co a kde se dokumentuje";
  - `DEVELOPER.md` u ř. 267: nový běh self-testu se `summary`;
  - `docs/inputs/comment-level.md`: „Theory" a `none` — `comment-level` platí pro komentář i summary, u `none` se nezapíše ani summary.
- `CONTEXT.md` — opravit / doplnit:
  - Purpose: přidat summary;
  - bullet o limitu komentáře: limit summary, varianty poznámky a celé tělo v logu u B4;
  - bullet o self-testu: dnes tvrdí, že `comment-level: none` + `update-comment: false` je jediný režim bez volání comment API, nově je druhý `report-target: summary`;
  - nový krok self-testu;
  - sémantika `generate()`;
  - D1 u `summary`;
  - bullet o hintech (#257): pro 403 dnes uvádí „the read-only fork/Dependabot token", přepsat podle nového textu `HINT_FORBIDDEN`.
- Poslední krok: `bash .claude/skills/context-md/check.sh --base origin/master --strict`.

## I. Text issue #285 (EN, vloženo do issue 2026-11-16)

```markdown
Part of #284.

## Problem

The report only goes to a PR comment, and posting a comment needs a token with write permission (`issues: write`).
A long report no longer fails since #266, but rows are cut from the comment, so the full report is only in the
job log. Users of other coverage actions ask for the job summary as a second channel (`Madrapps/jacoco-report#88`,
`#123`; that action has `comment-type: pr_comment | summary | both`).

## Fix

- New input `report-target`: `comment` (default, today's behaviour), `summary`, `both`.
- `summary` appends the same markdown as the comment to `$GITHUB_STEP_SUMMARY`, cut only at the job summary limit
  (1 MiB per step), not at the 65,536-character comment limit. Over 1 MiB, rows are cut from the end as in the
  comment, the full body goes to the job log, and the note links to it.
- `comment-level` applies to both targets. `comment-level: none` writes nothing.
- With `summary`, the action makes no comment API call, so the workflow needs no write permission: no comment is
  created, updated or removed, `update-comment` is ignored and the log says so. A comment from earlier runs stays as
  it is.
- The job result doesn't depend on the target: threshold breaches and operational errors fail the job as today; a
  summary that can't be written is a warning, like a comment that can't be posted.
- With `both`, when the comment is cut, its note links to the job summary.
- `skip-unchanged` removes every report: the summary gets a short "all reports are unchanged" message.
- `$GITHUB_STEP_SUMMARY` unset or not writable: a warning, the job result is unchanged.
- An invalid `report-target` value fails input validation, like the other inputs.
- README (Requirements, key features, troubleshooting "403") and the 403 log hint describe write permission in
  general terms: the comment needs `issues: write`, `report-target: summary` needs no write permission. The notes
  that name specific kinds of PRs with a read-only token are removed.

## Acceptance criteria

- [ ] Unit tests: each target value; summary written with the full body when the comment is truncated; summary cut
      over 1 MiB with the full body in the log; no comment API call with `summary` (either `update-comment`);
      all-reports-unchanged message; unset `$GITHUB_STEP_SUMMARY`; an invalid value fails validation.
- [ ] Offline integration test: full run with `$GITHUB_STEP_SUMMARY` pointing to a temp file; it contains the
      report title.
- [ ] Self-test: run with `report-target: summary` and a read-only token; the run succeeds with the expected
      outputs. (A later step can't read `$GITHUB_STEP_SUMMARY`: each step gets its own file.)
- [ ] `docs/inputs/report-target.md`, README input table, README and the 403 log hint updated as above.
- [ ] Tests pass with no coverage regression.

Breaking: no (default unchanged).
```

## Otevřené body

Žádné. Issue #285 je přepsané textem ze sekce I a další krok je implementace na větvi `feat/285-report-target`.
