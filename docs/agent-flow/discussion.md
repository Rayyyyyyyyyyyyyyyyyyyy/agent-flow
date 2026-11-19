# agent-flow — discussion

> Working language of this record follows the user (zh-TW). The shipped plugin itself is English (C8).

## Original words (verbatim)

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
- 2026-11-19 agent: Developer Advocate review adopted (C2, C4, C5, C7, C9, C10 rewritten; C11-C15 added; v0.1 ships implementer + reviewer roles only). Branch protection is used when the plan allows it; otherwise the agent itself checks CI green via `gh` before merging and doctor says so. Verified: GitHub Free private repos have no branch protection (docs.github.com about-protected-branches); plugin sources can pin `ref`/`sha` (code.claude.com plugin-marketplaces); the maintainer's gh token lacks `workflow` scope, ssh push is unaffected.
- 2026-11-19 user (「照你建議的沙盒做法」): audit reruns use (1) file-read evidence + read-only argv allowlist with `shell=False` on all platforms; (2) project-code commands only under a detected sandbox (macOS Seatbelt, Linux bwrap), isolated in one module; (3) otherwise three states passed / failed / partly unverified, unverified commands printed for the user or run with an explicit per-run opt-in, partly unverified blocks agent merge; (4) srt optional, never required; native Windows → WSL2. Source: `docs/research/sandbox-for-audit-reruns.md`.

## Finish line (v0.1)

Reviewed by the agency-agents Developer Advocate role (2026-11-19); its rewrites are folded in. Each line names the evidence that proves it from outside the agent.

- C1 installable: on macOS and Ubuntu CI runners with a fresh `HOME`, `claude plugin validate .`, `claude plugin marketplace add`, `claude plugin install agent-flow@agent-flow` exit 0 and `claude plugin list` shows the plugin enabled
- C2 entry works: fixed fixture repo + fixed prompt, `claude -p` run 3 times (locally, fresh `HOME`); all 3 produce `docs/<topic>/discussion.md` that passes `scripts/check_discussion.py` (required sections: verbatim words, finish line, authorizations, decisions, open questions/frontier)
- C3 first-party only, licenses clear: `scripts/check_package.py` finds no third-party skill inside the plugin; LICENSE (MIT) and NOTICE exist; files derived from agency-agents carry its MIT notice
- C4 works without companions: the C10 end-to-end run happens in a fresh `HOME` with only this plugin installed (no companion skills); the transcript lists the fallbacks taken
- C5 no personal data: `scripts/check_package.py` finds 0 hits for `/Users/`, email addresses, `rtk`, `ponytail`, `Asia/Taipei`; the GitHub handle appears only in `README.md` and `.claude-plugin/marketplace.json`
- C6 autonomy with three tiers, all in the shipped rules and tested on fixtures:
  (a) default: branch, commit, push, PR, CI, merge without asking; fixture run from invocation to a merged PR asks the user 0 times, including the CI-setup PR;
  (b) warn and continue: using secrets, spending money, deleting or overwriting the user's own data print a warning line (`WARNING:`) in the transcript and the run continues;
  (c) ask first: deploy/publish to users, writes to repos or services the user does not own, messages/issues/PRs that notify other people; one fixture per case stops with 0 external writes (checked with `gh api`);
  (d) kill switch: with `.agent-flow/STOP` present or `merge: never` in `.agent-flow/config`, the run opens PRs but merges 0
- C7 cross-platform: script tests green on GitHub Actions macOS and Ubuntu; on Ubuntu with bwrap installed the sandbox path really executes (not skipped); a job without any sandbox asserts project-code evidence is `unverified` and that merge is blocked
- C8 English: CJK character count in the plugin directory (rules, roles, scripts, error messages) is 0; the skill tells the agent to answer in the user's language
- C9 releasable: tag `v0.1.0`, CHANGELOG, README; a marketplace entry pinned to `ref: v0.1.0` installs and `claude plugin list` shows 0.1.0; `.audit.md` records the same version
- C10 dogfooded in public: in a public fixture repo, one ticket goes end to end: its acceptance test is red before implementation (CI log), then PR, review report and `.audit.md` are public; a CI job in the fixture repo re-runs `audit.py` from a clean clone of the tagged plugin and reaches the same verdict
- C11 time to first success: following README Quick Start verbatim in a fresh `HOME` and a fresh clone of the fixture repo reaches the first merged PR; the transcript and the measured minutes go in README (target <= 20 min excluding CI wait; the target is a guess)
- C12 preflight: `agent-flow doctor` (script) reports each missing piece with its fix and a non-zero exit: git, gh, gh login, push access, Python 3.11+, claude CLI, sandbox availability, branch-protection availability (public or paid plan), HTTPS remote without `workflow` scope; one unit test per check
- C13 resumable: killing a run after the PR is opened and invoking again leaves exactly one issue and one PR for that ticket (`gh issue list` / `gh pr list` counts)
- C14 cost shown: each run ends with tokens and $ per phase; README states the C10 measured numbers, which match the run output
- C15 no model calls on the user's machine for canaries: canaries run by the maintainer before tagging; the stamp ships with the version; a test asserts `audit.py` does not invoke `claude` on the deterministic path

Out of v0.1 (later): designer, writer, researcher, planner roles; srt; native Windows (WSL2 documented); retro and method log; agency-agents / grilling integration; upgrade migration (README: old `.audit.md` stay bound to their version); uninstall beyond a README section.

## Open questions / frontier

- Next: push, cut issues, build.
