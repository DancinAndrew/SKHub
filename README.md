# SKHub

Codex 與 Claude Code 的唯一個人技能及協作設定來源。agentkit 的有效能力已合併；舊的整包安裝、重複 rules、commands 和專用 reviewer 清單退役。

## 日常使用

同一台電腦只修改這個 repository。兩個工具用 symlink 讀取同一份 skill，沒有雙向複製或另一份最新版。

```bash
./install.sh --dry-run  # 查看連結及衝突
./install.sh            # 安裝、更新連結與共用個人指示
./install.sh --check    # 確認安裝沒有漂移
```

安裝入口：Codex 使用 `~/.agents/skills/`；Claude Code 使用 `~/.claude/skills/`。不再往 `~/.codex/skills/` 複製個人技能。平台內建、帳號同步及外掛內容仍由原平台管理。

安裝腳本只讀 [manifest.json](manifest.json)，不會把所有資料夾掃過後全部安裝。遇到未納管的實體檔案或連結會在任何寫入前停止，避免覆蓋個人內容。退役名稱不允許出現在啟用清單；不會自動恢復封存內容。

## 唯一維護位置

| 內容 | 位置 |
| --- | --- |
| 可公開、兩邊共用的技能 | `skills/<name>/SKILL.md` |
| 安裝清單、退役名稱與替代去向 | `manifest.json` |
| 共用個人協作準則 | `profiles/common.md` |
| Codex 專屬補充 | `profiles/codex.md` |
| Codex 既有代理設定 | `platforms/codex/agents/` |
| 個人語氣校準與未公開套件 | `.local/skills/`（不提交） |
| vault 路徑與研究入口 | `.local/config/`（不提交） |
| career-ops 執行環境及私人資料 | `.local/runtime/career-ops/`（不提交） |

`profiles/` 產生的兩份平台入口放在 `.local/generated/`，再連到各工具的全域指示檔。修改共用準則後執行 `./install.sh`；一般 skill 的內容修改因為是連結，立即反映到來源，已開啟對話可能仍持有舊內容，請在新對話驗證。

## 開發流程

`development-profile` 管理共用政策，按需求讀取規劃、除錯、review/handoff 與明確要求時的 strict TDD。新軟體專案以 OpenSpec + ADR 為預設，沿用專案已有慣例。測試與審查依風險和已接受的規則決定，不強制每次都啟動多個代理、固定覆蓋率或重做驗證。

`backend-development` 吸收 API、FastAPI、資料庫遷移、PostgreSQL、部署、容器、錯誤處理、工具伺服器及 LLM 評估／成本的條件式參考。`coding-standards`、`python-patterns`、`python-testing`、`search-first`、`git-workflow`、`security-review` 和 `selective-delegation` 分別處理具體工作。

其他技能涵蓋研究、履歷、個人寫作、旅遊、Instagram 匯出分析、Obsidian、媒體筆記、文章收錄及瀏覽器操作。完整入口以 manifest 為準，不另維護會過期的描述表。

## 更新與新增

1. 先檢查 manifest 的既有入口與退役替代去向。優先修改能承接該任務的 skill；只為獨立能力新增入口。
2. 新 skill 放進 `skills/`，登記到 manifest。大量條件式細節放 references，避免每次都載入整本手冊。
3. 執行 `python3 -m unittest discover -s tests -v` 和 `./install.sh --check`。涉及路徑／腳本時驗證實際操作；調整觸發描述時用相關與近似但不相關的真實任務檢查。格式檢查不代表模型行為已驗證。
4. 檢查 diff、私人資訊與授權，再提交 Git。上游更新按差異選擇性吸收，不整包覆蓋個人規則。

新電腦 clone 後執行 `./install.sh` 即可安裝公開部分；`.local/` 不會從 GitHub 下載。搬機時直接搬移這份本機區；缺少本機區時腳本會列出未安裝項目。career-ops runtime 缺席時不宣稱應徵追蹤可用。

## 本機資料與原生工具

`media-note` 依序使用 `MEDIANOTE_VAULTS`、`.local/config/media-note-vaults.json`、套件內的空白預設設定。現有 vault 位置不公開。`write-like-me` 含私人語氣校準，保留於本機區；`impeccable` 保留已安裝套件，沒有確認其發布授權前不轉載其套件內容。

`ego-browser` 由 ego 應用程式供應，manifest 只記錄入口與所有者。不要複製到 SKHub。Codex / Claude 的原生、同步及外掛技能同樣不納入手動維護。

本 repository 不保存原始履歷、私人對話、日記、付費課程原文、API key 或整份平台帳號設定。外部來源與整合去向見 [ATTRIBUTIONS.md](ATTRIBUTIONS.md)。
