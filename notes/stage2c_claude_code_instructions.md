# Stage 2c 指示書(GX10 / Claude Code 用)v1.0

作成: 2026-08-27。三部構成。Part 0 は原稿の機械的修正(ユーザ承認済み)、
Part A は極性チャネルの由来試験(D-3、単発のみ・集団なし)、Part B は qwen3:8b
閾値予測の系統較正(原稿の主見出し主張の強化)。**Part A と B は独立に実行可能。
A を先に(数時間で終わる)、B を後に(約 8–12 h)。**

読む順: この指示書全文 → `notes/13_stage2b_results.md` §7(D-1/D-2 の設計)→
`notes/05_stage1_results.md` §4(極性診断回帰の定義)→ `notes/15_manuscript_build.md`。

共通規約(全 Stage と同一): 温度 0.7、全呼び出しの seed・プロンプトハッシュ・
生応答・パース結果を JSONL に記録。既存 `results/` は変更しない(新規ファイルのみ
追加)。`external/` 変更禁止。科学的数値の改変禁止(Part 0 の 4 件を除く)。

---

## Part 0: 原稿の機械的修正(4 件 — notes/15 §4 の不一致の裁定結果)

`manuscript/01_draft.md` と `manuscript/tex/main.tex` の**両方**に適用し、
pdflatex+bibtex で `main.pdf` を再ビルド、`notes/15_manuscript_build.md` 末尾に
「修正記録(Stage 2c Part 0)」として追記する。si.tex に該当箇所はない(要確認)。

| # | 場所 | 現行(exact string) | 修正後 |
|---|---|---|---|
| F-1 | §1 | `describes 9{,}600 such communities` | `describes more than 10{,}000 such communities`(El et al. abstract の表現に整合。再解析対象の 6,400(客観)は §3 で既に正記) |
| F-2 | §3 | `(four models, 40 questions, 12 graphs, four episodes)` | `(four models, 40 questions, ten graphs per question, four episodes)`(4×40×10×4 = 6,400) |
| F-3 | §4 | `8-bit-quantized` | `4-bit-quantized (Q4\_K\_M)`(01_draft.md 側は `4-bit-quantized (Q4_K_M)`) |
| F-4 | §5.2 | `toward 0.16 ($\alpha = 1.3$)` | `to 0.078 ($\alpha = 1.0$)`(出典: notes/12 §3。0.16 は出典なしと判明) |

F-4 の前後文はそのまま(「rising from $x^* = 0.011$ ($\alpha = 0.2$)」は不変)。
4 件とも文字列置換のみ。他の文言・数値には触れない。

---

## Part A: D-3 — 極性チャネルの由来(llama3.1:8b 系 3 変種、単発のみ)

### A-0. 目的と凍結予測(この指示書のコミットをもって凍結とする)

§5.3 の確定事実「llama3.1:8b の集団は主張の肯定側に従う(単発の極性比 1.44)」に
対し、想定される査読反論は「それは RLHF/instruction tuning が作る同調・肯定
バイアス(sycophancy)ではないか」。本試験はこの極性チャネルの**由来段階**を
単発測定だけで切り分ける。集団は走らせない。

| 変種 | H-tuning(チューニング由来)の予測 | H-pretraining(事前学習由来)の予測 |
|---|---|---|
| instruct(現行 llama3.1:8b、陽性対照) | 極性比 ≈ 1.44(再測定で 1.3–1.6) | 同左 |
| base(llama3.1:8b-text) | **≈ 1.0(95% CI が 1 を含む)** | ≥ 1.3 |
| abliterated(instruct 系・拒否方向除去) | 下位仮説 H-align(安全アラインメント由来): < 1.2 に低下 / 下位仮説 H-instr(指示追従一般由来): ≈ 1.4 を保持 | ≈ 1.4 |

判定規則(事前固定): クレームクラスタ bootstrap 95% CI で、(i) base の比の CI が
1 を含み instruct の CI と非重複 → 「consistent with tuning-stage origin」、
(ii) base が instruct と同水準 → 「consistent with pretraining origin」、
(iii) abliterated の位置で H-align / H-instr を区別。**因果語は使わない**
(abliteration は拒否方向の除去であり prosociality の外科的除去ではない —
報告にこの限界を必ず一文入れる)。

### A-1. モデルの入手と同定

- base: `llama3.1:8b-text-q4_K_M`(ollama 公式タグ)。
- abliterated: 第一候補 `mannix/llama3.1-8b-abliterated`(Q4 系タグを選ぶ)。
  なければ ollama レジストリで「llama3.1 8b abliterated / uncensored」を検索し、
  **llama3.1-8b-instruct 派生であること**(3.2 や base 派生は不可)を model card で
  確認して代替。量子化が Q4_K_M と異なる場合はその旨を結果に併記。
- 3 変種すべての**正確なタグ・digest・パラメータ**を `ollama show` で記録。

### A-2. 測定 1 — メッセージ極性回帰(主観測)

Stage 1 の極性診断(notes/05 §4)と同一の設計を判定側のみで再実行:

- インボックスは**既存の 8B 産メッセージバンクから構成**(D-2 の 70B 測定と同じ
  流儀。生成はしない)。k ∈ {1, 2, 3, 5, 8}、TRUE 主張/FALSE 主張メッセージ数を
  ランダム化、A/B 割付・提示順ランダム化、変法 A プロンプト逐語。
