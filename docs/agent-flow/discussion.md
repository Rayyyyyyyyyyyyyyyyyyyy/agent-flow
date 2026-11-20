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

Reviewed by the agency-agents Developer Advocate role (2026-11-19); its rewrites are folded in. Each line names the evidence that proves it from outside the agent.

- C1 installable: on macOS and Ubuntu CI runners with a fresh `HOME`, `claude plugin validate .`, `claude plugin marketplace add`, `claude plugin install agent-flow@agent-flow` exit 0 and `claude plugin list` shows the plugin enabled
- C2 entry works: `scripts/check_discussion.py` validates the required sections of a `discussion.md` (verbatim words, finish line, authorizations, decisions, open questions/frontier); its unit test passes on this repo's `docs/agent-flow/discussion.md` and fails on a copy missing a section
- C3 first-party only, licenses clear: `scripts/check_package.py` finds no third-party skill inside the plugin; LICENSE (MIT) and NOTICE exist; files derived from agency-agents carry its MIT notice
- C4 works without companions: evidence: user judges (the user runs the installed plugin with no companion skills on a project of their choice)
- C5 no personal data: `scripts/check_package.py` finds 0 hits for `/Users/`, email addresses, `rtk`, `ponytail`, `Asia/Taipei`; the GitHub handle appears only in `README.md` and `.claude-plugin/marketplace.json`
- C6 outer boundaries and autonomy: `SKILL.md` has a Boundaries section that project rules may tighten but never loosen; a unit test greps each line:
  (a) do without asking: branch, commit, push, PR, CI, merge, including the CI-setup PR;
  (b) ask first: deploy/publish to users; writes to repos or services the user does not own; anything that notifies other people; using secrets, spending money, deleting or overwriting the user's own data; a verification method that spends usage, runs real model calls or creates external resources (asked upfront with a cost estimate); browser use;
  (c) never: claim done without evidence or report unverified as verified; fabricate projects, data or records as verification; delete or weaken tests, checks, CI, the boundaries or the kill switch to make a gate pass; commit or print secrets;
  (d) kill switch: with `.agent-flow/STOP` present or `merge: never` in `.agent-flow/config`, `merge_gate.py` refuses to merge (unit tests)
\1merge conditions on top of `merge_gate.py`'s fixed floor) into its `CLAUDE.md`/`AGENTS.md` or `docs/<topic>/`, inside the boundaries; a unit test greps the instruction; whether the result fits a project: evidence: user judges
- C7 cross-platform: script tests green on GitHub Actions macOS and Ubuntu; on Ubuntu with bwrap installed the sandbox path really executes (not skipped); a job without any sandbox asserts project-code evidence is `unverified` and that merge is blocked
- C8 English: CJK character count in the plugin directory (rules, roles, scripts, error messages) is 0; the skill tells the agent to answer in the user's language
- C9 releasable: tag `v0.1.0`, CHANGELOG, README; a marketplace entry pinned to `ref: v0.1.0` installs and `claude plugin list` shows 0.1.0; `.audit.md` records the same version
- C10 dogfooded: evidence: user judges (the user runs one ticket end to end on a project of their choice)
- C11 time to first success: evidence: user judges (the user follows README Quick Start in a fresh `HOME` and reaches a merged PR)
- C12 preflight: `agent-flow doctor` (script) reports each missing piece with its fix and a non-zero exit: git, gh, gh login, push access, Python 3.11+, claude CLI, sandbox availability, branch-protection availability (public or paid plan), HTTPS remote without `workflow` scope; one unit test per check
- C13 resumable: `references/tickets.md` requires the `<!-- agent-flow:<topic>#<NN> -->` marker and a search for it before creating an issue or PR (a unit test greps the rule)
- C14 cost shown: `review.py` prints tokens and $ (from `claude -p --output-format json`; unit test on a recorded JSON); the skill tells interactive users to check `/cost` (an interactive session cannot read its own usage)
- C15 no model calls on the user's machine for canaries: canaries run by the maintainer before tagging; the stamp ships with the version; a test asserts `audit.py` does not invoke `claude` on the deterministic path

Out of v0.1 (later): designer, writer, researcher, planner roles; srt; native Windows (WSL2 documented); retro and method log; agency-agents / grilling integration; upgrade migration (README: old `.audit.md` stay bound to their version); uninstall beyond a README section.

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

## Open questions

- Next PR (shipped rules): add the Boundaries section to `SKILL.md` (C6), move the warn tier to ask first in `SKILL.md` and `references/workflow.md`, add the project-rules instruction (C16), with rule-grep tests for C6, C13, C16. Restore `scripts/check_discussion.py` (+ test, lost with PR #27) for C2.
- `agent-flow-fixture` repo still exists: deleting needs `gh auth refresh -h github.com -s delete_repo` (user's action), then `gh repo delete Rayyyyyyyyyyyyyyyyyyyy/agent-flow-fixture --yes`.
- Canaries: they guard `audit.py` (a method tool) but run here and ship trap reports to every user; keep, move out of the plugin dir, or drop? Ask.
- Next after those: one opus review + audit over v0.1, then #13 release (README, CHANGELOG, 0.1.0, re-run canaries for the new version, tag, pinned install).
