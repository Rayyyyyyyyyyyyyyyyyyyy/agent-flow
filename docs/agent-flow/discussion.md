# agent-flow — discussion

> Working language of this record follows the user (zh-TW). The shipped plugin itself is English (C8).

## Original words

> 我有個想法，我要改變主詞
> 意思是說 我要打包main workflow這套方法弄成skill
> 安裝在全域，在正確的repo底下開啟claude 呼叫這個skill來做整套flow
> 朝這方向再來重新對過flow

> 1. 照你推薦 2. 專案紀錄走 grill-with-docs 的做法吧？ 3. 照你推薦 4. 你覺得如果要開放給其他人用（完全不相干的人），適合怎麼樣的做法？ 5. 就先不管他了

> 直接做成公開版

> 名稱用 agent-flow，開新 repo，MIT
> https://github.com/Rayyyyyyyyyyyyyyyyyyyy/agent-flow.git
> sandbox的部分不必要的話就去research 大眾認為的好解決方法

(2026-11-19, session started in skill-workflow main)

## Finish line

Rewritten 2026-11-23 (realignment, see Decisions). This phase is the Method; release (old C9, C11) waits for #13. Removed: C4 (companions are gone, ADR 0002), C7's sandbox part and C15 (no sandbox audit, ADR 0001), C9 and C11 (moved to #13).

