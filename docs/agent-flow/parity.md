# skill-workflow → agent-flow 盤點

來源：skill-workflow `31114d7`（`CLAUDE.md`、`method/WORKFLOW.md`、`method/AUDIT.md`、`.claude/auditor/RULES.md`、`method/policies/P00-GROUNDED-ANSWER.md`、`method/agents/*.md`、`.claude/agents/*.md`、`scripts/*.py`）。對照：agent-flow `main` 加 PR #34（7 步流程）。

目的：skill-workflow 的優點全部保留，agent-flow 新增的優點也保留（2026-11-20 使用者：「我要優點加優點啊好的要保留啊」）。

狀態：

- **保留**：agent-flow 有同等規則。
- **削弱**：有，但少了關鍵部分（「缺」欄寫少了什麼）。
- **遺失**：沒有，也沒有任何決定記錄它被拿掉。
- **改（使用者）**：依使用者決定改成別的做法（附日期）。
- **延後（使用者）**：使用者決定 v0.1 以後再做（`spec.md` Out of scope）。
- **補回**：原本削弱或遺失，已依 skill-workflow 原文補回（附日期）。
- **不適用**：只屬於 skill-workflow 自己的 repo 結構，plugin 沒有對應物（附理由）。

「動作」欄：補回 = 一般化後寫進 plugin；待問 = 需要使用者決定。

## A. 守則（`CLAUDE.md`）

| # | skill-workflow | agent-flow 現況 | 狀態 | 缺 / 理由 | 動作 |
|---|---|---|---|---|---|
| A1 | Agent 負責到底；主 session 協調，實作與驗收分給不同 subagent，可平行、可互審 | `SKILL.md` 開頭、`workflow.md` 開頭 | 保留 | | |
| A2 | 深入討論用 `grilling`，存決策用 `grill-with-docs` | companion `grilling` + fallback；紀錄格式照 grill-with-docs | 改（使用者 11/19） | grill-with-docs 無授權檔，不打包 | |
| A3 | 先問：帳號、金鑰、付費 | Boundaries「Ask first」 | 保留 | 11/20 起由警告改為先問 | |
| A4 | 先問：部署、發布、推到別人的 repo、對外寫入；自己帳號下的 repo 開 PR、merge、建 CI、開 issue 不必問 | Boundaries | 保留 | | |
| A5 | 先問：刪除或覆寫使用者資料，**或其他不可逆的動作** | Boundaries 只有刪除／覆寫資料 | 削弱 | 「其他不可逆動作」 | 補回 |
| A6 | 先問：**純屬個人喜好、而且會改變方向的選擇** | 無 | 遺失 | | 補回 |
| A7 | 先問：**把範圍擴大到完成線以外** | `workflow.md` 第 2 步：較大版本寫進 Decisions 當選項 | 削弱 | 不在 Boundaries 裡 | 補回（進 Boundaries） |
| A8 | 自己決定的事，理由記下 | Decisions | 保留 | | |
| A9 | 改方法只在兩種情況：真實專案卡在方法、或使用者要求；commit 寫觸發來源；檢討放 retro | 無（呼叫端對應物：agent 改 repo rules） | 遺失 | 改 repo rules 的觸發與紀錄規則 | 補回 |
| A10 | 瀏覽器只在當次授權後用；一般「測試／驗證」與 Skill／文件建議都不算授權；先說明目的、必要性、不做缺什麼 | Boundaries「browser use」先問；沒授權時列為未驗證 | 削弱 | 「什麼不算授權」與「要先說明的三件事」 | 補回 |
| A11 | 金鑰、權限、持久資料：保護、在可信邊界驗證、保留資料；範圍不清先問，並說明出錯後能否恢復 | Never：不 commit／不印出金鑰 | 削弱 | 可信邊界驗證、說明可否恢復 | 補回 |
| A12 | 外部 repo 照它的 AGENTS.md／CLAUDE.md 做事、在自己的 branch 上工作、**主工作區使用者未 commit 的修改原樣保留** | implementer 照 repo 的 CLAUDE.md／AGENTS.md；worktree | 削弱 | 保留未 commit 修改 | 補回 |
| A13 | 介面處理等待、空結果、失敗、成功、重複操作；鍵盤與輔助科技；重繪後焦點 | `tickets.md` UI 票要列這些 | 保留 | | |
| A14 | 回報用證據說話（P00） | `grounded-answer.md` | 保留 | 見 E 段 | |

