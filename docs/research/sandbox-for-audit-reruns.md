# audit.py 重跑 reviewer 證據指令：沙盒研究

研究日期：2026-11-19。只讀官方文件／官方 repo；每項主張附來源編號（見末尾來源清單）。標記：**[事實]** 來源直接寫的；**[推論]** 我的推論；**[假設]** 未驗證前提；**未知**＝查不到。

## 結論摘要

1. **[推論]** 沙盒不是「重跑」的絕對必要條件，但「由腳本自動重跑模型寫的任意指令、沒有人逐條確認」正是官方文件要求加隔離邊界的情境（S3：無人值守需要 container／VM／sandbox runtime）。所以：任意指令要有沙盒；沒沙盒時只能跑受限的指令。
2. **[事實]** 主流 agent 都把沙盒當第二道防線，且都有「沙盒不可用」的處理：Claude Code 預設 fail-open（S1）、Cursor 退回逐次詢問（S8）、Codex 建議由 container 提供隔離（S6）。沒有一家把「沒沙盒就直接判失敗」當預設。
3. **[事實]** 跨平台沒有單一方案：macOS 內建 Seatbelt；Linux 要裝 bubblewrap；原生 Windows 在 Claude Code 沒有沙盒（S1）、Codex 有自己的 Windows 沙盒（S7）、srt 的 Windows 還是 alpha 且需提權安裝（S2）。
4. **[推論]** 建議：分層。預設＝argv 白名單（不經 shell、唯讀指令）；偵測到沙盒（macOS Seatbelt／Linux bwrap）才額外允許「專案測試類」指令；都沒有就跳過那些指令並標「未驗證」，不要直接判不通過，也不要不設防地執行。
5. **[推論]** 不建議內建依賴 srt（0.0.x、Beta、設定格式可能變、Windows alpha）；若採用，作為可選整合並鎖精確版本。

## 1. 威脅模型：沙盒必要嗎？

- **[事實]** Anthropic 把 prompt injection 列為威脅：攻擊者在輸入裡塞惡意文字去覆蓋 AI 的指示（S4）。Claude Code 自己的防護是權限系統（Manual mode 敏感操作要明確核准）、網路指令預設不自動核准、指令注入偵測、fail-closed matching（S4）。**這些都是「逐次人工／classifier 把關」，不是 audit.py 這種自動重跑會有的東西。**
- **[事實]** 官方沙盒文件寫明 OS 強制的邊界「不管模型選了什麼指令都成立，即使被允許的指令做的事比名稱暗示的更多」（S1）。同頁也警告：不要依賴沙盒限制去擋「惡意指令」（針對 `allowNestedUserNamespaces` 等放寬設定）（S1）；沙盒「降低風險但不是完整隔離邊界」（S1）。
- **[事實]** 官方比較頁：有人逐次核准時，權限模式決定「是否執行」，隔離決定「執行後能碰什麼」；無人值守（`--dangerously-skip-permissions`）必須在 container／VM／sandbox runtime 內；Bash 沙盒「單獨使用不足以支撐完全無人值守」；auto mode 的 classifier 是逐動作控制而非隔離邊界，隔離屬於 defense in depth、非必須（S3）。
- **[事實]** Codex：「Prompt injection 可讓 agent 抓取並遵循不可信指示」，預設 `workspace-write` 沙盒關網路，並保護 `.git`、`.codex` 唯讀（S6）。Cursor：預設封網路、保護 `.git/hooks` 等（S8）。
- **[事實]** 「受審程式碼本身在測試時執行」這點：官方沒有針對 audit 重跑的專門討論（**未知**）。一般性說法：Claude Code 建議處理不可信內容時用 VM 跑腳本與工具呼叫（S4）；GitHub 把 self-hosted runner 視為「可被不可信程式碼持久入侵」，GitHub-hosted 則是 ephemeral VM（S10）。
- **[推論]** 你們的情況與使用者前提：主 session 本來就無沙盒跑 `yarn test`。差別在於**指令來源**——主 session 跑的是專案自己定義的 script（使用者已信任該 repo），audit.py 跑的是「reviewer 報告裡的字串」，這個字串可被 injection 影響，且 audit.py 沒有人工核准那一關。所以「主 session 也沒沙盒」不能直接推出「audit 重跑不需要」：兩者的信任來源不同。**[假設]** reviewer 在審查時讀過不可信內容（PR 內容、依賴碼、網頁）；若 reviewer 只讀使用者自己的 repo，風險較低但仍非零。
- **[推論]** 但沙盒是「放寬到任意指令」的條件，不是「重跑」本身的條件：若只重跑唯讀、argv 白名單內的指令（`git diff`、`grep`），沒有沙盒風險也很小（仍可能讀到祕密並寫進報告，見下方限制）。

## 2. 方案比較

