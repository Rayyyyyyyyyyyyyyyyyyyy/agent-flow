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
- 2026-11-19 user (「照你建議的沙盒做法」): audit reruns use (1) file-read evidence + read-only argv allowlist with `shell=False` on all platforms; (2) project-code commands only under a detected sandbox (macOS Seatbelt, Linux bwrap), isolated in one module; (3) otherwise three states passed / failed / partly unverified, unverified commands printed for the user or run with an explicit per-run opt-in, partly unverified blocks agent merge; (4) srt optional, never required; native Windows → WSL2. Source: `docs/research/sandbox-for-audit-reruns.md`.

## Finish line (draft, not yet confirmed)

- C1 installable: in a fresh `HOME`, `claude plugin validate`, `marketplace add`, `install` exit 0
- C2 entry works: in a fixture repo, `claude -p` invoking the skill produces `docs/<topic>/discussion.md` with the required sections (script check)
- C3 first-party only, licenses clear: no vendored third-party skill; LICENSE + NOTICE; roles derived from agency-agents (MIT) keep its notice (script check)
- C4 works without companions: fresh `HOME`, only this plugin, C2 fixture passes
- C5 no personal data: grep for handle, `/Users/`, email, `rtk`, `ponytail`, `Asia/Taipei` = 0
- C6 autonomous by default: inside the repo where it is invoked, the agent branches, commits, pushes, opens PRs, verifies and merges its own PRs once the gates pass, without asking. It stops only for accounts/secrets/payment, deploy or publish outside the repo, writes to repos it does not own, and irreversible deletion of user data (fixture run: zero questions to the user, PR merged with gates green)
- C7 cross-platform: script tests green on GitHub Actions macOS + Ubuntu; without a usable sandbox, project-code evidence is "unverified" (never "passed") and blocks agent merge
- C8 English: CJK count in the plugin dir = 0; skill tells the agent to answer in the user's language
- C9 releasable: tag `v0.1.0`, CHANGELOG, README install steps; install from the tag works
- C10 dogfooded: one ticket end to end (CI, review, audit, merge) in a fixture repo, with the record

## Open questions / frontier

- Waiting for the user's go before cutting tickets.