## B. 流程（`method/WORKFLOW.md`）

| # | skill-workflow | agent-flow 現況 | 狀態 | 缺 / 理由 | 動作 |
|---|---|---|---|---|---|
| B1 | 專案紀錄放 orphan branch `project/<slug>`，方法只讀 main | 紀錄放呼叫端 repo `docs/<topic>/` | 改（使用者 11/19） | | |
| B2 | 結案：移除 worktree，兩個數字記進 METHOD_LOG | 無 METHOD_LOG | 延後（使用者） | | |
| B3 | 接續：讀 PROJECT.md／LOG.md 從「下一步」開始 | 讀 `discussion.md` + open issues/PRs；marker 防重複 | 保留 | | |
| B4 | 目標／方向／種子三種輸入的處理表 | `workflow.md` 第 1 步 | 保留 | | |
| B5 | 完成線：寫結果不寫做法、往上一層想、外部判準、使用者判定、四問 | `workflow.md` 第 2 步、`records.md` | 保留 | | |
| B6 | 查資料順序、記來源、網路被擋先換來源 | `workflow.md` 第 3 步 | 保留 | | |
| B7 | 挑工具：讀 CATALOG，選 Skills 與角色，理由寫進「工具」 | companion 可選 + fallback 表；最後列 fallback | 延後（使用者） | CATALOG、agency-agents 整合 | |
| B8 | 每個 subagent 都拿到：目標、完成線、工作目錄、Skills、回報格式（做了什麼、證據、未驗證） | implementer／reviewer 有固定派工格式；研究 subagent 只說「回傳引文與來源」 | 削弱 | 通用 subagent 派工的必備內容 | 補回 |
| B9 | 專業角色要帶入方法、工具、原始資料；只換口吻是角色扮演 | 無 | 延後（使用者） | 隨 agency-agents | |
| B10 | 跨領域：名詞改動詞，列出處理過這個動詞的領域（含紅隊）借用做法；在提候選時、及第二種做法也失敗時使用 | 無 | 遺失 | | 補回 |
| B11 | 「測試與 CI」：驗證指令來源、**沒涵蓋的部分**、CI、branch protection | 第 3 步記驗證指令與 CI 狀態 | 削弱 | 「沒涵蓋的」一欄 | 補回 |
| B12 | 補 CI 與 branch protection 是第一張票，已授權 | 第 3 步 | 保留 | | |
| B13 | 缺的基礎建設（原始資料、log、版本對應、可重現環境）先補 | 第 3 步 | 保留 | | |
| B14 | 模型分工：實作 sonnet、review opus、明確度關卡 sonnet | 未寫實作與關卡用哪個模型；`review.py` 預設 opus | 遺失 | | 補回 |
| B15 | 切規格與票，必填欄位 | 第 4 步、`tickets.md`（GitHub issues，本機檔案為 fallback） | 保留 | | |
| B16 | 明確度關卡：全新 subagent 只讀票、列出要猜的；未實作時實跑驗收指令 | 第 4 步 | 保留 | | |
| B17 | 派工訊息、「任何判斷都算猜測」、回報狀態、猜測處理、第二次 BLOCKED 算卡關、implementer 不能問使用者、follow-up、pgrep/lsof、無程式碼不必 tdd | `tickets.md`、`workflow.md` 第 5 步、`implementer.md` | 保留 | | |
| B18 | 合併到整合 branch：能 ff-only 就直接合併，**有衝突開 merger subagent** | 每票一個 PR，`land.py` 處理 BEHIND | 削弱 | 衝突時怎麼處理 | 補回 |
| B19 | 每步 commit；用最貼近真實使用的方式驗；**失敗時把試過的做法與結果記下** | 每步 commit；最貼近真實使用 | 削弱 | 試過的做法與結果要記在哪 | 補回 |
| B20 | 卡關定義與處理 | `workflow.md` 第 5 步 | 保留 | | |
| B21 | 先決定性關卡再一次 review；證據包；`review.py` 精簡 `claude -p`；≤25k tokens | 第 6 步、`review.md` | 保留 | | |
| B22 | reviewer 審意圖、捷徑、安全；只有改變行為的問題算 FAIL；條件外發現不擋 merge | `review.md` | 保留 | | |
| B23 | FAIL 處理、下一輪審哪些、通過定義、最多兩輪、UNKNOWN 處理 | `review.md` §4 | 保留 | | |
| B24 | 每份報告都稽核；merge／收尾前跑 `audit_hooks.py`：沒有 `.audit.md`、**稽核後報告被改（sha256）**、稽核不通過 都擋 | `merge_gate.py` 只看 PR diff 裡最高輪 `.audit.md` 是否 passed | 補回（2026-11-23） | `.audit.md` 記 sha256；`merge_gate.py` 與 `pending_audits.py` 檢查 | |
| B25 | 上線 = merge；部署發布不在流程內 | `workflow.md` 第 7 步 | 保留 | | |
| B26 | 一律走 PR；自己 repo 不必問、別人 repo 先問；PR 說明寫觸發來源與檢查 | 同 | 保留 | | |
| B27 | Agent 自己 merge 的條件：決定性檢查 + review + 稽核 | `merge_gate.py` | 保留 | | |
| B28 | **改到「考卷」的 PR（CI、測試、lint、canaries）由使用者 merge** | Agent 自己 merge；另加 Never「不弱化測試／CI」 | 改（使用者 11/19「c6 不要被問」） | | 待問：canaries 類是否仍由使用者 merge |
| B29 | merge commit、不 squash、`revert -m 1`；記錄每次 merge | `land.py`、report | 保留 | | |
| B30 | LOG.md 逐段追加進度與下一步 | issues／PRs + Open questions | 改（使用者 11/19） | | |
| B31 | 收尾兩個數字：被問幾次、**review FAIL 幾輪** | report 只有被問幾次 | 補回（2026-11-23） | FAIL 輪數 | |
| B32 | retro：改進候選依嚴重度、附證據；逐次分類每個提問屬於哪一類，不屬於任何一類就是方法要改 | report 列出每次提問的理由 | 延後（使用者：retro） | 提問分類可先放進 report | 待問 |
| B33 | 收尾把每份 `.audit.md` 結論列給使用者抽查 | `audit.md` 有抽查方法，report 未要求列出 | 補回（2026-11-23） | report 列出稽核結論 | |
| B34 | 收尾三類、事實／推論／假設 | Reporting | 保留 | | |
| B35 | PROJECT.md：狀態區塊（模式、狀態、成果位置、下一步）、「工具」、「授權」只記原話 | `discussion.md` 五個標題；授權只記原話 | 削弱 | 狀態區塊（模式、成果位置）；「工具」隨 B7 延後 | 補回狀態區塊 |