| 方案 | 跨平台 | 安裝門檻 | 強度（官方描述） | 主要限制 |
|---|---|---|---|---|
| macOS Seatbelt（`sandbox-exec`） | 僅 macOS | 無（內建）（S1, S2, S6） | 核心機制被 Claude Code、Codex、Cursor、Gemini CLI 採用（S1, S6, S8, S9） | man page 標示 DEPRECATED（S12，見下註）；profile 要自己寫或用 srt 產生 |
| bubblewrap | 僅 Linux／WSL2（WSL1 不支援） | 要裝 `bubblewrap`（Claude Code 另需 `socat`）（S1） | 建 mount namespace；「不是現成完整 sandbox，保護取決於呼叫者給的參數」；掛進去的東西（如 D-Bus socket）可能被用來提權（S11） | 依賴 unprivileged user namespaces；Ubuntu 24.04+ 需放寬 AppArmor userns 限制（S2）；container 內常需弱化模式（S1, S6） |
| Anthropic sandbox-runtime（srt） | macOS／Linux；Windows alpha（S2） | `npm i -g @anthropic-ai/sandbox-runtime`，Node >=22.12（S13）；Linux 另需 bwrap、socat、ripgrep；macOS 需 ripgrep；Windows 需一次性提權 `windows-install`（S2） | 預設網路全擋、最小權限（S2）；Apache-2.0、npm 最新 0.0.83（S13） | Beta research preview，「API 與設定格式可能改變」（S2, S3）；Windows alpha，Schannel 不能用（curl.exe、Invoke-WebRequest 等 HTTPS 失敗）（S2）；Linux glob 支援較窄（S2）；網路過濾靠 hostname，不檢查 TLS，可能 domain fronting（S1） |
| Claude Code 內建沙盒 | macOS、Linux、WSL2；**原生 Windows 無**（S1） | macOS 無；Linux 裝 bwrap+socat（S1） | OS 強制；讀取預設可讀大部分機器含 `~/.ssh`，需自行 deny（S1） | **預設 fail-open**（不支援／依賴缺失就無沙盒執行，除非 `failIfUnavailable: true`）；失敗後可用 `dangerouslyDisableSandbox` 無沙盒重試；hooks、MCP、Read/Edit 等在沙盒外（S1）。這是 Claude Code 的功能，不是給外部 plugin 呼叫的函式庫 **[推論]** |
| Codex CLI | macOS Seatbelt；Linux bwrap+seccomp（0.115 起，WSL1 不支援）；Windows 原生 `mxc`／`elevated`／`unelevated`（S5, S6, S7） | macOS 無；Linux 裝 bwrap（無則用內建 helper，需 userns）；Windows `elevated` 需管理員核准的設定、`mxc` 需 Windows 11 24H2/25H2 特定 build（S5, S7） | 預設 `workspace-write`、網路關、`.git` 等唯讀（S6）；Windows `unelevated` 網路隔離較弱、不支援 deny read（S7） | 沙盒不可用時文件建議在 container 層隔離再用 `danger-full-access`（S6）；MXC 的 deny-read glob 只在 process 啟動時評估（S7） |
| Gemini CLI | macOS Seatbelt；Docker/Podman（跨平台）；Windows 原生（`icacls` Low Mandatory Level，且完整性設定在 session 結束後仍保留）；gVisor、LXC 僅 Linux（S9） | 預設**關閉**；容器法需 Docker/Podman（S9） | Seatbelt 預設 profile `permissive-open`：寫入限專案目錄、**讀與網路寬鬆**；gVisor 號稱最強（S9） | 不同後端強度差很大；Windows 方案會改檔案 ACL 且持久（S9） |
| Cursor | macOS Seatbelt（`sandbox-exec`）；Linux Landlock+seccomp（要 kernel ≥6.2、Landlock v3、userns）；Windows 文件未提（S8）。**注意**：搜尋結果中的 TypeScript SDK 文件寫 Linux 用 bubblewrap，與 run-modes 頁的 Landlock 說法不一致（S8, S14），後端以哪個為準**未知** | 無額外安裝（S8） | 預設封網路、保護 `.git/hooks` 等；讀取預設「System」可讀工作區外（S8） | 核心不支援時**退回逐次詢問核准**；沙盒失敗時 agent 可在沙盒外重跑，交給 classifier 審（S8） |
| Aider | 無 | 無 | 官方指令文件只說 `/run`、`/test` 執行 shell 指令；**未提沙盒或安全**（S15） | 未知（沒找到沙盒文件） |
| OpenHands | Docker（建議）／process／remote（S16） | 需 Docker | Docker「與主機良好隔離」；process 模式「不安全但快」，無容器隔離（S16） | 預設為 docker（legacy `RUNTIME` 變數）（S16）；需要 Docker |
| Container／devcontainer | 跨平台（靠 Docker） | 需 Docker；Windows/macOS 實際是 VM 內跑 Linux **[推論]** | Anthropic 範例 devcontainer 有預設拒絕的 iptables 防火牆，可支援無人值守（S3） | 掛載可寫的專案仍可被改；有網路就可外洩可讀資料（S3）；使用門檻高、不適合在使用者機器上被 plugin 臨時叫起 **[推論]** |
| CI runner（GitHub Actions） | 雲端 | 需 workflow 設定 | GitHub-hosted 為 ephemeral 隔離 VM；self-hosted 可被持久入侵（S10） | `pull_request_target` 下 checkout 不可信碼會暴露 secrets；不在使用者本機（S10）。**[推論]** 這是「另一種部署形態」，不是本機 audit.py 的替代 |
| VM／microVM（Firecracker、e2b、Docker Sandboxes） | Firecracker 只跑在 Linux 主機（S17）；e2b 為託管雲、需 `E2B_API_KEY`（S18）；Docker Sandboxes 平台與狀態文件未說明（S19） | 高（帳號／KVM／額外產品） | 官方比較頁稱 VM「最強隔離」、有獨立 kernel（S3）；Firecracker 預設 seccomp、jailer，且不過濾 guest 出站流量，要自己在主機過濾（S17） | 對開源 MIT plugin 的陌生使用者而言需帳號或額外安裝 **[推論]**；本研究不建議 |
| 指令白名單／不經 shell 的 argv | 全平台（Python `subprocess` list 形式不隱式呼叫 shell；Windows 的 `.bat/.cmd` 例外）（S20） | 無 | **不是隔離**：只限制「能跑什麼」，擋 shell metacharacter 注入；被允許的程式仍可做它能做的事（如 `git` 可經設定／hook 執行程式、`grep` 可讀任何可讀檔案）**[推論]**。Claude Code 自己的 deny 規則也是「按字面比對」，網路強制要靠沙盒（S4） | 無法涵蓋 `yarn test` 這類執行任意專案程式碼的指令；要維護白名單與 `git -c`、`--exec-path` 之類旗標的黑名單 **[推論]** |