- C1 installable, evidence: on macOS and Ubuntu CI runners with a fresh `HOME`, `claude plugin validate .`, `claude plugin marketplace add`, `claude plugin install agent-flow@agent-flow` exit 0 and `claude plugin list` shows the plugin enabled
- C2 records checkable, evidence: `scripts/check_discussion.py` passes on this file and fails on a copy missing a section (unit test)
- C3 first-party only, licenses clear, evidence: `scripts/check_package.py` finds no third-party skill inside the plugin; LICENSE (MIT) and NOTICE exist
- C5 no personal data, evidence: `scripts/check_package.py` finds 0 hits for `/Users/`, email addresses, `rtk`, `ponytail`, `Asia/Taipei`; the GitHub handle appears only where allowed
- C6 outer boundaries and kill switch, evidence: unit test greps each Boundaries line in `SKILL.md` (do / ask first / never); `merge_gate.py` refuses with `.agent-flow/STOP` or `merge: never` (unit tests)
- C7 cross-platform scripts, evidence: unit tests green on GitHub Actions macOS and Ubuntu
- C8 English, evidence: CJK count in the plugin directory is 0; the skill tells the agent to answer in the user's language
- C10 dogfooded, evidence: user judges (the Owner runs a goal end to end in an experiment repo)
- C12 preflight, evidence: `doctor.py` reports each missing piece with its fix and a non-zero exit (one unit test per check)
- C13 resumable, evidence: a unit test greps the rule that a re-run reuses existing ticket files, branch and PR instead of creating duplicates
- C14 cost shown, evidence: a unit test greps the rule that the final report lists the review's cumulative tokens; no budget until the experiment repo gives numbers
- C16 project rules, evidence: a unit test greps the instruction to write the Calling repo's own rules and verify inside the Boundaries; fit: user judges
- C17 Environment alignment, evidence: a unit test greps step 0 in `SKILL.md` (list installed skills, one per step with a reason, required settings, `.agent-flow/skills.md`, read `SKILL.md` for non-invocable skills, own instruction only when none fits); fit: user judges
- C18 confirm and Plan PR, evidence: unit tests grep the confirm step (task list and goal re-confirmed with the Owner before cutting tickets) and the Plan PR contents; `merge_gate.py` refuses to merge a Plan PR unless `plan: agent` is set in `.agent-flow/config` (unit tests)
- C19 locks, evidence: `merge_gate.py` refuses a non-Plan PR that touches `.agent-flow/**`, CI workflow files or `docs/<topic>/tickets/` (unit tests)
- C20 Evidence check, evidence: `merge_gate.py` refuses when any ticket criterion lacks a Verify command, when a Verify command uses a pipe, `;` or `$?`, or when the Evidence check CI job is not green (unit tests); the skill tells the agent to add that CI job (rule grep)
- C21 no reinvented steps, evidence: user judges (each step's text in the plugin either points at the skill chosen in step 0 or is the minimal fallback)
- C22 owner-judged items, evidence: `merge_gate.py` refuses a PR labelled `agent-flow:owner-judges` (unit test); tickets carry only Verify commands (rule grep)

## Authorizations

> 直接做成公開版 — publishing agent-flow as a public plugin (tag, release, README) is the goal itself (2026-11-19).
> 名稱用 agent-flow，開新 repo，MIT — https://github.com/Rayyyyyyyyyyyyyyyyyyyy/agent-flow.git (2026-11-19).
> 我不要被問，要做就是做完 pr and verify and merge — applies to this project's own work (2026-11-19).
> 會影響到他人的才要做詢問 / 金鑰、付費、使用者自己的資料 要警告 (2026-11-19).

## Decisions

- 2026-11-19 user: package as a **Claude Code plugin** (skill + 6 roles + scripts), marketplace = this repo.
- 2026-11-19 user: project records follow grill-with-docs: `docs/<topic>/discussion.md` (verbatim words, finish line, authorizations, decision tree, open questions / frontier), `GLOSSARY.md`, `docs/adr/`; work log lives in issues and PRs; repo know-how in the target repo's CLAUDE.md/AGENTS.md. The plugin ships its own description of this format (grill-with-docs has no license file, so it is not bundled).
- 2026-11-19 user: audit trust anchor = installed plugin version (tag); `.audit.md` records it.
- 2026-11-19 user: public from day one. Core plugin carries only first-party content; third-party skills are recommended companions with upstream install commands, and the flow degrades gracefully without them. Personal settings move out to the user's global CLAUDE.md. English shipped text.
- 2026-11-19 user: name `agent-flow`, new public repo, MIT.
- 2026-11-19 user: skill-workflow PR #9 and msp-web-vue3 are parked.
- 2026-11-19 user (「c6 不要被問，要做就是做完 pr and verify and merge」): replaces the conservative-permissions default; invoking the plugin in a repo is the consent.
- 2026-11-19 user (「會影響到他人的才要做詢問」): the only stop condition is impact on other people.
- 2026-11-19 user (「金鑰、付費、使用者自己的資料 要警告」): those three get a visible warning and the run continues.
- 2026-11-19 agent: C14 narrowed to what a script can observe (review.py, harness JSON); interactive cost goes to `/cost`.
- 2026-11-19 agent: Developer Advocate review adopted (C2, C4, C5, C7, C9, C10 rewritten; C11-C15 added; v0.1 ships implementer + reviewer roles only). Branch protection is used when the plan allows it; otherwise the agent itself checks CI green via `gh` before merging and doctor says so. Verified: GitHub Free private repos have no branch protection (docs.github.com about-protected-branches); plugin sources can pin `ref`/`sha` (code.claude.com plugin-marketplaces); the maintainer's gh token lacks `workflow` scope, ssh push is unaffected.
- 2026-11-19 user (「照你建議的沙盒做法」): audit reruns use (1) file-read evidence + read-only argv allowlist with `shell=False` on all platforms; (2) project-code commands only under a detected sandbox (macOS Seatbelt, Linux bwrap), isolated in one module; (3) otherwise three states passed / failed / partly unverified, unverified commands printed for the user or run with an explicit per-run opt-in, partly unverified blocks agent merge; (4) srt optional, never required; native Windows → WSL2. Source: `docs/research/sandbox-for-audit-reruns.md`.
- 2026-11-19 user (「1 照你推薦，繼續做完」): v0.1 stays a Claude Code plugin; an MCP server exposing audit/merge_gate/doctor/check_discussion is a v0.2 candidate.
- 2026-11-20 user (「阿你沒問我就開了個假專案做事」「有病嗎？我有說是這樣的驗證方式嗎」「虛構的都刪掉」): the fixture-repo E2E was never agreed. PR #27 closed, fixture repo to be deleted. Verification methods that create external resources or spend usage need the user's explicit yes (rule in references/workflow.md step 2).
- 2026-11-20 user (「檢討 token都花在哪裡」「明文訂好」): session phases, docs via subagent, land.py, verification agreed upfront (PR #28, review round 2 + audit passed; land.py fix PR #29).

- 2026-11-20 user (「e2e是要by project 去跑的」「而且不是每個project都需要e2e」「C4 C10 C11 改成 user judges」): E2E is a per-project choice, not a default; agent-flow itself does not run one. C2, C6, C13, C14 are proven by unit tests and rule greps; C4, C10, C11 by user judgment. Issue #12 closed.

- 2026-11-20 user (「執行的是呼叫plugin的repo 不是這裡啊」「是要告訴呼叫plugin的repo裡的agent 去寫適用他自己的rule and verify」「要寫出界線底線不能跨越的最外層界線」): the plugin ships the outer boundaries plus the method; the agent in the calling repo writes that repo's own rules and verify inside them (C16). Nothing of the flow is executed here.
- 2026-11-20 user (「9 對」「2 警告改成用問」): the 9 boundaries in C6 stand; secrets, money and deleting or overwriting the user's own data move from warn-and-continue to ask first. Replaces the 2026-11-19 「要警告」 decision.
- 2026-11-20 user (「py 工具是這套方法的執行方式 也就是原本skill-workflow做的事情」): the scripts (review, audit, merge_gate, land, doctor, sandbox) stay; they are how the method runs in the calling repo.

- 2026-11-20 user (「對，merge 條件照你建議」): flow order confirmed: 0 doctor + kill switch + print the boundaries, 1 intake, 2 finish line, 3 (new) write the project's rules and verify, 4 spec and tickets, 5 clarity gate, 6 dispatch, 7 check (CI, review.py, audit.py), 8 land.py, 9 report. `merge_gate.py`'s conditions (CI green, audit passed, no kill switch) are a boundary; project rules may add merge conditions, never remove one.
- 2026-11-20 user (「為什麼要跑 review.py 加 audit.py」「以後不跑 review/audit，記下來」): this repo's own PRs no longer run `review.py`/`audit.py` or merge through `land.py`; those tools run in the calling repo. A PR here merges on green CI (tests, `no_cjk.py`, `check_package.py`, plugin validate) with `gh pr merge --merge`; whether the rule text is right is the user's judgment.
- 2026-11-20 user (「回到flow本身很單純 接收需求 確認需求 搜集資訊 切票 實作 review audit」「步驟改成我的 7 步」): the flow in `SKILL.md` and `references/workflow.md` is exactly 7 steps: 1 receive the request, 2 confirm the request (finish line), 3 gather information (incl. the repo's own rules and verify), 4 cut tickets (incl. the guess check), 5 implement, 6 review, 7 audit (ends with `land.py`). Doctor stays a start check; the report stays a closing section. Replaces the 9-step order above.
- 2026-11-20 user (「現在是一個抽象的plugin 很多情境都是要依照呼叫端的repo 內容去制定」): the plugin is abstract; situations are decided from the calling repo's content, not fixed in the plugin.

- 2026-11-23 user (「陷阱也是要跟著呼叫端project 內容去客製的啊， canaries 不是沒用嗎？」): the plugin ships no canaries, no stamp and no `run_canaries.py`; trap reports are written per project from its own code, as skill-workflow's project-rules layer did (parity C8, C15).
- 2026-11-23 user (「我當初創agent-flow 這個repo 不是叫你重弄欸，是要站在skill-flow這個基礎上做出一個抽象的工具方法包」): skill-workflow is the base. Port it file by file; abstract only what is tied to the skill-workflow repo itself (orphan project branches, CATALOG, personal paths, language); keep every other rule. Rules the user changed since stay changed (7 steps, Boundaries, kill switch, merge_gate/land, bwrap, ticket marker). `parity.md` is the checklist; its "ask the user" rows are settled by this rule, not asked.

- 2026-11-23 user (「我覺得repo 方向偏了」「目標很明確，所以先把方法做好，才能包裝給其他project用啊」「先自己，其他人只是附帶」): the drift was packaging before the Method was good. The Owner is the first user; the Plugin is the product even for the Owner (「就算用戶是我自己也是透過 / 來呼叫」). Release (#13, old C9, C11) waits until the Method is done. Vocabulary: `GLOSSARY.md`.
- 2026-11-23 user (Q3 「對」, 「不需要再改skill-workflow 啊」): this phase is a faithful port plus Owner-requested improvements (Base A9's second trigger); skill-workflow stays frozen at `31114d7`.
- 2026-11-23 user, requested improvements: 「review太花token，稽核也沒有根據證據」「切票切完可以並行」「我的理想是你可以自己運行：接收需求、收集與彙整資料當作實作地基、切票、實作、驗證、merge，同時資料要有事實根據，驗證要有證據查核不能為了綠燈自己改規則」「應該每個動作都有可以套用的skill，不要重複造輪子」.
- 2026-11-23 user (Q7 「先做抽象的方法論，我會套到實驗repo去做呼叫」): proof of the Method is the Owner's own run in an experiment repo; the agent runs no E2E.
- 2026-11-23 user (Q9-Q30, all 「ok」/「對」): the Method is 0 Environment alignment, 1 receive, 2 gather into a cited `docs/<topic>/foundation.md`, 3 confirm the task list and re-confirm the goal with the Owner (「切票前與使用者確認task與重新確認目標」), 4 cut tickets into `docs/<topic>/tickets/<NN>-<slug>.md`, each criterion with a Verify command, then the Plan PR (finish line, Foundation, rules, tickets; merged by the Owner unless `.agent-flow/config` has `plan: agent`), 5 implement via the chosen implementation skill on one integration branch and one PR per goal, 6 Review by the chosen review skill, once, with cumulative tokens reported, 7 Evidence check in CI, 8 merge through `merge_gate.py`/`land.py`. Replaces the 7-step order of 2026-11-20, per-ticket PRs, GitHub issues as the ticket source, and the reviewer-supplied evidence.
- 2026-11-23 user (Q11, Q13-Q15, Q19, Q26, Q27): Verify commands are fixed in the Plan PR and locked; the Evidence check is a CI job; `merge_gate.py` enforces the locks, coverage, no pipes, and the `agent-flow:owner-judges` label. "Audit" splits into Evidence check and Review. `audit.py`, `sandbox.py`, `canaries.py`, `pending_audits.py`, `review.py`, `agents/reviewer.md`, `agents/implementer.md` are to be removed (ADR 0001). Replaces the 2026-11-19 sandbox audit decision and the 2026-11-23 audit-layer port.
- 2026-11-23 user (「ponytail 可以做到 audit吧，你被自己侷限住了，本機電腦不是只有裝matt的skill」「先讓我可以在本機run起來，也就是要可以呼叫使用者電腦裡的skill，使用plugin之前的動作是對齊環境」「不是只有matt的要用」): skills come from whatever the Owner's environment has, chosen in step 0; no bundled copies and no plugin dependency (ADR 0002). Replaces the 2026-11-19 companions-with-fallback decision; its premise that grill-with-docs had no licence is outdated (mattpocock/skills is MIT).
- 2026-11-23 user (Q18 「ok」): order of work: this realignment first, then the parity rows it does not cover (Boundaries A5-A7 first), then the Owner's experiment-repo run, then #13.

## Open questions

- Next: cut the realignment into tickets (this repo's PRs still merge on green CI, no review/audit): step 0 Environment alignment, confirm step, Plan PR and `plan:` setting, `docs/<topic>/tickets/` layout, `merge_gate.py` locks / coverage / no-pipe / owner-judges, the Evidence check CI job instruction, removal of the audit/review/sandbox scripts and their tests and CI jobs, `references/` trimmed to what no skill covers, C1-C22 tests.
- `parity.md` needs a pass marking rows superseded by the 2026-11-23 realignment (review, audit, canaries, tickets, records, companions).
- Unverified until the Owner's experiment run: whether a skill shipped by another plugin can be invoked through the Skill tool, and whether reading `SKILL.md` works for `disable-model-invocation` skills from the plugin cache.
- `agent-flow-fixture` repo still exists: deleting needs `gh auth refresh -h github.com -s delete_repo` (user's action), then `gh repo delete Rayyyyyyyyyyyyyyyyyyyy/agent-flow-fixture --yes`.
