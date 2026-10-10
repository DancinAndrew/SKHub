---
name: media-note
description: >-
  Turn a YouTube video, a podcast episode (Spotify, Apple Podcasts, SoundOn, RSS, audio URL) or lecture
  recordings with optional slide PDFs into a Traditional Chinese Obsidian study note: fetch uploaded subtitles or
  transcribe locally with Whisper, capture chart/animation frames, and embed the matching slide pages. Use when the
  user shares such a link or files and asks to 做筆記、轉成筆記、整理成筆記、課程筆記、逐字稿轉筆記, make notes,
  or transcribe for notes. Replaces obsidian-course-note and spotify-podcast-course-note.
metadata:
  version: "3.0.0"
---

# media-note

版本 3.0.0：影音閱讀筆記預設使用完整白話推理的文章格式；課程與舊版時間軸仍相容。

影音來源 → 逐字稿（上傳字幕或本機 Whisper）→ 需要時截影片圖表或嵌投影片頁 → 繁中 Obsidian 筆記。
下載、轉錄、抽圖、PDF、對頁、路徑、驗收全部走同一支 driver，Codex 與 Claude Code 共用：

```bash
uv run ~/.agents/skills/media-note/scripts/medianote.py vaults
```

每個指令在 stdout 最後一行印一個 JSON（`ok`、產出路徑、`work_dir`），進度訊息在 stderr。下文的 `MN` 是 `uv run ~/.agents/skills/media-note/scripts/medianote.py` 的簡寫。快取在 `~/.cache/media-note/<來源>/`，重跑直接用快取。

寫筆記前先讀 [references/note-format.md](references/note-format.md) 與 [references/research-policy.md](references/research-policy.md)。

> [!important] 在 Codex 裡執行
> Codex 預設沙箱會讓**每個** driver 指令失敗：`Failed to initialize cache at ~/.cache/uv`（uv 寫不進快取）。
> 開了網路並允許寫入 `~/.cache` 與 vault 後，下載、字幕、抽圖、PDF、驗收都能在沙箱內跑，但**本機轉錄一定要在沙箱外**：沙箱擋住 Apple GPU，會回 `mlx-whisper cannot reach the Apple GPU (Metal)`。遇到這兩個錯誤就用提升權限重跑，不要改用別的方法繞過。

## 1. 判斷路線，開始前一次問清楚

| 使用者給的 | 路線 |
| --- | --- |
| YouTube 連結 | A |
| Spotify／Apple Podcasts／SoundOn 單集連結、RSS、音檔網址 | B |
| 本機錄音或影片檔（可能附 PDF 講義） | C |

先跑 `probe` 拿標題、長度、字幕狀態；既有對話已確認圖表與目的地就沿用，只有缺資訊時一次問清楚（Claude 用 AskUserQuestion）：

1. **A 路線必問**：影片有沒有動畫、圖表、投影片要截圖進筆記？依 probe 給建議（直播、訪談、podcast 通常沒有；小Lin说 這類解說影片有）。
2. **存放位置**：依 `vaults` 的 `use_for` 提議 vault 與資料夾，請使用者確認。
3. **C 路線**：錄音檔與 PDF 的順序對不對。

```bash
uv run ~/.agents/skills/media-note/scripts/medianote.py probe "https://www.youtube.com/watch?v=GkUnfbPyXVA"
```

`transcript_plan` 是 `youtube-subs:<語言>` 代表有同語言的上傳字幕；`asr` 代表要本機轉錄，`asr_estimate` 是預估時間。

## 2. 取得素材

### A. YouTube

```bash
uv run ~/.agents/skills/media-note/scripts/medianote.py transcript "https://www.youtube.com/watch?v=GkUnfbPyXVA"
uv run ~/.agents/skills/media-note/scripts/medianote.py transcript "https://www.youtube.com/watch?v=YC7HD_-k4TI" --force-asr
```

有同語言的上傳字幕就用字幕，否則下載音訊跑 Whisper；YouTube 自動字幕一律不用。`--force-asr` 在字幕品質很差時使用。`transcript.md` 每次執行都會覆寫：用 `--force-asr` 測試後要改回字幕版，就不帶旗標再跑一次。

使用者說有圖表時抽候選畫面（下載 720p 純影像）：

```bash
uv run ~/.agents/skills/media-note/scripts/medianote.py frames "https://www.youtube.com/watch?v=8BN8p5xDkzw"
```

打開輸出的每張 `sheets` 圖片：每格標 `#編號 時間`，底部是影片燒進去的字幕。`recurring_sheets` 是被排除的重複畫面（主持人鏡頭），確認沒有誤刪重要圖表。

### B. Podcast

```bash
uv run ~/.agents/skills/media-note/scripts/medianote.py probe "https://open.spotify.com/episode/1CNZv0gXOQesAJmCTWTTWx"
uv run ~/.agents/skills/media-note/scripts/medianote.py transcript "https://open.spotify.com/episode/1CNZv0gXOQesAJmCTWTTWx"
```