註（S12）：`sandbox-exec` 的 DEPRECATED 字樣來自 man page 的鏡像網站（二手，僅作線索）；Apple 官方頁面我沒取得內容，故「Apple 官方是否有公告淘汰時程」＝**未知**。實務上 Claude Code、Codex、Cursor、Gemini CLI 官方文件都仍在用它（S1, S6, S8, S9）。

## 3. 對 agent-flow 的建議

### 預設做法（推論）

1. **argv 執行層永遠開啟**：reviewer 報告裡的證據指令先解析成 argv（`shlex.split`，POSIX 規則；Windows 路徑要另處理），`subprocess.run(argv, shell=False)`，拒絕含 `|`、`;`、`&&`、重導、`$()` 的字串，對白名單程式（`git diff/log/show/status`、`grep`/`rg`、`cat`/`ls` 等唯讀）執行。理由：跨平台、零安裝、擋掉 shell 注入（S20）。限制：白名單內程式仍能讀祕密，所以輸出寫入報告前要考慮遮蔽 **[推論]**。
2. **「專案測試類」指令（`yarn test` 等）只在有沙盒時才自動重跑**：沙盒偵測順序：macOS `sandbox-exec` → Linux `bwrap`（含 userns 可用性探測）→ 其他不可用。沙盒策略沿用現有設計（只寫暫存 worktree 與 scratch、不讀 `~/.ssh` `~/.claude`、網路只到 localhost），與 Codex／Cursor 預設一致（S6, S8）。
3. **Windows**：沒有官方、免提權、已 GA 的第三方可呼叫方案（Claude Code 原生 Windows 無沙盒；srt Windows alpha；Codex 方案是 Codex 內建）（S1, S2, S7）。建議 Windows 使用者走 WSL2（此時按 Linux 路徑），原生 Windows 只做第 1 點。

### 沒有沙盒可用時的退路（推論）

- 不要像現況「直接判不通過」：這讓大多數 Linux（沒裝 bwrap）與 Windows 使用者永遠過不了，而主流工具的做法是降級而非失敗——Cursor 退回逐次核准（S8）、Codex 建議容器層隔離（S6）。
- 也不要像 Claude Code 預設那樣靜默 fail-open（S1）：對自動重跑、無人把關的場景太寬。
- 建議退路：**降級並明講**。無法在沙盒內跑的指令標記為「未驗證（需人工執行）」，audit 結論分三態（通過／未通過／部分未驗證），把指令原文印給使用者自己跑；另提供顯式 opt-in（如 `--unsafe-run-in-place`，文字註明等同信任報告內容）給願意承擔的人。三態與旗標設計是我的建議，非來源內容。
- 對使用者的事實前提「主 session 本來就無沙盒跑測試」：可作為 opt-in 的理由，但要在文件寫清楚指令來源不同（見第 1 節推論）。

