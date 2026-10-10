# Bullet 寫法

## 公式

**主動動詞 + 你具體做了什麼 + 可量化的結果或影響 + 用了什麼技術**

也可以想成「透過 {具體貢獻}，達成 {影響}，用 {數字} 衡量」。順序不必死守，但前三個元素至少要有。
要傳達的是：你能獨立做事、你的工作讓團隊或公司變好、你知道自己的工作為什麼重要。職級越高，這個期待越強。

## 可以量化的東西（只挑真的有的）

- 規模：使用者數、QPS/RPS、事件量、資料量、客戶數、採用的團隊數
- 品質：錯誤率、可用性、測試覆蓋率前後、偵測率、準確率
- 速度：延遲、建置或部署時間、處理時間、時程提前
- 成本：基礎設施費用、人工工時、support ticket 數
- 商業：營收、轉換率、留存
- 人：帶幾個人、mentor 幾位、workshop 參與人數、社群規模
- 開源：被合併的 PR、專案規模（stars、下載數）

## 找不到數字時

1. **問**：現職就問團隊或主管這件事的預期或實際影響；前職可以聯絡前同事。
2. **估**：用前後對比、抽樣、歷史紀錄估出數量級，寫成 `~`、`estimated` 或區間。
3. **換**：沒有成果數字，就用規模或複雜度數字（整合了 N 種資料源、N 個系統）。
4. **留空**：草稿用 `[N]` 佔位並列入待補清單。**不要編。**

## 數字說不完整的工作（排查、溝通、判斷）

Support、solution engineering、資料治理這類工作，價值常在判斷與轉譯，不在件數。少量的件數（例如兩個月 10 張 ticket）單獨寫出來反而顯得小。改用這四種證據，任選兩三種組成一條：

1. **複雜度**：問題有幾種路徑或變數、資料量、牽涉幾個系統（`across [N] deletion paths`、`100K+ records`）
2. **判斷**：你在不確定中做了什麼決定、依據是什麼（`decided per case whether records were safe to delete`）
3. **產出物**：留下了什麼可交接的東西——root-cause 報告、含重現步驟的 ticket、runbook、給非技術同事的說明
4. **結果**：之後發生了什麼——被修好、被排進 roadmap、CSM 能直接回覆客戶、同類問題不再升級

句型：`[動詞] [複雜的東西]，[做了什麼判斷或分析]，[產出物] that [結果]`。
例（示意）：`Traced LLM-agent failures through execution traces (tools never called, guardrails not firing) and wrote reproducible tickets that Product used to prioritise fixes.`

## 弱 → 強 的改寫模式

以下範例只示範句型，不是真實經歷。

| 弱 | 問題 | 強 |
| --- | --- | --- |
| `Worked on the payment service.` | 只有職責 | `Added idempotency keys to the payment webhook consumer, cutting duplicate charges from ~20/week to zero (Python, PostgreSQL).` |
| `Helped improve search performance.` | 弱化語、沒有數字 | `Rewrote the product-search query path with a covering index and result caching, cutting p95 latency from 1.2 s to 300 ms.` |
| `Participated in planning; sometimes ran it.` | 被動、含糊修飾 | `Ran sprint planning for a 6-person team for two quarters; introduced estimate reviews that cut carry-over work from ~30% to ~10%.` |
| `We built a tool used by other teams.` | 「我們」、沒有規模 | `Built an internal feature-flag dashboard (React, Flask) adopted by 5 product teams, replacing manual config edits.` |
| `Responsible for customer tickets.` | 職責清單 | `Diagnosed root causes for [N]+ customer tickets on data mismatches; [N] traced to platform bugs and fixed by engineering.` |
| `Side project: URL shortener.` | 看不出難度 | `URL shortener in Go with a Redis token-bucket rate limiter; load-tested to 2k RPS on a single small VM; 90% test coverage. [GitHub]` |

## 動詞

動詞只是開頭，具體細節才是重點；不要為了華麗動詞犧牲精確。

- 建造：Built, Designed, Implemented, Shipped, Launched, Migrated, Automated
- 改善：Reduced, Cut, Improved, Raised, Accelerated, Simplified
- 主導：Led, Owned, Drove, Initiated, Proposed
- 分析：Diagnosed, Benchmarked, Evaluated, Profiled（後面要接結論或結果）
- 人：Mentored, Onboarded, Taught, Organized

少用：Helped, Assisted, Participated, Supported, Was responsible for, Worked on, Tried。
`Investigated`、`Analyzed` 單獨出現只代表「看過」，要接上找到什麼、改了什麼。

## 長度與數量

- 每條 1–2 行；每職位 3–5 條；最近的職位最詳細
- 一條只講一件事；兩件事就拆開
- 目標是每條至少一個數字——多數履歷沒有數字，有就會突出

## Side project、開源、社群

- 一樣套成果公式：為什麼有趣或困難、規模、使用者、測試、結果
- 附可點的 repo 或 demo；README 要說清楚是什麼、怎麼跑、怎麼測
- 已部署且有真實使用者 > 只在本機跑；有付費或真實客戶更好
- 有自動化測試就寫出來（測試數、覆蓋率）——學生和轉職者很少有
- 開源：寫被合併的貢獻與專案規模
- 社群或志工：寫你做了什麼、產生什麼結果（規模、場次），刪掉只是名目的合作關係

## 縮寫

- 業界通用縮寫直接用（API、RAG、LLM、CI/CD、MVP 等，依 JD 的寫法）。它們也是 recruiter 搜尋的關鍵字；展開成全名既佔空間，也可能對不到關鍵字。
- 自創或冷門的指標，第一次出現時展開，例如 `Percentage of Correct Events (PCE)`。
