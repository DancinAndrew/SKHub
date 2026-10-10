# SKHub

我自己的 Claude Code skills 存放處。換電腦時 clone 下來、跑一次 `install.sh`，就能把全部 skill 裝回 `~/.claude/skills/`。

## Skills

| Skill | 用途 | 來源 |
| --- | --- | --- |
| [tech-resume](skills/tech-resume/SKILL.md) | 技術履歷健檢、改寫 bullet、針對 JD 客製化，以及 LinkedIn／GitHub／cover letter | 由 Gergely Orosz《The Tech Resume Inside Out》（ByteByteGo 課程版）歸納的原則，非原書內容 |

## 安裝（新電腦）

```bash
git clone https://github.com/DancinAndrew/SKHub.git ~/Documents/SKHub
```

```bash
~/Documents/SKHub/install.sh
```

`install.sh` 會把 `skills/` 底下每個資料夾以 symlink 連到 `~/.claude/skills/`：

- 已經是 symlink → 更新指向
- 已有同名的實體資料夾 → 跳過並提示，不覆蓋
- 要裝到別的位置：`CLAUDE_SKILLS_DIR=/path/to/skills ./install.sh`

因為是 symlink，之後 `git pull` 就會直接更新已安裝的 skill。

## 新增一個 skill

1. 在 `skills/<skill-name>/` 放 `SKILL.md`（frontmatter 至少要有 `name`、`description`），其他參考資料放 `references/`。
2. 跑一次 `./install.sh`。
3. 在上方表格補一行，commit、push。

## 公開前檢查

這個 repo 是公開的。不要放：履歷本身、電話與住址、API key、私人日記或從私人筆記萃取的內容、付費書籍或課程的原文。