### 要不要鎖版本（推論）

- **srt**：不建議作為預設硬依賴。理由：npm 最新 0.0.83、Beta research preview、設定格式可能變、Windows alpha（S2, S3, S13），且需 Node >=22.12（S13）。若提供整合：可選依賴、鎖**精確版本**（不用 `^`）、啟動時檢查版本與設定檔載入（官方提醒：設定檔不存在時 srt 仍會啟動，「不要把乾淨啟動當成設定已載入」，S3），並用自己的 fixture 驗證「`cat ~/.ssh/...` 被擋、對外 curl 被擋」（S2 範例）。授權 Apache-2.0 與 MIT 專案的相容性**未驗證**，發佈前自行確認。
- **自寫 `sandbox-exec` profile／bwrap 參數**：不存在版本問題，但維護成本在你。bwrap 文件明說保護取決於你給的參數（S11），且要處理 `--new-session`（TIOCSTI，S11）。若自寫，建議讀 srt 原始碼當對照（S2）。
- **Seatbelt**：man page 標 DEPRECATED（S12）。把 macOS 路徑集中在單一模組，之後換掉時只改一處。

### 仍未驗證／未知

- Anthropic 或 Apple 對 `sandbox-exec` 的官方淘汰時程：未知。
- Codex Linux 用 Landlock 與否：Codex 文件說 `bwrap` + `seccomp`、未提 Landlock（S6）；Cursor 文件說 Landlock+seccomp，SDK 文件說 bubblewrap（S8, S14），兩者不一致。
- 官方文件沒有直接討論「自動重跑 LLM 產生的審查證據指令」這個具體情境；上述對應是我從無人值守與 injection 的一般說法推論的。
- 本研究沒有實際跑過任何沙盒工具，所以各方案在 agent-flow 目標環境（含 yarn test 能否在沙盒內跑通，例如 srt README 提到 Jest 需 `--no-watchman`，S2）的實際相容性**未驗證**。
- Aider 沙盒：只讀了指令頁，未找到沙盒文件；不代表沒有。
- Docker Sandboxes 的平台支援與成熟度：頁面未說明。

## 來源清單

WebFetch 內容由小模型摘要，引文以其回傳為準；關鍵數字（版本、平台、預設值）建議實作前再對原頁複核。

- S1 Claude Code Sandboxing：https://code.claude.com/docs/en/sandboxing（亦取 .md 版 https://code.claude.com/docs/en/sandboxing.md）
- S2 anthropic sandbox-runtime README：https://github.com/anthropics/sandbox-runtime（讀取時曾導向 anthropic-experimental 路徑；僅讀到約前 100k 字元）
- S3 Claude Code Sandbox environments：https://code.claude.com/docs/en/sandbox-environments.md
- S4 Claude Code Security：https://code.claude.com/docs/en/security.md
- S5 Codex Sandboxing：https://developers.openai.com/codex/concepts/sandboxing（轉址至 https://learn.chatgpt.com/docs/sandboxing）
- S6 Codex Agent approvals & security：https://developers.openai.com/codex/agent-approvals-security（轉址至 https://learn.chatgpt.com/docs/agent-approvals-security）
- S7 Codex Windows sandbox：https://developers.openai.com/codex/windows（轉址至 https://learn.chatgpt.com/docs/windows/windows-sandbox）
- S8 Cursor Run Modes：https://cursor.com/docs/agent/security/run-modes
- S9 Gemini CLI sandbox：https://github.com/google-gemini/gemini-cli/blob/main/docs/cli/sandbox.md
- S10 GitHub Actions secure use：https://docs.github.com/en/actions/reference/security/secure-use
- S11 bubblewrap README：https://github.com/containers/bubblewrap
- S12 sandbox-exec man page 鏡像（二手，僅線索）：https://keith.github.io/xcode-man-pages/sandbox-exec.1.html
- S13 npm registry `@anthropic-ai/sandbox-runtime`（0.0.83、Apache-2.0、node >=22.12.0）：https://registry.npmjs.org/@anthropic-ai/sandbox-runtime/latest
- S14 Cursor TypeScript SDK（僅見於搜尋結果摘要，未直接讀取）：https://cursor.com/docs/sdk/typescript
- S15 Aider commands：https://aider.chat/docs/usage/commands.html
- S16 OpenHands sandboxes：https://docs.openhands.dev/openhands/usage/sandboxes/overview
- S17 Firecracker design：https://github.com/firecracker-microvm/firecracker/blob/main/docs/design.md
- S18 E2B docs：https://docs.e2b.dev/
- S19 Docker Sandboxes：https://docs.docker.com/ai/sandboxes/
- S20 Python subprocess：https://docs.python.org/3/library/subprocess.html