- クレーム: Stage 1 の較正済み 17 クレーム。
- 予算: 変種あたり 6,000 呼び出し(並列インスタンス port 11435 で約 30 分/変種)。
  instruct も**同一バッチで再測定**する(陽性対照 + バンク・季節差の統制)。
- 解析: TRUE 主張数・FALSE 主張数を説明変数、クレーム固定効果つきロジスティック
  回帰。極性比 = |b_TRUE| / |b_FALSE|。クレームクラスタ pairs bootstrap 95% CI。

### A-3. 測定 2 — 裸の肯定指数(副観測、スキャフォールド最小)

Stage 2b の原クレーム 4 + 否定形言い換え 4 の 8 本(claim 6/382/1569/2070 と
90006/90382/91569/92070)について、メッセージなし(k=0)の裸判定を
変種 × クレーム × 64 呼び出し(A/B 完全カウンターバランス)。
対ごとに S = P(affirm|原) + P(affirm|言い換え) を報告(内容駆動なら S ≈ 1、
肯定バイアスは S を 1 から押し上げる)。予測: instruct S > 1.2、
H-tuning のもとで base S ≈ 1.0–1.1。

### A-4. パース門(base モデル対策、事前固定)

各変種で 200 呼び出しのパイロットを先行させ、単一文字 A/B のパース率を測る。
**95% 未満の変種が一つでもあれば**: 3-shot の形式例示(A/B 回答例 3 つ)を
プロンプト先頭に付加した fallback 版を **3 変種すべてに同一適用**して全測定を
実施(比較可能性のため。素版パイロットの数値も報告に残す)。fallback でも
base が 90% を切る場合はその旨を報告し、base は S 指数(A-3)のみで評価。

### A-5. 成果物

`results/stage2c_d3_polarity.csv`(変種 × 係数 × CI)、
`results/stage2c_d3_bare_pairs.csv`、生 JSONL、
`notes/16_stage2c_results.md` の Part A 節(予測表 vs 観測、判定文、限界一文)。

---

## Part B: qwen3:8b 閾値予測の系統較正(推奨・約 8–12 h)

### B-0. 目的

原稿の結び主張「転換点の有無と位置は集団を走らせる前に単体測定から判定できる」は
現状 2 クレームの的中(+1 部分一致、1 外れ)に立つ(notes/14 §4 の明記済み限界)。
クレーム数を 8 に拡張し、**予測閾値 vs 観測境界の系統比較**に格上げする。
手順は D-1(notes/13 §7)と完全同一のパイプライン。qwen3:8b(タグ 500a1f067a9f、
think:false)のみ。llama には触れない。

### B-1. 較正と選定

1. CLIMATE-FEVER から未使用の候補 20 本(SUPPORTS 10 / REFUTES 10)を、
   フルスキャフォールド下の二段較正(24 → 境界域 64 呼び出し、A/B カウンター
   バランス)にかける。
2. 各候補にミニ単体測定(D-1 と同じ per-claim フィット設計、約 1,200 呼び出し/
   クレーム)→ 縮約 → 固定点計算(α ∈ {0.30, 0.55})。
3. **8 本を選定**: 内部不安定固定点が [0.10, 0.90] に予測されるもの ≥ 4、
   正答側単安定 ≥ 2、誤答側支配 ≥ 2(取れる範囲で近づける。双安定が 4 本
   未満なら候補を 10 本追補して再較正)。選定規準はこの文言で固定。

### B-2. 予測の凍結

集団エピソードを 1 本でも走らせる**前に**、選定 8 クレーム × α ∈ {0.30, 0.55} の
固定点(安定・不安定すべて)と予測分類(単安定正答 / 単安定誤答 / 双安定 +
閾値位置)を `results/stage2c_blind_predictions.csv` に書き出し、
sha256 と mtime を `notes/16` に記録する。

### B-3. 集団

- α ∈ {0.30, 0.55}、x₀ ∈ {2, 6, 10, 14, 18, 22, 26, 30}/32、2 反復
  → 8 クレーム × 2 × 8 × 2 = **256 エピソード**(D-1 実績から約 8–12 h)。
- プロトコルは D-1 と同一(N=32、T=8、Markovian inbox、メッセージは qwen 自己生成、
  seed 記録)。

### B-4. 解析(事前固定)

- クレーム × α ごとに: 観測境界 = 最終アウトカム(δ=0.1 分類)vs x₀ の単調
  ロジスティックフィットの 50% 交差点、エピソード bootstrap 95% CI。
  全セル同符号(境界なし)の場合は「単安定」と分類。
- 主表: 予測分類 vs 観測分類の 8×2 一致表 + 双安定セルの予測閾値 vs 観測交差の
  散布(これが図の素材)。的中・部分・外れをすべて列挙(D-1 と同じ透明性)。
- 副解析: 予測閾値と観測交差の順位相関(双安定セルが 4 点以上あるとき)。

### B-5. 成果物

`results/stage2c_group.csv`(全エピソード)、`results/stage2c_thresholds.csv`
(予測 vs 観測)、生ログ、`notes/16_stage2c_results.md` の Part B 節。

---

## 禁止事項・完了条件

- 原稿(01_draft.md / tex/)には Part 0 の 4 置換以外、一切触れない。
  Part A/B の結果の原稿反映はユーザと Cowork 側で行う。
- 既存 results/・external/ の変更禁止。集団実験の追加(Part B の 256 本以外)禁止。
- 完了条件: Part 0 の再ビルド成功 + notes/15 追記、Part A の判定文、
  Part B の凍結 → 集団 → 一致表。すべて `notes/16_stage2c_results.md` に集約。