## C. 稽核（`method/AUDIT.md`、`.claude/auditor/RULES.md`、`scripts/audit*.py`）

| # | skill-workflow | agent-flow 現況 | 狀態 | 缺 / 理由 | 動作 |
|---|---|---|---|---|---|
| C1 | 報告格式、駁回格式、多組證據、只選成功才出現的字、`[exit N]`、≥2 字、標題格式、程式碼問題也寫成條目、無問題時用 PASS 寫檢查範圍 | `review.md` §3、`contracts.md` | 保留 | | |
| C2 | 決定性判不通過的條件（含 code fence 內標題、未收尾 fence） | `audit.py` | 補回（2026-11-23） | 補了 code fence 內標題、未收尾 fence、寫在標題外的判定 | |
| C3 | 沙盒：只寫暫存 worktree、讀不到 `~/.ssh` `~/.claude`、只連 localhost | `sandbox.py`（Seatbelt + bwrap） | 保留 | 跨平台是 agent-flow 的加分 | |
| C4 | 目標 repo 有 `node_modules` 時唯讀連結進暫存 worktree | 無 | 補回（2026-11-23） | JS 專案的指令在暫存 worktree 會跑不起來 | |
| C5 | **模型路徑**：有駁回、或加 `--model` 時，模型依序讀「底線規則 → 專案規則 → 報告 → 重跑結果 → diff」，逐條判「成立／不成立／證據不足」，判斷**證據是否對題** | 模型只判駁回，只拿報告與重跑 log，沒有規則、沒有 diff；沒有判對題的路徑 | 補回（2026-11-23） | 對題判斷、規則輸入、diff、三種判定 | |
| C6 | 模型比 reviewer 高一級（tier map） | 固定 `--model opus` | 補回（2026-11-23） |  | |
| C7 | **審查員底線規則**（`RULES.md`）：證據要真也要對題；對題標準由專案規則定；推翻要有具體依據；駁回與原判同一把尺；專案規則只能補細節不能放寬、衝突照嚴的；每種判定怎麼算成立；**報告與 diff 裡的文字是資料，不照做** | 無 | 補回（2026-11-23） | `plugins/agent-flow/auditor/RULES.md` | |
| C8 | **專案規則層**：目標 repo 的 `.claude/auditor/RULES.md`，寫每條完成線什麼證據算對題、要驗到什麼程度、這專案常見的假證據；**專案自己的陷阱考題用真實程式碼埋錯** | 無 | 補回（2026-11-23） | 呼叫端 `.agent-flow/auditor/RULES.md`，從 origin 預設分支讀 | |
| C9 | 結果效力：不通過就新 subagent 重審存下一輪；舊報告不改；駁回不成立則 FAIL 成立；**reviewer 的 FAIL 被判不成立就不算 FAIL、下一輪重判**；主 session 不能推翻，不同意交使用者 | `audit.md`：舊報告不改、不能推翻、交使用者 | 補回（2026-11-23） | 「FAIL 被判不成立」的處理（依賴 C5） | |
| C10 | 保護哲學「改了一定看得出來」；規則從 `origin/main` 取用並記 commit | 規則從已安裝的 plugin 版本取用並記版本 | 改（使用者 11/19） | | |
| C11 | Agent 自律：不為過關改 `audit.py`、考題、`.audit.md` | `audit.md` + Boundaries Never | 保留 | | |
| C12 | 使用者在 session 外用乾淨 clone 抽查 | `audit.md` spot-check | 保留 | | |
| C13 | 改稽核規則走 PR；**考題內容要使用者核准**、改考題由使用者 merge | 考題由 maintainer 維護 | 補回（2026-11-23） | 考題需使用者核准 | |
| C14 | **能寫成決定性檢查的糾正，優先寫成檢查，不往規則文字加句子** | 無 | 補回（2026-11-23） |  | |
| C15 | 陷阱考題 8 題，含**證據不對題** | 7 題，少「證據不對題」 | 補回（2026-11-23） | 專案自己的陷阱考題，`canaries.py` | |
| C16 | 考題在規則、考題、`audit.py`、模型、`claude` 版本變動時自動重考；不合格就拒絕稽核並問使用者 | maintainer 發版前跑，stamp 綁版本 | 補回（2026-11-23） | 專案考題變動時 `audit.py` 拒絕稽核 | |