Spotify 只讀頁面上的單集標題與節目名，再到該節目的公開 RSS 找同名單集的音檔；找不到就請使用者給 RSS 或 Apple 連結，不繞過 DRM 或付費牆。RSS 網址要指定單集：

```bash
uv run ~/.agents/skills/media-note/scripts/medianote.py probe "https://feeds.soundon.fm/podcasts/954689a5-3096-43a4-a80b-7810b219cef3.xml" --episode-index 1
```

### C. 課程錄音＋PDF（ML Week2 實測指令）

錄音檔按播放順序給；時間軸是各段累計時間，逐字稿會標出每段錄音的起點。

```bash
uv run ~/.agents/skills/media-note/scripts/medianote.py pdf "Week2/1.Introduction-to-AI.pdf" "Week2/2.Introduction-to-ML.pdf"
uv run ~/.agents/skills/media-note/scripts/medianote.py transcript "Week2/recordings/lecture-part1.m4a" "Week2/recordings/lecture-part2.m4a" "Week2/recordings/lecture-part3.m4a" --title "機器學習 Week2：Introduction to AI & ML" --terms-from "Week2/1.Introduction-to-AI.pdf" "Week2/2.Introduction-to-ML.pdf"
uv run ~/.agents/skills/media-note/scripts/medianote.py align --work "<transcript 輸出的 work_dir>" --pdf "Week2/1.Introduction-to-AI.pdf" "Week2/2.Introduction-to-ML.pdf"
```

`--work` 用 `transcript` 輸出的 `work_dir`。`align` 產生 `align/alignment.md`：每分鐘對到哪一頁（D1＝第一份 PDF）與分數。它只是候選，**一定要**對照 `pdf` 輸出的縮圖 sheet 和逐字稿確認；分數 < 0.08 的段落靠縮圖判斷，整段都沒有對應頁時，多半是講義沒給齊，要在筆記註明。

耗時（Apple M5 實測，whisper-large-v3-turbo）：每小時音訊約 3 分鐘（98 分鐘英文課 3.8 分鐘、70 分鐘中文 podcast 3.1 分鐘），外加 YouTube 下載約 1.5 MiB/s。能背景執行就背景執行。

## 3. 寫筆記

1. 讀完整份 `transcript.md`（長的分段讀）；`transcript.json` 的 `quality` 看可疑比例與缺漏區間。
2. 取得輸出路徑（會拒絕覆蓋既有檔案）：

   ```bash
   uv run ~/.agents/skills/media-note/scripts/medianote.py paths --vault Engineering --title "機器學習 Week2：Introduction to AI & ML"
   ```

3. 按 note-format 的語意章節寫完整閱讀文章，保留主要說話順序與必要推理；全篇來源 coverage 留工作區。課程學習格式另依 course-format，不批次改無生成證據的課程。
4. 圖片：
   - A：挑能支撐各段解釋的原圖候選（總覽圖不能取代原圖），依筆記順序匯出，貼上輸出的 `embed`：

     ```bash
     uv run ~/.agents/skills/media-note/scripts/medianote.py export-frames --work "$HOME/.cache/media-note/yt-8BN8p5xDkzw" --pick 1,9,20,28,38,46,52,61,74,83,99 --dest "<paths 輸出的 attachments_dir>"
     ```

   - C：確認過的對應頁匯出成圖片（預設 JPEG，比 PNG 小 2–4 倍；要 PNG 加 `--format png`），貼上 `embed`：

     ```bash
     uv run ~/.agents/skills/media-note/scripts/medianote.py export-pages --pdf "Week2/2.Introduction-to-ML.pdf" --pages 4,8,13,19,23,26,29,35,40,45,46,48,50,53 --dest "<paths 輸出的 attachments_dir>"
     ```

5. **逐字稿不寫進 vault。** 它只是中間產物，留在 `<work_dir>/transcript.md`；完成來源覆蓋、查證、發布讀回與收據後才清理本次獨占的中間素材；保留工作區的來源讀取證據與雜湊以供授權修訂，不刪其他 worker 正在用的共用快取。筆記裡不要放逐字稿連結，也不要加「與既有筆記的連結」那一節。
6. 依 research-policy 查證會過期的事實。一定要打開原文核對，不能只看搜尋摘要；一般 JavaScript 頁面可用許可的瀏覽器工具；遇到明確存取拒絕、付費牆或授權限制就停止該取得途徑，找合法公開一手來源或標限制，不換工具繞過。講時事的 podcast，這一步通常最花時間。
7. 寫到 `paths` 的 `note`，執行結構檢查（reading-v3 可加 `--coverage WORK/coverage.json`），逐項處理錯誤與解釋警告，再依 note-format 完成人工來源與語意核對；`ok: true` 不是內容已驗證：

   ```bash
   uv run ~/.agents/skills/media-note/scripts/medianote.py check "<paths 輸出的 note>"
   ```

8. 回報：筆記路徑、逐字稿來源（字幕或 ASR）、嵌入幾張圖／頁、可信度問題、講者說法和一手資料不一致的地方。

