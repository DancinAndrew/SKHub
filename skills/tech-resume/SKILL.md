---
name: tech-resume
description: Review, rewrite and tailor software / AI / data / solution-engineering resumes with hiring-manager principles — 6-second scan, impact bullets, one version per job description, no ATS myths. Also covers LinkedIn, GitHub profile and cover letters for job hunting. Use when the user says "看我的履歷", "履歷健檢", "幫我改履歷", "改 bullet", "針對這個 JD 改履歷", "review my resume", "tailor my resume", "rewrite these bullets", or hands over a resume PDF/text, a job description, or a cover-letter draft.
origin: personal — principles paraphrased and condensed from Gergely Orosz, "The Tech Resume Inside Out" (ByteByteGo course edition). Not a copy of the book.
---

# /tech-resume — 技術履歷健檢、改寫與客製化

履歷只有一個目的：讓對的人願意約你面試。它不是完整的工作紀錄。
所有建議都用同一把尺量：**這個改動有沒有讓不認識你、手上有上百份履歷的 recruiter 或 hiring manager，在幾秒內更確定你適合「這個」職位？**

## 鐵律（所有模式都適用）

1. **不捏造。** 沒有的數字、經歷、技術一律用 `[N]`、`[metric]` 佔位，並列進「需要你補的資料」。估算可以，但要標成估算，且面試時說得出怎麼算的。
2. **證據導向。** 每條意見都要引用履歷原文（或指出缺了什麼）→ 說明原則 → 給具體改法或改寫範例。不寫「可以更好」這種空話。
3. **事實一致。** 不同版本可以強調不同面向，但日期、職稱、數字不得互相矛盾——同一個人的多份履歷常在公司內被對照。
4. **在地慣例要確認。** 這套原則以英語為工作語言的科技公司為基準。照片、口說語言、長度等在其他市場可能不同；遇到時標註「依目標公司或地區確認」，不要硬套。
5. **不為挑而挑。** 風格偏好、可接受的寫法，直接說「這條可以不改」。

## 開始前先確認

缺了就問；低風險時可明示假設後繼續。

- 目標職類（例：SE/FDE、Backend、AI/ML、Data）與年資級別
- 有沒有具體 JD：有 → 模式 B；沒有 → 模式 A 並建議分版本
- 目標市場與公司類型：大型科技 generalist／特定技術棧公司／顧問或外包／小新創
- 用途是求職還是升學（升學履歷慣例不同：教育在前、GPA、研究經歷）

## 模式 A：健檢（Review）

1. **6 秒掃描**：模擬第一眼，只檢查五件事能不能立刻找到——
   年資（從畢業日期與工作日期推算）、相關技術、職稱與公司、所在地與工作許可、最亮的一個訊號（獎項、知名公司、開源核心貢獻、專利等）。
2. **逐項對照** [references/checklist.md](references/checklist.md)：基本規則 → 結構 → bullet → 技能 → 格式 → 連結 → 不必要內容 → 定位。
3. **能驗證的就實際驗證**：連結是否可點、是否回應正常；GitHub 是否有 profile README、置頂專案、專案說明與 README。不要只看文字推測。
4. **依下方格式輸出報告。**

## 模式 B：針對 JD 客製化（Tailor）

依 [references/tailoring.md](references/tailoring.md)：讀懂招募動機 → 抽關鍵字 → 建證據對照表 → 決定段落順序與保留哪些 bullet → 用 JD 的詞改寫**既有事實** → 列出「JD 要但你沒有證據」的缺口（不要硬塞）。

## 模式 C：寫或改 bullet（Write）

依 [references/bullets.md](references/bullets.md)：先把做過的事全部倒出來 → 挖數字（問同事主管、合理估算）→ 套公式 → 每職位刪到 3–5 條、每條不超過 2 行。

## 模式 D：履歷以外

LinkedIn、GitHub、技術文章、cover letter、回饋與打磨：[references/beyond-resume.md](references/beyond-resume.md)。

## 結構與段落順序

依年資與職涯路徑（學生、有經驗、senior、tech lead、EM、轉職、空窗）：[references/structure-by-level.md](references/structure-by-level.md)。

## 健檢報告格式

```markdown
## 結論
一兩句：目前的水準、最大的一個落差。

## 6 秒掃描
| 掃描項 | 找得到嗎 | 備註 |

## 做得好的（保留）
- …

## 優先修正
- P0：不改會直接影響能不能被約面試
- P1：明顯加分
- P2：細節
每條：**問題** — 原文引用 → 原則 → 建議改法（含改寫範例；未知數字用 [N]）

## 需要你補的資料
- 例：這段實習處理過幾張 ticket？

## 關鍵假設
- 我假設 X；若不對，結論會變成 Y。（最多三條）
```

改寫範例只示範句型與結構；正式版本中的每個數字都必須由使用者確認。

## 不要做的事

- 不推薦付費的「ATS 優化」服務，也不拿「多數履歷被機器刷掉」這類說法嚇人（事實見 tailoring.md）。
- 不建議加自評星等或百分比、照片、生日、婚姻狀態、推薦人清單（在地慣例另議）。
- 不為了填滿版面加無關內容，不為了顯得完整列出所有用過的工具。
- 不把字縮小、把間距擠掉來塞進一頁；寧可刪內容或改用兩頁。