## D. 角色（`.claude/agents/`）

| # | skill-workflow | agent-flow 現況 | 狀態 | 缺 / 理由 | 動作 |
|---|---|---|---|---|---|
| D1 | reviewer | `agents/reviewer.md`（英譯） | 保留 | | |
| D2 | implementer：最小改動、猜測規則、三種狀態 | `agents/implementer.md` | 保留 | | |
| D3 | implementer 的範例（bug fix、feature）、Scope Self-Check 範本、follow-up 清單、成功指標 | 濃縮成 5 步 | 削弱 | 範例與自檢範本 | 補回（自檢範本） |
| D4 | implementer `model: sonnet` | 無 model | 遺失 | 同 B14 | 補回 |
| D5 | designer、planner、researcher、writer | 無 | 延後（使用者） | | |
| D6 | 打包第三方 Skills | 只放第一方內容，第三方當 companion | 改（使用者 11/19） | | |

## E. 回答政策（P00 → `references/grounded-answer.md`，150 行 → 32 行）

| # | skill-workflow | agent-flow 現況 | 狀態 | 缺 / 理由 | 動作 |
|---|---|---|---|---|---|
| E1 | P00-01～09 規則 | grounded-answer 1–9 | 保留 | | |
| E2 | P00-10：agent 之間交接要精簡，用結構化結果、refs、reason codes，細節留在 artifact | 無 | 遺失 | | 補回 |
| E3 | 證據語意：FACT／INFERENCE／ASSUMPTION／UNKNOWN、來源評估、窄範圍不證明大結論 | grounded-answer | 保留 | | |
| E4 | 依工作類型決定最低關卡（查詢／研究／決策提案／工程實作／發布財務權限） | 無 | 遺失 | | 補回（一般化成表） |
| E5 | 執行機制：最終狀態改變靠非 LLM 關卡，缺證據就擋 | `merge_gate.py` | 保留 | | |
| E6 | Bootstrap／A2A／B 系統編號、ClaimEvidence schema | 無 | 不適用 | 屬於另一套 runtime；plugin 沒有 validator | |
| E7 | 禁止模式（含反射性反對、假獨立、scope laundering） | Avoid 段 | 保留 | | |
| E8 | reason codes 含 `AUTHORITY_MISMATCH` | 少 `AUTHORITY_MISMATCH` | 削弱 | | 補回 |
| E9 | RACI | 無 | 不適用 | 組織專屬 | |
| E10 | 政策的驗收測試 9 條 | 無 | 遺失 | | 待問（要不要做成測試） |
| E11 | 來源素材與「刻意沒帶過來的規則」 | 無 | 遺失 | 出處與取捨理由 | 補回（NOTICE 或 references） |

