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

> 對 我要弄這個agent-flow 就是因為她

(2026-11-24, on Lauren Tan's AI Engineer talk as summarised in a post the user pasted: repo as the AI's textbook, near-zero comments, lint over markdown, hide error-prone APIs, the agent runs the app itself, tokens go to verification, one agent first then many. Numbers in the post are second-hand and unverified.)

## Finish line

This phase is the Method; release waits for #13.

- C1 installable, evidence: on macOS and Ubuntu CI runners with a fresh `HOME`, `claude plugin validate .`, `claude plugin marketplace add`, `claude plugin install agent-flow@agent-flow` exit 0 and `claude plugin list` shows the plugin enabled
- C2 records checkable, evidence: `scripts/check_discussion.py` passes on this file and fails on a copy missing a section (unit test)
- C3 first-party only, licenses clear, evidence: `scripts/check_package.py` finds no third-party skill inside the plugin; LICENSE (MIT) and NOTICE exist
- C5 no personal data, evidence: `scripts/check_package.py` finds 0 hits for `/Users/`, email addresses, `rtk`, `ponytail`, `Asia/Taipei`; the GitHub handle appears only where allowed
- C6 outer boundaries and kill switch, evidence: unit test greps each Boundaries line in `SKILL.md` (do / ask first / never); `merge_gate.py` refuses with `.agent-flow/STOP` or `merge: never` (unit tests)
- C7 cross-platform scripts, evidence: unit tests green on GitHub Actions macOS and Ubuntu
- C8 English, evidence: CJK count in the plugin directory is 0; the skill tells the agent to answer in the user's language
- C10 dogfooded, evidence: user judges (the Owner runs a goal end to end in an experiment repo)
- C12 preflight, evidence: `doctor.py` reports each missing piece with its fix and a non-zero exit (one unit test per check)
- C13 resumable, evidence: a unit test greps the rule that a re-run reuses the existing OpenSpec change, branches and PRs instead of creating duplicates
- C14 cost shown, evidence: a unit test greps the rule that the final report lists the review's cumulative tokens; no budget until the experiment repo gives numbers
- C16 project rules, evidence: a unit test greps the instruction to write the Calling repo's own rules and verify inside the Boundaries; fit: user judges
- C17 Environment alignment, evidence: a unit test greps step 0 in `SKILL.md` (OpenSpec readable via `openspec list --json`, else the user is told to install or init; for the steps OpenSpec does not cover, list installed skills, one per step with a reason, required settings, `.agent-flow/skills.md`, read `SKILL.md` for non-invocable skills, own instruction only when none fits); fit: user judges
- C18 propose, confirm and Plan PR, evidence: unit tests grep the propose step (`/opsx:propose` into `openspec/changes/<topic>/`, opened as the Plan PR), the confirm step (the Owner reviews proposal, specs and tasks before apply) and the Plan PR contents; `merge_gate.py` refuses to merge a Plan PR unless `plan: agent` is set in `.agent-flow/config` (unit tests)
- C19 locks, evidence: `merge_gate.py` refuses a non-Plan PR that touches `.agent-flow/**`, CI workflow files, `openspec/config.yaml` or `openspec/changes/<topic>/specs/` (unit tests); `tasks.md` is not locked
- C20 Evidence check, evidence: `merge_gate.py` refuses when any Scenario in `openspec/changes/<topic>/specs/` lacks a Verify command or `Owner judges:`, when a Verify command uses a pipe, `;` or `$?`, or when the Evidence check CI job is not green (unit tests); the skill tells the agent to add that CI job (rule grep)
- C21 no reinvented steps, evidence: user judges (each step's text in the plugin points at its `/opsx:*` command, the skill chosen in step 0, or the minimal fallback)
- C22 owner-judged items, evidence: `merge_gate.py` refuses a PR labelled `agent-flow:owner-judges` (unit test); Scenarios carry only Verify commands or `Owner judges:` (rule grep)
- C23 archive, evidence: a unit test greps step 9 (`/opsx:archive` after merge, on `agent-flow/<topic>-archive`); `merge_gate.py` refuses an archive PR whose diff leaves `openspec/specs/**` and `openspec/changes/**` (unit tests)

## Authorizations

> 直接做成公開版 — publishing agent-flow as a public plugin (tag, release, README) is the goal itself (2026-11-19).
> 名稱用 agent-flow，開新 repo，MIT — https://github.com/Rayyyyyyyyyyyyyyyyyyyy/agent-flow.git (2026-11-19).
> 我不要被問，要做就是做完 pr and verify and merge — applies to this project's own work (2026-11-19).
> 會影響到他人的才要做詢問 (2026-11-19).

## Decisions

- 2026-11-19 user: agent-flow is a **Claude Code plugin**; this repo is its marketplace. Name `agent-flow`, public repo, MIT.
- 2026-11-19 user: project records follow `references/records.md`: `docs/<topic>/discussion.md` (verbatim words, finish line, authorizations, decisions, open questions), `GLOSSARY.md`, `docs/adr/`; work log lives in PRs; repo know-how in the Calling repo's `CLAUDE.md`/`AGENTS.md`.
- 2026-11-19 user: skill-workflow PR #9 and msp-web-vue3 are parked.
- 2026-11-19 user (「1 照你推薦，繼續做完」): v0.1 stays a Claude Code plugin; an MCP server exposing the scripts is a v0.2 candidate.
- 2026-11-19 user (「c6 不要被問，要做就是做完 pr and verify and merge」): invoking the plugin in a repo is the consent to the Do without asking tier.
- 2026-11-20 user (「9 對」「2 警告改成用問」): the Boundaries in C6 stand; secrets, money and deleting or overwriting the user's own data are Ask first.
- 2026-11-20 user (「e2e是要by project 去跑的」「而且不是每個project都需要e2e」): E2E is a per-project choice, not a default; agent-flow itself does not run one.
- 2026-11-20 user (「執行的是呼叫plugin的repo 不是這裡啊」「是要告訴呼叫plugin的repo裡的agent 去寫適用他自己的rule and verify」「要寫出界線底線不能跨越的最外層界線」): the plugin ships the outer boundaries plus the Method; the agent in the Calling repo writes that repo's own rules and verify inside them (C16). Nothing of the flow is executed here.
- 2026-11-20 user (「現在是一個抽象的plugin 很多情境都是要依照呼叫端的repo 內容去制定」): the plugin is abstract; situations are decided from the Calling repo's content, not fixed in the plugin.
- 2026-11-20 user (「以後不跑 review/audit，記下來」): this repo's own PRs merge on green CI (tests, `no_cjk.py`, `check_package.py`, plugin validate) with `gh pr merge --merge`; whether the rule text is right is the user's judgment.
- 2026-11-23 user (「我當初創agent-flow 這個repo 不是叫你重弄欸，是要站在skill-flow這個基礎上做出一個抽象的工具方法包」「不需要再改skill-workflow 啊」): skill-workflow `31114d7` is the frozen Base; abstract only what is tied to its own repo; where the Owner changed the Method, the Owner's decision wins.
- 2026-11-23 user (「我覺得repo 方向偏了」「目標很明確，所以先把方法做好，才能包裝給其他project用啊」「先自己，其他人只是附帶」「就算用戶是我自己也是透過 / 來呼叫」): the Owner is the first user and the Plugin is the product even for the Owner. Release (#13) waits until the Method is done. Vocabulary: `GLOSSARY.md`.
- 2026-11-23 user, requested improvements: 「review太花token，稽核也沒有根據證據」「切票切完可以並行」「我的理想是你可以自己運行：接收需求、收集與彙整資料當作實作地基、切票、實作、驗證、merge，同時資料要有事實根據，驗證要有證據查核不能為了綠燈自己改規則」「應該每個動作都有可以套用的skill，不要重複造輪子」.
- 2026-11-23 user (「先做抽象的方法論，我會套到實驗repo去做呼叫」): proof of the Method is the Owner's own run in an experiment repo; the agent runs no E2E.
- 2026-11-23 user (Q11, Q13-Q15, Q19, Q26, Q27): Verify commands are fixed in the Plan PR and locked; the Evidence check is a CI job; `merge_gate.py` enforces the locks, coverage, no pipes, and the `agent-flow:owner-judges` label; Review only judges quality and whether each Verify command tests its Scenario (ADR 0001). One integration branch and one integration PR per goal; the Owner merges the Plan PR unless `.agent-flow/config` has `plan: agent`; one review per goal with cumulative tokens reported.
- 2026-11-23 user (「ponytail 可以做到 audit吧，你被自己侷限住了，本機電腦不是只有裝matt的skill」「使用plugin之前的動作是對齊環境」「不是只有matt的要用」): steps OpenSpec does not cover use skills from whatever the session has, chosen in step 0; no bundled copies and no plugin dependency (ADR 0002).
- 2026-11-24 user (「我想把 openspec流程放進來」「我要把grill 換成 openspec explore」「matt spec + tickets + plan PR 換成 opsx-propose → proposal / design / specs/ / tasks.md」「Implement 換成 opsx-apply (逐項勾 tasks.md)」「(之後) 加入opsx-archive + sync → openspec/specs/ 累積「現行規格」」): OpenSpec is fixed in every Calling repo for explore (`/opsx:explore`), propose (`/opsx:propose` into `openspec/changes/<topic>/`), apply (`/opsx:apply`) and archive (`/opsx:archive`, folding the change into `openspec/specs/`). `docs/<topic>/discussion.md` and `foundation.md` stay (ADR 0003).
- 2026-11-24 user (「我覺得你歪了 你是一個抽象方法」「就算呼叫端跑了 openspec init也是在呼叫端的repo裡面」「跟正常手動輸入指令是一樣的 你只要讀得到就好了」「如果找不到openspec cli 就用戶建議安裝」): agent-flow runs the `opsx-*` commands as a user would and only reads what they leave in the Calling repo. `doctor.py` fails when `openspec` is missing (fix: `npm install -g @fission-ai/openspec@latest`) or `openspec list --json` fails (fix: the user runs `openspec init`); the agent does neither.
- 2026-11-24 user (「explore 是進入討論環節 使用者會自己決定是否進入下一階段開propose」「確認沒問題之後再進入apply」「4 跳過」): the Method is 0 Align, 1 Receive (a goal skips explore; a direction or seed is explored until the user moves on), 2 Gather, 3 Propose and open the Plan PR, 4 Confirm (merging the Plan PR is the go-ahead), 5 Apply, 6 Review, 7 Evidence check, 8 Merge, 9 Archive.
- 2026-11-24 user (「1 可以」): Verify commands sit under each `#### Scenario:` in `openspec/changes/<topic>/specs/**/spec.md`. Locked after the Plan PR: `.agent-flow/**`, `.github/workflows/**`, `openspec/config.yaml`, `openspec/changes/<topic>/specs/**`; `tasks.md` is not locked so apply can tick it.
- 2026-11-24 user (「2 選 a」「ok」): the archive PR is its own kind, head `agent-flow/<topic>-archive`; `merge_gate.py` allows its diff only under `openspec/specs/`, `openspec/changes/<topic>/` and `openspec/changes/archive/<date>-<topic>/`. The `evidence-check` job is skipped on it.
- 2026-11-24 user (「第一層的gate 就是限制大方向與絕對不能做的事情」「第二層就是要讀過project之後才能寫的東西」): layer 1 is fixed by agent-flow in its skill and identical in every Calling repo (direction, absolute limits, the Scenario and Verify format); a repo may tighten it, never loosen it. Layer 2 is written by the agent only after reading the Calling repo in step 2.
- 2026-11-24 user (「然後你比對一下 matt系列的skill保留必要」「ok」): matt skills in the Method: `research` (2), `tdd` (inside apply), `code-review` (6, Spec axis on `openspec/changes/<topic>/`), `pr`, `domain-modeling`; situational `codebase-design`, `diagnosing-bugs`, `prototype`, `retro`. Not used: `grilling`, `grill-me`, `grill-with-docs`, `to-spec`, `to-tickets`, `implement`, `implement-spec`, `setup-matt-pocock-skills`. Installed skills are not removed.
- 2026-11-24 agent, settled from the requested improvement 「切票切完可以並行」: apply stays parallel. Each `## N.` group of `tasks.md` starts with `Blocked by:`; ready groups run as one subagent and one worktree each, running `/opsx:apply` for that group only.
- 2026-11-24 agent, settled from the existing step 2 rule: layer 2 rules stay in the Calling repo's `CLAUDE.md`/`AGENTS.md` (or `docs/<topic>/` for one goal); agent-flow does not write `openspec/config.yaml`.
- 2026-11-24 user (「恩 照你的建議」): subagent models by alias, from the Base's split (implement sonnet, review opus): apply implementers and the guess check `sonnet`, every review subagent `opus`, passed explicitly on each call; recorded in the Model column of `.agent-flow/skills.md`, where a Calling repo may change them. The main session's model is the user's.
- 2026-11-24 user (「不要留歷史混淆你自己」「都刪,tickets.md 也刪」): records hold the current state only. Deleted: `parity.md`, `docs/research/sandbox-for-audit-reruns.md`, `docs/agent-flow/reviews/`, `references/tickets.md`, and superseded Decisions.

## Open questions

- Ask the user, one by one (proposed 2026-11-24 from the talk above and from reading obra/superpowers, garrytan/gstack and affaan-m/ECC; nothing is changed yet):
  - P1 one agent first: the first experiment run executes task groups one at a time; parallel apply is switched on only after one agent delivers a PR that merges as is.
  - P2 second time becomes a check: a mistake seen twice in a Calling repo becomes a lint or Verify check whose message says how to fix it, not another line in `CLAUDE.md`/`AGENTS.md` (feeds A9).
  - P3 models by task size: each `## N.` group in `tasks.md` carries a size; a complete spec touching 1-2 files runs on `haiku`, integration on `sonnet`, design on `opus`; review model scales with diff size and risk, `sonnet` as the floor (superpowers `subagent-driven-development`, "turn count beats token price"). Changes the 2026-11-24 model decision.
  - P4 subagent brief and report files: the task text goes to a brief file, the full report to a report file; the subagent returns only status, commits, one test line and concerns; no pasted history; implementers start no reviewers (feeds B8, E2).
  - P5 review by file: the diff is written to one file for the reviewer; the reviewer does not re-run tests the implementer already ran; re-review covers only the fix diff.
  - P6 fix loop: rounds 1-3 resume the same implementer, rounds 4-5 a fresh one a model tier up, then the agent rules and records; only after that does the existing "stuck after three approaches" rule ask the user.
  - P7 ruling format: decisions the agent makes alone are recorded as `Ruling: what - why - cost if wrong` (feeds A6, A7).
  - P8 hooks as fences: a PreToolUse hook blocks edits to locked paths, lint/test config and destructive commands at the moment they happen, fail-closed (gstack `careful`/`freeze`, ECC `config-protection`), instead of only at `merge_gate.py` (feeds A5, A12). The plugin would ship a hook: needs an ADR.
  - P9 review findings: a workaround added by this diff, or a comment that excuses one, is a finding; workarounds already in the repo are recorded, not fixed (keeps A7).
  - Not taken: superpowers' "no parallel implementers" (worktrees already isolate), gstack "Boil the Ocean" (against A7), ECC `verification-loop` (pipes in checks), per-tool telemetry hooks; deleting most comments; screenshots or E2E by default (E2E stays per project).

- Next: the Owner runs a goal in an experiment repo (C10) and reports where it gets stuck. That run also settles whether the agent can invoke the `/opsx:*` commands itself, whether another plugin's skill can be invoked through the Skill tool, and whether reading `SKILL.md` from the plugin cache works for `disable-model-invocation` skills.
- Owner-judged Scenarios rely on the agent adding the `agent-flow:owner-judges` label; `verify.py` lists them (`OWNER`) but `merge_gate.py` does not read them. Make it deterministic if the experiment shows the label being missed.
- Base rules still weaker or missing in the Method (from the deleted port checklist), to port next, Boundaries first: Ask first for other irreversible actions (A5), for choices that are pure preference and change direction (A6), for widening scope beyond the finish line (A7); when and how a repo's rules may change, with the trigger in the commit (A9); what does not count as browser permission and the three things to state first (A10); trust-boundary validation and saying whether a mistake can be undone for secrets, permissions and persistent data (A11); keep the user's uncommitted changes in the main worktree (A12); what every subagent brief contains (B8); cross-domain borrowing when a second approach fails (B10); recording what Verify commands do not cover (B11); recording tried approaches and results on failure (B19); compact hand-offs between agents with refs and reason codes (E2); minimum checks per kind of work (E4); read GLOSSARY and ADRs before exploring and call out ADR conflicts (F4).
- `agent-flow-fixture` repo still exists: deleting needs `gh auth refresh -h github.com -s delete_repo` (user's action), then `gh repo delete Rayyyyyyyyyyyyyyyyyyyy/agent-flow-fixture --yes`.
