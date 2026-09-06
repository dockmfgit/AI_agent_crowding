# GitHub 非公開リポジトリ作成記録

日付: 2026-08-29。指示書: `repo_prep/github_publish_instructions.md` v1.3。

## リポジトリ

- URL: **https://github.com/dockmfgit/AI_agent_crowding**（**private** — gh API で
  `isPrivate: true` を確認済み）
- ブランチ: main、コミット: `af7501a59c65708adb3785771739e6ecdc06e568`
- Author/Committer: `Makoto Fukushima <dockmfgit@users.noreply.github.com>`
  （`git log --format=full -1` で確認。Co-Authored-By 等のトレーラなし）
- 追跡ファイル数: 239

## 含めたもの / 除外したもの

| パス | サイズ | 備考 |
|---|---|---|
| scripts/ | ~1 MB | `__pycache__/*.pyc` 9 件を含む（repo_prep の .gitignore に
__pycache__ 指定がないため組み立てツリーどおり収載。改変禁止規則に従い据え置き）|
| results/ | <1 MB | 全 CSV |
| notes/ | <1 MB | 00–16, 19, 指示書群 |
| manuscript/ | ~3 MB | tex/（LaTeX 中間物は .gitignore で除外）、main.pdf, si.pdf |
| fig/ | ~5 MB | |
| data/stage1/ | 28 MB | 生 JSONL 込み |
| data/stage2_episodes.tar.gz | 83 MB | 全エピソード JSON の tar.gz（<90 MB）|
| data/（その他）| <1 MB | stage2/2b/2c/2d の小物、parquet |
| **除外** | | external/（El et al. データ、再配布せず）、`*_ollama_serve.log`
（20.8 GB）、scratch/、data/stage2/episodes/（tar.gz で代替）、AppleDouble |

総サイズ: 117 MB（目安 100–150 MB 内）。

## 公開前チェック（4 項目、実行日 2026-08-29）

1. `find $DST -size +90M` → **空**（最大は tar.gz の 83 MB）✓
2. `$DST/external` 不在 ✓ / `data/*serve*` 不在 ✓
3. トークン様文字列（ghp／api key／Authorization ヘッダの各パターン）grep → **ヒットなし** ✓
4. du -sh → 117 MB ✓

## 経緯メモ

- `gh` CLI 未導入だったため公式バイナリ v2.98.0 (linux_arm64) を `~/.local/bin` に導入。
- ユーザ認証は細粒度 PAT。作成権限がなかったため、指示書のフォールバックどおり
  ユーザが GitHub 上で空 private リポジトリを作成 → トークンに Contents: Read and
  write を付与 → push。トークンはファイル・履歴に一切記録していない。
- push 時の GH001（Large files 警告）は 83 MB の tar.gz に対する LFS 推奨のみで、
  100 MB 制限内のため対応不要。
- 公開（public 化）は arXiv 投稿時にユーザが手動で行う。本作業では private のまま。

## 更新 2026-09-04

指示書: `repo_prep/github_update_instructions.md` v1.0。

- 新コミット: `1c2e14b28b66a5aadfe2e1b8780041395cae6445`（af7501a → 1c2e14b、
  fast-forward push、force なし）。Author/Committer は本人名義・トレーラなし（確認済み）。
- 変更規模: 23 ファイル（+824 / −298 行）。主な内容: 新 Fig 3（fig3_neuron
  PDF/PNG + panel_a）、`scripts/41_neuron_io_fig.py` 追加、fig1/fig6 更新、
  main.tex / si.tex / refs.bib / main.pdf / si.pdf 更新、
  `manuscript/overleaf_upload.zip` 追加、notes/15 更新、notes/19 収載、README 更新。
- `data/stage2_episodes.tar.gz` は**再作成せず**（8/29 以降の新規エピソード 0 件、
  mtime 不変を確認）。
- 公開前チェック: >90M なし ✓ / external 不在 ✓ / serve ログ不在 ✓ /
  トークン様文字列 grep → 初回は notes/19 の記録文（grep パターン自体の逐語）に
  偽陽性 1 件 → SRC 側の表記を無害化して再同期後 **ヒットなし** ✓。
- du -sh: 217 MB（うち .git 約 94 MB。作業ツリーは約 123 MB）。
- 逸脱の記録: NAS の SMB 削除プレースホルダ `.smbdelete*` 20 件が rsync で混入
  したため、.gitignore の「NAS artifacts」区分と同種のゴミとして公開ツリーから
  削除した（初回コミットに混入していた 1 件も本コミットで削除）。
- 追補 v1.1（2026-09-04）: `45c9bb6dcb44da9d7ee827374a7b4f1917815bd0` —
  manuscript/overleaf_upload.zip を削除（NAS 側削除の同期）。同コミットに
  NAS 側更新 3 件（cover_letter_pnasnexus.md、notes/15、notes/19 の §更新記録）を同梱。
  チェック 4 項目すべて合格、tar.gz 再作成なし、fast-forward push。
