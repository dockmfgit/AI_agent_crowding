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

## 再作成 2026-09-06(投稿版)

指示書: `repo_prep/github_refresh_instructions.md` v2.0。ユーザが旧リポジトリを退避し
空の private リポジトリを再作成済み(isEmpty: true, isPrivate: true を確認してから実行)。

- 新コミット: **`c576a639d901f1f5524c9e6d10225b1bd0906599`**(単一コミット、
  fast-forward 相当の新規 push、force なし)。Author/Committer 本人名義・トレーラなし。
- 公開ツリー: `../AI_agent_crowding_publish_v2`(旧ツリーは tar.gz 再利用元として保持)。
  追跡ファイル数 **266**、総サイズ **120 MB**。
- 除外(指示書 §1 の理由どおり): cover letter・推薦査読者リスト・所属ロゴ(投稿事務用)、
  外部レビュー文書と再解析指示書(作業文書)、notes/20(別論文の私的メモ)、
  01_draft.md(tex に置換済みの旧鏡像)、__pycache__(.gitignore にも追記)、
  .smbdelete*、LaTeX 中間物。
- 図の整理: fig3_single_agent.{pdf,png} を削除(旧 SI Fig. S1。png は指示書に明記が
  ないが同一理由で削除と判断・記録)、fig1_framework.png / fig3_neuron.png /
  fig6_generality.png を削除(PDF の重複)。**fig3_panel_a.png は scripts/41 の入力
  (著者作画、mpimg.imread で読み込み)と確認し保持**。tables/ は 22 個を確認。
- tar.gz: episodes 2,633 件・8/29 以降の更新 0 を確認し、旧ツリーからコピーで**再利用**
  (再圧縮なし)。
- MANIFEST: `data/MANIFEST.md` が無かったため新規作成(67 ファイルの相対パス・バイト数・
  SHA-256 と tar.gz の展開説明)。
- チェック: >90M なし / external 不在 / serve ログなし / トークン様文字列なし /
  投稿事務ファイルなし / __pycache__ なし / scripts 50–57 + hmf_lib 9 本 /
  results r1・r23・r34・r4・r5・r6・r8 揃い / main.pdf 20 頁 / si.pdf 12 頁 /
  "Claim-induced fields" が README と main.tex に各 1 — **全項目合格**。

## 更新 2026-09-06(第 2 コミット)

指示書: `repo_prep/github_update_v21.md`。

- コミット: **`a1c0ec2dee5c2a13874fc5a82b72758bfa50dd1e`**(c576a63 → a1c0ec2、
  fast-forward、force なし、本人名義・トレーラなし)。
- 変更: **7 ファイル(+161 / −33 行)** — README.md、manuscript/tex/{main.tex, si.tex,
  main.pdf, si.pdf}、notes/{15, 19} — §2 の想定リストと完全一致。
- チェック: 新タイトル句 "Message capacity and claim wording" が README・main.tex・
  si.tex に各 1 ✓ / "claim-induced" 残存なし ✓ / "Use of generative AI" 1 ✓ /
  main.pdf 21 頁・si.pdf 12 頁 ✓ / 投稿フォルダ submission_pnasnexus_20260906 は
  rsync 除外を追加し混入なし ✓ / トークン様文字列なし ✓。
- 復活ファイルの除去: --delete なし rsync により v2.0 で削除済みの 5 図ファイル
  (fig3_single_agent.{pdf,png}、fig1_framework.png、fig3_neuron.png、
  fig6_generality.png)が作業ツリーに復活したため削除し、コミット状態を復元。
- 記録(齟齬): §2 の図チェックの期待「fig3_panel_a.png のみ」は、c576a63 で意図的に
  保持された fig2/fig4/fig5/fig7/figS1 の PNG(追跡済み)と矛盾する。追跡済み PNG の
  削除は本指示の範囲外(内容変更)と判断し、v2.0 の削除リスト 5 件の復活除去のみ実施。