vault 一般寫入規則看 `vaults` 與 AGENTS：預設只新增，Business&Finance 原文凍結、清冊不動。使用者明確授權改既存 skill 生成筆記時，先以 source ID／生成紀錄列遷移 manifest，備份與前置 hash，保留身分、路徑、人改、原圖與連結，發布後讀回；未知生成來源或缺完整素材的篇目不要猜改。各來源只由指定協調者發布，同時寫入即停止。技術進度與備份留既有工作區，不散布到讀者目錄；排程需另外授權。

## Gotchas

- **不要從來源推測語言。** 中文授課環境的 ML 課也可能整堂講英文；強制用中文轉錄會得到亂碼，還因為一直重試解碼而慢 4 倍。driver 每 30 秒偵測一次語言；只有確定時才加 `--language zh|en`。
- **Whisper 提示詞只影響第一個 30 秒窗口**（mlx-whisper 0.4.3 在關閉「參考前文」的防幻覺設定下無法延續提示），所以專有名詞常錯：「股癌／謝孟恭」→「古埃／聖夢恭」、Yann LeCun →「Yang Li Kun」。用 probe metadata 與 PDF 術語校正，沒有依據的名字不要猜；課程筆記要附一張「聽成 → 實際」對照表。
- **字幕可能晚幾小時才上傳。** M觀點 EP336 上傳隔天就有 `zh-TW` 字幕；剛上架的影片 probe 說要 ASR 時，可以問使用者要不要等。
- **yt-dlp 需要 JavaScript 執行環境**解 YouTube 的驗證；driver 自動帶 `--js-runtimes node`，沒有 node/deno 時格式和字幕會默默消失。yt-dlp 每次都跑 `@latest`。
- **快節奏解說影片不能用換場偵測**：小Lin说 平均 2 秒一切。driver 改找「連續 ≥2 秒幾乎不動」的畫面、取最後一張（動畫畫完的狀態）、剔除反覆出現的主持人鏡頭；16 分鐘影片約 116 張候選，最後用了 11 張。畫面底部 18% 的燒入字幕不計入差異。
- **簡體字幕自動轉台灣繁體**（OpenCC s2twp），但譯名不會變（特朗普、日元）；筆記正文自己改成台灣譯名。
- **PDF 頁碼用 PDF 第幾頁**（`p.N`），投影片上印的頁碼常差 1。
- 課堂錄音常在開課後才開始錄、下課休息時暫停：ML Week2 從第一份講義 p.4 開始，最後 14 分鐘講迴歸時兩份講義都沒有對應頁。
- 主持人講的數字和日期常和一手來源有出入（例：OpenAI 發表日 9/8 被說成 9/9；OpenAI 對「有沒有用到使用者資料」的回應比轉述保留）。差異寫進 `> [!research]-`，不要默默改掉講者說法。
- 可調的環境變數：`MEDIANOTE_CACHE`（快取位置）、`MEDIANOTE_ASR_MODEL`（轉錄模型）、`MEDIANOTE_VAULTS`（vault 設定檔）、`MEDIANOTE_YTDLP_ARGS`（額外 yt-dlp 參數）。

## Troubleshooting

| 症狀 | 處理 |
| --- | --- |
| `Failed to initialize cache at ~/.cache/uv` | 在 Codex 沙箱內：用提升權限重跑 |
| `mlx-whisper cannot reach the Apple GPU (Metal)` | 轉錄必須在沙箱外執行：用提升權限重跑 |
| `YouTube asked to sign in to confirm you're not a bot` | 稍後重試；使用者明確同意後才設 `MEDIANOTE_YTDLP_ARGS='--cookies-from-browser chrome'`（會讀瀏覽器 cookie） |
| `WARNING: no node/deno/bun on PATH` | 先用已安裝的 node／deno；缺少就回報，安裝另依使用者授權 |
| `No public audio found for …`（Spotify 獨家節目） | 請使用者提供 RSS／Apple 連結；沒有公開音檔就停止 |
| 逐字稿前幾分鐘是亂碼或語言不對 | 看輸出的 `language_runs`，用 `--language en` 或 `--language zh` 重跑 |
| `Output already exists` / `Refusing to overwrite` | 新建換標題或資料夾；已授權遷移用備份及前置 hash 保護，勿刪原檔迴避碰撞 |
| `check`：`wikilink target not found` | 刪掉捏造的連結，或改連真的存在的筆記 |
| `check`：`gap after previous section` | 補上缺的時間段（業配也要一行） |
| `check` warnings：`check first-use explanations for: …` | 在該縮寫第一次出現的句子就地加括號說明 |

## 測試

```bash
cd ~/.agents/skills/media-note/scripts && uv run --python 3.12 --with pytest --with numpy --with pillow --with opencc-python-reimplemented pytest tests -q -p no:cacheprovider
```

需要 ffmpeg 與 poppler；不需要網路與 GPU（網路和轉錄以假資料替換，媒體以 ffmpeg／Pillow 合成）。測試包括舊格式相容性與 reading-v3 的來源身分、回聽及附件檢查；實際數量以執行結果為準。
