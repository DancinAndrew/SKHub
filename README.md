# SKHub

我自己的 Claude Code skills 存放處。換電腦時 clone 下來、跑一次 `install.sh`，就能把全部 skill 裝回 `~/.claude/skills/`。

## Skills

| Skill | 用途 | 來源 |
| --- | --- | --- |
| [tech-resume](skills/tech-resume/SKILL.md) | 技術履歷健檢、改寫 bullet、針對 JD 客製化、研究所申請 CV，以及 LinkedIn／GitHub／cover letter | 由 Gergely Orosz《The Tech Resume Inside Out》（ByteByteGo 課程版）歸納的原則，非原書內容；研究所 CV 部分整理自加拿大學程官方頁 |
| [media-note](skills/media-note/SKILL.md) | YouTube、podcast、課程錄音＋投影片 PDF → 附圖表與投影片頁的繁中 Obsidian 筆記；Claude Code 與 Codex 共用 | 自製。需要 Apple Silicon macOS、`uv`、ffmpeg、poppler；YouTube 另需 node、deno 或 bun 其一 |
| [note-prose-cleanup](skills/note-prose-cleanup/SKILL.md) | 修順既有筆記，清除重複聲明、整理過程與生硬句法，保留例子、來源與必要限制 | 自製；依句子用途判斷，不以關鍵字批次刪除 |

## 安裝（新電腦）

```bash
git clone https://github.com/DancinAndrew/SKHub.git ~/Documents/SKHub
```

```bash
~/Documents/SKHub/install.sh
```

`install.sh` 會把 `skills/` 底下每個資料夾以 symlink 連到 `~/.claude/skills/`（Claude Code）和 `~/.agents/skills/`（Codex 等其他 agent）：

- 已經是 symlink → 更新指向
- 已有同名的實體資料夾 → 跳過並提示，不覆蓋（先把它移走再重跑）
- 要裝到別的位置：`SKILL_TARGET_DIRS=/path/a:/path/b ./install.sh`

`media-note/config/vaults.json` 記的是我自己的 Obsidian vault 位置（`~/Documents/...`）；新電腦的 vault 路徑不同時，改這個檔或用環境變數 `MEDIANOTE_VAULTS` 指向另一份設定。

因為是 symlink，之後 `git pull` 就會直接更新已安裝的 skill。

## 新增一個 skill

1. 在 `skills/<skill-name>/` 放 `SKILL.md`（frontmatter 至少要有 `name`、`description`），其他參考資料放 `references/`。
2. 跑一次 `./install.sh`。
3. 在上方表格補一行，commit、push。

## 公開前檢查

這個 repo 是公開的。不要放：履歷本身、電話與住址、API key、私人日記或從私人筆記萃取的內容、付費書籍或課程的原文。