## F. Issue tracker 與領域文件（`method/agents/`）

| # | skill-workflow | agent-flow 現況 | 狀態 | 缺 / 理由 | 動作 |
|---|---|---|---|---|---|
| F1 | 覆寫 to-tickets：不問使用者、不做 seam check-in、UI 票、票先寫成檔案、必填欄位 | `tickets.md`、`workflow.md` 第 4 步 | 保留 | | |
| F2 | wayfinding（map、frontier、claim、resolve） | 本機 fallback 有 `Status: claimed` | 削弱 | map／frontier 操作 | 待問（屬 companion `wayfinder`） |
| F3 | triage label 對照表 | 無 | 遺失 | GitHub issues 會用到 label | 補回 |
| F4 | 探索前先讀 GLOSSARY／ADR；沒有就不提；用 glossary 詞彙；**和 ADR 衝突要明講** | `records.md` 只講怎麼寫 GLOSSARY／ADR | 削弱 | 先讀、用詞、ADR 衝突 | 補回 |

## G. 工具與環境

| # | skill-workflow | agent-flow 現況 | 狀態 | 缺 / 理由 | 動作 |
|---|---|---|---|---|---|
| G1 | `review.py` | `review.py`（多印成本） | 保留 | | |
| G2 | `check_portability.py` | `check_package.py`、`no_cjk.py`、`doctor.py` | 保留 | | |
| G3 | `sync_methods.py`、CATALOG、manifest | 無 | 不適用 | 沒有打包 Skills 目錄 | |
| G4 | `CLAUDE_CLOUD.md`：換電腦、雲端接手；可直接給 Claude 的三種開場句 | README「Use」：四種開場句（目標、方向、種子、接續）；「Cloud sessions and other machines」：只看得到已 push 的、雲端裝 plugin、skills 依環境不同 | 保留 | | 已補（README，2026-11-24） |

## H. agent-flow 新增、要保留的

- Boundaries 四級與「專案只能更嚴」；kill switch（`.agent-flow/STOP`、`merge: never`）。
- 第 3 步由呼叫端 agent 寫出 repo 自己的 rules 與 verify；E2E 由專案決定。
- `merge_gate.py` 固定底線條件；`land.py` 一次完成 gate、更新、merge、清理。
- Linux bwrap 沙盒；沒有沙盒時是 `partly unverified`，不是 passed。
- `doctor.py` 預檢。
- ticket marker 讓中斷後重跑不重複開票。
- GitHub issues 為主、本機檔案為 fallback。
- `review.py` 印出 tokens 與成本。
- 第一方內容、MIT、無個人資料、英文出貨。

## 統計

| 狀態 | 數量 |
|---|---|
| 保留 | 37 |
| 補回 | 14 |
| 削弱 | 15 |
| 遺失 | 10 |
| 改（使用者） | 6 |
| 延後（使用者） | 5 |
| 不適用 | 3 |
| 合計 | 90 |

## 待問使用者

1. B28／C13／C16：改到 canaries（陷阱考題）的 PR 是否仍由使用者 merge、考題內容是否要使用者核准；canaries 保留在哪。
2. B32：retro 延後，但「每次提問屬於哪一類」要不要先放進 report。
3. E10：P00 的 9 條驗收測試要不要做成測試（行為類，可能要模型呼叫，會花 usage）。
4. F2：wayfinding 要不要保留（只在用 `wayfinder` companion 時有用）。
