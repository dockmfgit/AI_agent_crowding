# 原稿ビルド記録（notes/manuscript_build_instructions.md v1.0 の実施）

日付: 2026-08-27。成果物:

- `manuscript/tex/main.tex` → `manuscript/main.pdf`（13 頁、pdflatex+bibtex、エラー 0）
- `manuscript/tex/si.tex` → `manuscript/si.pdf`（8 頁）
- `manuscript/tex/figs/fig1–fig6`（PDF + 300dpi PNG、`scripts/40_manuscript_figs.py` で全再生成）
- `manuscript/tex/tables/*.tex`（16 断片、`scripts/41_si_tables.py` で results/*.csv から自動生成）
- `manuscript/tex/refs.bib`（書誌はウェブで確認、下記）

環境: 既存の texlive（/usr/bin/pdflatex）を使用、追加導入なし。

## 1. [USER] 項目一覧

1. **タイトル最終確定**（現行は候補 1 を仮置き）:
   1. Input crowding and the tipping point of collective truth-finding in networks of language-model agents（現行）
   2. A critical crowding level for collective truth-finding in networks of language-model agents
   3. From single-agent response to collective fate: input crowding and the truth-committor of LLM collectives
2. **so-what 一文**（本文未挿入。00_outline の候補）: a. (log N)/α の飽和則 / b. K* の読み下し
   / c. 人間の α の位置づけ / d. マルチエージェント設計への含意 / e. 場支配相の実測
   / f. 「転換点の有無自体がモデルの性質で、単体測定から事前判定できる」
3. **所属・連絡先・資金・謝辞**: main.tex の `\thanks{[USER: ...]}`。
4. **synaptic crowding 論文の正確な書誌**: refs.bib の `SciRepCrowding` は
   プレースホルダ（本文 2 箇所で引用。埋めるまで引用表示は [USER:...] のまま）。
5. **公開リポジトリの場所と範囲**: Methods の Data availability に [USER:] あり。
6. **Discussion の散文化**: §6 は draft v0.3 の骨子（箇条書き）を忠実に保持した。
   散文化は科学的主張の再構成を伴うため本ビルドでは行っていない。

## 2. ビルド上の判断・逸脱の記録

- **Abstract 圧縮**: 原文 386 語 → 250 語ちょうど。数値はすべて保持
  （31,824 / 6,400 / 1,414 / α*=0.435 / 6.4/31 / 2–6% / 75% / 0.005 / 0.125 / 0.625 /
  0.12–0.15 / 0.62 / 1/4 / 1.44→1.03）。**純粋な削除だけでは 250 語に届かず、
  最小限の語順変更・接続の付け替えを行った**（指示は「削除のみ」— 逸脱として記録。
  原文と圧縮版の対照は §5）。
- 図はすべて再生成（既存 fig/ は下敷きのみ）。Fig 3a の減衰曲線 2 本は、
  実測パラメータ（γ=0.9, α_load=0.14）の形状をスケール係数のみ最小二乗で
  当てた提示用オーバーレイ（新しい統計主張ではない）。
- Fig 4b・SI の「修正入力アトラクタ」数値は notes/12 §3 の記載値をそのまま使用
  （再計算はしていない）。
- refs.bib の `Ashery2025` はビルド指示に従い収載したが、draft 本文に言及箇所が
  ないため未引用（出力 PDF には現れない）。
- De Marzo et al. の arXiv:2409.02822 は最新版でタイトルが
  "AI agents can coordinate beyond human scale" に変更されている（旧題
  "Language Understanding as a Constraint on Consensus Size in LLM Societies"）。
  最新版タイトルで収載。
- qwen3:8b の暫定盲予測表（stage2d_blind_predictions.csv）で claim 382/90382 の
  固定点欄が空（F(x)>x 全域 = 境界吸収）。SI 表では "none (flows to boundary)" と表記。

## 3. 文献確認（確認 URL）

| キー | 確認結果 |
|---|---|
| El2026 | arXiv:2608.16578、El, Paeng, Dinc, Su, Erdogan, Pappu, Ye, Zhao, Ganguli, Zou (2026-08-17) — https://arxiv.org/abs/2608.16578 |
| Diggelmann2020 | arXiv:2012.00614、NeurIPS 2020 Climate Change workshop — https://arxiv.org/abs/2012.00614 |
| Taniguchi2024 | arXiv:2409.00102（RSOS 12:241678 は notes/11 の記載に基づく。arXiv ページに誌情報なし — 投稿前に RSOS 掲載情報の最終確認を推奨）— https://arxiv.org/abs/2409.00102 |
| DeMarzo2024 | arXiv:2409.02822、De Marzo, Castellano, Garcia — https://arxiv.org/abs/2409.02822 |
| Ashery2025 | Science Advances 11(20):eadu9368 — https://www.science.org/doi/10.1126/sciadv.adu9368 |
| CarandiniHeeger2012 | Nat Rev Neurosci 13:51–62, doi:10.1038/nrn3136（標準文献、ウェブ照合は DOI のみ）|
| SciRepCrowding | **[USER] プレースホルダ（未確認・未記入）** |

## 4. 数値照合表（本文の値 → 出典 → 出典値）

「一致」= 丸めの範囲で一致。**不一致・照合不能は太字**で列挙（本文は変更していない）。

### Abstract / §1 / §2

| 本文の値 | 出典 | 出典値 | 判定 |
|---|---|---|---|
| 31,824 queries | notes/05 §3 | 31,824、パース失敗 0 | 一致 |
| α*=0.435, K*=6.4 | notes/08 §5–6 | 0.435 (K*=6.4) | 一致 |
| 閉形式誤差 2–6%（中央値 2.1/6.4%、最悪 9%）| notes/08 §5 | 2.1% / 6.4% / 9% | 一致 |
| K̄ の過小 3–11% | notes/08 §2 | −3%（α=0.3）〜−11%（α=2）| 一致 |
| λ=1 の過大 30–90% | notes/08 §4 | 30–90% | 一致 |
| 場の遮蔽 K≈10 | notes/08 §4 | K≈9.7 | 一致（丸め）|
| **El et al. 9,600 communities** | El2026 abstract / notes/00 | **abstract は「over 10,000」、Stage 0.5 の客観系は 6,400（＋主観 6,400）** | **照合不能（draft 値の出典を特定できず）** |
| 6,400 published communities | notes/00 | 6,400（客観）| 一致 |
| **§3 "40 questions, 12 graphs, four episodes"** | notes/00 | **1 問あたり 10 グラフ（distinct グラフは 12 ランダム + 2 格子 = 14）。4×40×12×4 ≠ 6,400** | **不一致（"12" はランダムグラフ総数の意味なら正しいが per-question ではない）** |

### §3（再解析）

| 本文の値 | 出典 | 出典値 | 判定 |
|---|---|---|---|
| 問題間分散 50–99.5% | notes/02 A-1 | 0.503–0.995 | 一致 |
| 問題内相関 0.04–0.27 | notes/02 A-1 | 0.041–0.273 | 一致 |
| x₀=0.15 で 32/32 正答 | notes/02 A-1 | math_train_497: x̄₀=0.149, q=1.000, n=32 | 一致 |
| クラスタ CI 4–10 倍 | notes/02 A-6 | 3.9×–9.6× | 一致 |
| ランダム族 k=2–4 集中 | notes/07 §5 / notes/00 | 質量 66% が k=2–4 | 一致 |
| w_T 旧推定 1.16–1.71 | notes/00（Table 3 比）| 1.159–1.712 | 一致 |
| 43,500 obs/model | notes/02 A-3 | n_obs ≈ 43,500 | 一致 |
| GPT w_T 1.055 [0.996,1.114] | notes/03 R-2 | 同値 | 一致 |
| λ_lab 0.08–0.56 | notes/03 R-2 | 0.080–0.555 | 一致 |
| θ 全モデル t≥3.4 | notes/03 R-2 | t ≥ 3.4 | 一致 |

### §4（単体測定）

| 本文の値 | 出典 | 出典値 | 判定 |
|---|---|---|---|
| **"8-bit-quantized"（llama3.1:8b）** | notes/05 §0 | **Q4_K_M = 4-bit 量子化** | **不一致（draft 由来。Methods 節は Q4_K_M と正記）** |
| 17 claims, \|h_q\|<0.4, 16/17 REFUTES | notes/05 §1 | 同値 | 一致 |
| 裸較正の非転移、幅 3.5 logits | notes/05 §7-2 | FE 範囲 [−0.72, +2.76] = 3.48 | 一致 |
| 極性比 1.44 | notes/05 §4 | 1.443 | 一致 |
| w_T 0.74–0.89 | notes/05 §4 | 0.738 / 0.894 | 一致 |
| h=0.725 [0.516,0.915] | results/stage1_coeffs.csv | 同値 | 一致 |
| θ=1.909 [1.723,2.106] | results/stage1_coeffs.csv | 同値 | 一致 |
| e^{−0.14k} / β/(1+0.9k) | results/stage1_decay_models.csv | α_load=0.14, γ=0.9 | 一致 |
| 変法 A α* 0.40–0.46（全縮約）| notes/06 §2 | 0.40–0.46 | 一致 |
| 変法 B 0.46 vs 1.27–1.33 | notes/06 §2 | 0.46 / 1.27–1.33 | 一致 |

### §5.1–5.2（集団第一波）

| 本文の値 | 出典 | 出典値 | 判定 |
|---|---|---|---|
| 1,414 episodes、パース失敗 0 | notes/07 冒頭 | 1,414 / 0 | 一致 |
| q<0.5 全セル | results/stage2_committor.csv | 最大 q=0.45 | 一致 |
| 低 x₀ 誤答率 0.98→0.75 | results/stage2_alpha_star_emp.csv | 0.982→0.750 | 一致 |
| 0/2,000 bootstrap 交差 | results/stage2_alpha_star_emp.csv | 0/2000 | 一致 |
| Brier 0.10–0.16 vs 0.17–0.25 | results/stage2_onestep_calibration.csv | 0.1028–0.1581 / 0.1735–0.2465 | 一致 |
| 争点構成バイアス −0.20 | notes/07 §3-4（0.574 vs 0.390）| −0.184（表では −0.196 の帯）| 一致（丸め）|
| 0.29 vs 0.54（k=8,l=4）| notes/12 §2 / notes/07 §3-4 | 0.292 / 0.54 | 一致 |
| x*=0.011（α=0.2）| notes/12 §3 | 0.011 | 一致 |
| **x* "toward 0.16 (α=1.3)"** | notes/12 §3 | **記載は 0.078（α=1.0）まで。0.16 の出典を特定できず** | **照合不能** |
| 定数則 x*=0.44@1.3 / 正規化 0.067, 0.093 | notes/12 §3 | 0.438 / 0.067, 0.093 | 一致 |
| 観測 0.061–0.072 / 0.092–0.097、±0.005 | notes/12 §3 | 同値 | 一致 |
| ρ: 最大 0.09、4/6 セルで 0.00 | results/stage2_rho_control.csv | −0.0875 最大、4 セル 0 | 一致 |

### §5.3–5.4（判別・一般性）

| 本文の値 | 出典 | 出典値 | 判定 |
|---|---|---|---|
| A-1 x̄₈ 0.67–1.00（12.5% 開始込み）| results/stage2b_group.csv / notes/13 §5 | 最小 0.667 | 一致 |
| A-2 0.98–1.00 vs 原 0.00–0.43 | notes/13 §5 | 0.984–1.000 / 0.000–0.434 | 一致 |
| 場が否定側の言い換え p=0.34 | notes/13 §1 | 0.344 | 一致 |
| 1103@0.55 の外れ（予測 0.305、観測 0.67–0.79）| notes/13 §0 回答 | 同値 | 一致 |
| qwen 予測 0.12–0.15 / 0.62–0.66 | results/stage2d_blind_predictions.csv | claim 6: 0.149/0.121（α≤0.55; α=1.0 は 0.043）、claim 1239: 0.661/0.653/0.621 | 一致（本文の 0.12–0.15 は α≤0.55 の範囲）|
| 分裂 0.125 / 0.625、0.875 は正答 | results/stage2d_group.csv | x₀=4/32 で 0.20–0.88、x₀=20/32 で 0.00–0.42、28/32 で 0.94–1.0 | 一致 |
| 0.375 以上は正答収束（claim 6）| results/stage2d_group.csv | x₀≥12/32 全て 1.0 | 一致 |
| 1/4 外れ（1569）、部分外れ（91569@0.30）| notes/14 §2-2 | 同値 | 一致 |
| 70B 1.44→1.03、\|logit\| 3.7–7.2 | notes/13 §7 D-2 | 同値 | 一致 |

### §6 / Methods / SI

| 本文の値 | 出典 | 出典値 | 判定 |
|---|---|---|---|
| 不応係数 +0.98 | notes/13 §4 E-5 | +0.98 (SE 0.13) | 一致 |
| 分岐比 1.8–3.6 | results/stage2b_E_branching.csv | 1.776–3.546 | 一致 |
| 0.62 / 3.5 gens/s | notes/07 §0 | 同値 | 一致 |
| qwen tag 500a1f067a9f | notes/13 §7 | 同値 | 一致 |
| 較正 24→64 回、opp. 70–85% | notes/05 §1 / notes/13 §1 | 同値 | 一致 |
| 忠実度 1.00/0.00/0.44 vs 0.875/0.125/0.38 | notes/07 §3-5 | 同値 | 一致 |
| 凍結時系列（08-23 / 08-25 / 08-26、13 時間前）| notes/07・13・14 §1 | mtime 08-26 03:00、D-1 完了 08-26 16:20 | 一致 |
| SI: qwen SUPPORTS 4 / REFUTES 3 | notes/13 §7 D-1 | 同値 | 一致 |
| SI: async 91.8% size-1、幾何裾 | results/stage2b_E_async_cascades.csv | 9341/10178=91.8% | 一致 |
| SI: ラベル残差 r=0.194 (n=1,008) | notes/13 §4 E-4 | 同値 | 一致 |
| SI: 反復曝露 +0.026 (0.006) / −0.004 (0.003) | notes/13 §4 E-3 | 同値 | 一致 |
| SI: 70B per-k 2.41→1.35、極性 +0.583/−0.563 | セッション記録（2026-08-27 の追加集計）| 同値 | 一致 |
| SI 自動生成表（16 本）| results/*.csv | スクリプト転記 | 一致（機械転記）|

**不一致・照合不能の総括（本文は未変更、ユーザ判断待ち）**:
1. §1 の「9,600 communities」— El et al. abstract は「over 10,000」、再解析対象は 6,400（客観）。
2. §3 の「12 graphs」— 1 問あたりは 10（12 は distinct ランダムグラフ数）。
3. §4 の「8-bit-quantized」— 実体は Q4_K_M（4-bit）。Methods は正しい表記。
4. §5.2 の「toward 0.16 (α = 1.3)」— notes/12 に対応値なし（0.078@α=1.0 まで）。

## 5. Abstract 原文（v0.3、386 語）と圧縮版（250 語）

### 原文（01_draft.md より逐語）

> Collectives of large-language-model (LLM) agents can settle on a wrong consensus even when a minority of agents starts from the correct answer. We ask to what extent the fate of such a correct minority is fixed by a single parameter of the individual agents — a crowding parameter α that limits how many sources each agent accepts, and thereby generates the interaction network itself — rather than by anything fitted to collective behavior. Building on a resource-allocation model of synaptic input selection, we let each agent accept a further input with probability e^{−αr} when r inputs are already accepted, which yields a mean in-degree (log N)/α and an in-degree distribution available in closed form. Combining this distribution with response coefficients measured on single agents (31,824 randomized single-shot queries to an 8-billion-parameter model), we derive, in closed form and with no fit to collective data, a critical crowding level α* at which the wrong-consensus basin of the collective dynamics disappears; for our measured coefficients α* = 0.435, equivalently a threshold mean fan-in of 6.4 out of 31 possible sources, and the closed form tracks exact numerics to within 2–6%. A reanalysis of 6,400 published LLM communities shows why existing datasets cannot test such predictions: initial correct fractions are endogenous to question difficulty. We therefore ran 1,414 collective episodes with exogenously assigned initial opinions on crowding-generated networks. The pre-registered prediction failed: no critical crowding level appears in the measured window, and the collectives converge on the wrong consensus from almost every initial condition — including majorities of 75% correct agents. The failure localizes, however, not to the theory's collective step but to coefficient transport: [...] (中略 — 全文は manuscript/01_draft.md にあり)

### 圧縮版

main.tex の Abstract（250 語、数値全保持）。

## 6. 残作業（ユーザ向け）

- [USER] 5 項目（§1）の記入。
- 不一致 4 件（§4 総括）の裁定。
- §6 Discussion の散文化と so-what の選定。
- Taniguchi et al. の RSOS 掲載情報の最終確認。

## 7. 修正記録（Stage 2c Part 0、2026-08-27）

notes/15 §4 の不一致 4 件をユーザ裁定（stage2c 指示書 Part 0）に従い修正した。
`manuscript/01_draft.md` と `manuscript/tex/main.tex` の両方に適用し、main.pdf を
再ビルド（13 頁、エラー 0）。si.tex に該当箇所なし（確認済み）。

| # | 修正前 | 修正後 |
|---|---|---|
| F-1 | describes 9,600 such communities | describes more than 10,000 such communities |
| F-2 | (four models, 40 questions, 12 graphs, four episodes) | (…, ten graphs per question, …) |
| F-3 | 8-bit-quantized | 4-bit-quantized (Q4_K_M) |
| F-4 | toward 0.16 (α = 1.3) | to 0.078 (α = 1.0) |

## 8. v0.4 改稿記録（Stage 2c 反映、Cowork 側で実施 2026-08-28）

対象: `01_draft.md`・`tex/main.tex`・`tex/si.tex`・`00_outline.md`。根拠は
`notes/16_stage2c_results.md` と独立検証 `notes/17_stage2c_verification.md`。

- **§5.4**: 8 クレーム系統較正の段落を追加（20 候補 → 選定 8、凍結 → 256
  エピソード、分類一致 14/16、双安定 10 セルの ρ=0.68 / p=0.03、CI 内 7/10、
  1146 の境界ケースと 1151 の系統的外れを明記）。
- **Fig 7 新設**（`figs/fig7_calibration.pdf/png`、予測 x_c vs 観測交差の散布、
  既存様式 #2E6FB7/#C8442C）。図番号は Fig 6（一般性）の直後。
- **Abstract**: 較正の一文を追加。250 語 → 271 語（1,904 字。arXiv の 1,920 字
  制限内。250 語指針からの逸脱として記録）。
- **Discussion**: D-3 の一項を追加（abliterated でチャネル保持 1.24 [1.05, 1.47]、
  base は強制選択設計の外・パース率 5% 未満。因果語なし）。
- **Methods**: 「Cross-model calibration campaign」小節を追加。事前登録時系列に
  (iv) を追加 — 凍結はドライバ起動の**約 1 分前**（notes/16 の「約 1 時間」は
  誤りにつき採用せず。sha256 = 06d320c2…8572、notes/17 §2 で照合済み）。
- **si.tex**: 「Stage 2c」節を Residual 節の前に挿入（16 セル全表 + D-3 表）。
  プレアンブルに `\usepackage{xcolor}` を追加（クラウド側 texlive 2023 で
  hyperref の色指定が未定義になるため。出力は不変）。
- 再ビルド環境: クラウド側 texlive 2023（pdflatex + bibtex）。main.pdf 15 頁・
  si.pdf 10 頁、エラー 0、未解決参照なし。数値はすべて notes/16・17 の検証値と
  照合済み。[USER] 項目は §1 のまま未変更。
- （追記 2026-08-28）§2.2 に縮約前の完全 HMF 写像 F(x) を表示式で追加し、
  「閾値ユニットは実測ロジスティックの無限利得極限であり、閾値非線形性は
  どこにも仮定しない」「元論文 [SciRepCrowding] の平均場構成の閾値ユニットを
  実測ロジスティックに置換したものである」ことを明文化。Methods の
  Networks/episodes に、Markovian プロトコルが HMF 独立性仮定を支える設計で
  ある旨の 1 文を追加。式番号が 1 つずつ繰り下がる（G: (2)→(3)、λ: (3)→(4)）。
- （追記 2026-08-28、その 2）ユーザ提供の原著 URL により §1 の [USER] 項目 4 を
  解消: refs.bib の `SciRepCrowding` を正式書誌で置換（Fukushima, M.
  "Analytically tractable model of synaptic crowding explains emergent
  small-world structure and network dynamics." Sci Rep 16:11748 (2026),
  doi:10.1038/s41598-026-47213-2 — https://www.nature.com/articles/s41598-026-47213-2 で確認）。
  §2.2 の元論文の記述を原文どおりに修正: ユニットは sign 型の硬い閾値
  （truth weight は元論文にはなく、weighted-majority の語を削除）。committor
  q(x₀) の吸収マルコフ連鎖による計算も元論文由来である旨を追記。
- （追記 2026-08-28、その 3）文献調査レビュー（notes/18）に基づく引用更新:
  refs.bib に DeNobili2026 / Arditi2024 / Sharma2023 / HuQu2026 / Chuang2024
  を追加（全件 arXiv 原典で実在・内容確認済み）。§1 の novelty 文を
  De Nobili を最近接先行として引用・区別する形に差し替え（不在主張を
  「crowding 生成ネットワーク」と「truth-finding 集団の盆地境界の凍結予測」に
  限定）。§5.3 末に Chuang らの truth-ward 収束の極性再解釈 1 文。
  Discussion の D-3 項に Arditi（手法）と Sharma（sycophancy との区別）、
  対話無効項に Hu & Qu の 1 文。調査で誤記述と判明した 2608.03744 は不引用。
- （追記 2026-08-29）so-what 確定（本人選択・案 1 = d 主軸）: 00_outline の
  空欄に記入。「注意予算」は英語本文では intake budget（attention 禁止規約を
  維持）。Abstract の結び一文を f 軸（転換点の有無は単体で測れる）から
  d 軸（intake budget は臨界値が事前計算できる設計変数、条件は場の先行測定）に
  差し替え。§6 lead claim を b–d 先行・三モデルは実証の位置に並べ替え。
  e・f の記述自体（§5.3–5.4、較正 14/16 等）は不変 — 位置づけのみ変更。
- （追記 2026-08-29、その 2）[USER] 項目の解消: 著者注を「Honda Research
  Institute Japan / makoto.fukushima@jp.honda-ri.com」で確定（謝辞・資金は
  なしとの本人指定）。Data availability は「GitHub で公開予定」とし、
  残る [USER] は リポジトリ URL の 1 箇所のみ。公開準備一式（README /
  LICENSE(MIT) / .gitignore / MANIFEST — サイズ実測と 418 MB エピソードの
  取り扱い 3 案、除外物: serve ログ 20.8 GB・external/）を repo_prep/ に配置。
- （追記 2026-08-29、その 3）PNAS Nexus 投稿版の準備: §6 Discussion を散文化
  （骨子 8 項の内容・数値は不変。順序変更 1 点 — K_shown 段落を lead 段落末尾に
  統合。メタ指示文「boundary sentence を書け」を境界文そのもので置換。結びの
  実務則 2 文を新規追加）。Abstract 直後に Significance statement(107 語)を
  新設(so-what 案 1 の英語圧縮)。cover_letter_pnasnexus.md を新規作成
  ([USER]: 推薦査読者)。skeleton 注記を削除。main.pdf 16 頁・エラー 0。
- （追記 2026-08-29、その 4）Flint, Aiello, Pastor-Satorras & Baronchelli,
  PNAS 123(34):e2531697123（2026-08-18 掲載、ユーザ提供 PDF で全文確認）を
  refs.bib に追加し、§1 の最近接先行を naming game 系 2 本（De Nobili +
  Flint）に拡張（区別軸: 規約 vs 真偽、完全混合 vs 生成ネットワーク、凍結予測の
  有無）。未引用だった Ashery2025 も同節で引用に昇格。Discussion の El 関係段落に
  「モデル依存レジームの収束証拠 + 彼らの future work（構造化トポロジー）を
  crowding 過程が供給する」の 1 文を追加。FAST 版にも同一の 2 編集をミラー。
  両 PDF 再ビルド、エラー 0。
- （追記 2026-08-29、その 5）リポジトリ確定に伴う最終記入: GitHub アカウント
  dockmfgit を実在確認し、Data availability の URL を
  https://github.com/dockmfgit/AI_agent_crowding で確定（**main.tex の [USER]
  プレースホルダはこれで全て解消**）。コミット著者メールは
  dockmfgit@users.noreply.github.com（本人承認）。カバーレターにも URL を追記。
  指示書 repo_prep/github_publish_instructions.md は v1.3（記入完了・実行可）。
  残る投稿前判断: タイトル最終確定（現行候補 1）と推薦査読者のみ。
- （追記 2026-08-29、その 6）本人指摘による帰属修正: §2.1 Network generation の
  受容過程・P(k) 漸化式・E[K]=(log N)/α を \citet{SciRepCrowding} に明示帰属し、
  「New here is only the closure」で有限 N 閉形式 K̄(α) のみが本研究の寄与である
  線引きを追加。draft・FAST 版にも同一修正。両 PDF 再ビルド、エラー 0。
- （追記 2026-08-29、その 7）scientific-writing 規範による文体レビュー:
  強意語・編集的形容の除去 5 件（genuinely ×2、demonstrating→showing、
  essentially tie→are indistinguishable、transparent 削除）。図を主語にした文・
  因果語・新規性語・opinion-signaling 語は検出ゼロ（既適用の執筆規範と重複する
  ため違反が少ない）。据え置きと判断した項目: "sharpens/sharper"（直後に数値で
  定量化されており容認）、Abstract 278 語（arXiv 制限内・PNAS 改訂時に調整）、
  Results/Discussion の節内混在（物理系の叙述様式 + 各節末主張の規範として意図的
  — 生物医学式の分離は行わない）。draft・FAST 版にも該当箇所を反映、両 PDF
  エラー 0。
- （追記 2026-08-29、その 8）本人指摘の p3 はみ出しを修正: §2.2 の h/β̄/δ 定義を
  align 環境（数式内長文注釈、188pt 超過）から散文へ、式 (2) の u_s 定義を式外の
  後続文へ移動、Methods の逐語プロンプトを footnotesize 化 + 改行挿入。
  全 Overfull 0 件を確認。Overleaf プロジェクト(AI_agent_crowding_manuscript)の
  main.tex も差し替え・再コンパイル済み。内容・数値の変更なし（レイアウトのみ）。
- （追記 2026-08-29、その 9）本人指摘の図の不具合を修正: Fig 1(b) のボックスから
  のテキストあふれ（箱を拡大・文言短縮・フォント 6.3pt・行間調整）、Fig 1(a) の
  α=0.45 ラベルの曲線への重なり（ピーク上方へ移動）、Fig 6(b) の目盛ラベル同士の
  重なり（バー間隔を拡大し 2 行ラベル化）、Fig 6 の suptitle 切れ（削除 —
  内容はキャプションと (a) 接頭辞に既存）。scripts/40_manuscript_figs.py にも
  同一修正を反映（再生成時の回帰防止）。本体・FAST・Overleaf の 3 箇所を更新、
  全ビルドエラー 0。データ・数値の変更なし。

## 追記その 10(2026-08-29): α 解釈段落とタイトル変更

- Discussion に α の解釈段落を追加(「coefficient transport, not the identity
  of the degree.」の直後)。内容: 本実験では router が課す enforced reading
  budget / 配備系では context window・token cost・sampling policy / naming game
  では finite interaction memory [Flint2026] / 人間では divided attention
  [HodasLerman2012]。モデル自身の容量は β(k) として別勘定。refs.bib に
  HodasLerman2012(arXiv:1205.2736, ASE/IEEE SocialCom 2012)を追加。
- タイトル変更(本人決定 2026-08-29):
  旧: Input crowding and the tipping point of collective truth-finding in
      networks of language-model agents
  新: **Message-capacity limits of individual agents set the transition point
      of collective truth-finding in language-model networks**
  理由: 手段語(crowding)先頭では意義が伝わらない(本人指摘)。結論型・
  d 軸。"phase transition" は有限 N の fold に対する厳密性懸念があり
  "transition point" を採用。本文の "tipping point" とは非矛盾。
- 反映先: main.tex / 01_draft.md / 00_outline.md(候補 0 として記録)/
  cover_letter_pnasnexus.md / fast_main.tex(+ 凝縮 1 文と Hodas 参照追加、
  再ビルド 9pp・エラー 0)/ openreview_metadata.md / repo_prep/README.md /
  overleaf_pkg(main.tex・refs.bib 差し替え、zip 再生成)。
- main.pdf 再ビルド: 16 頁、エラー 0、Overfull 0。fast_main は既存の数式
  Overfull 10.2pt(式、追加前から存在)のみ。

## 追記その 11(2026-08-29): 人間の討議への含意(本人指示)

- 本人指示「人間同士の討議でも認知的な記憶容量限界による問題が起こりうる、
  という示唆を discussion・イントロ・abstract に」→ 4 箇所に挿入:
  (1) Abstract 末尾に 1 文(同形の認知的 intake 限界 → 機械を超えた
  truth-finding の候補制約)。(2) Significance 末尾に同旨 1 文(全体を
  120 語ちょうどに圧縮し直し)。(3) §1 の「attention という語を避ける」文の
  直後に 3 文(working memory ~4 項目 [Cowan2001]・divided attention
  [HodasLerman2012] → 委員会や陪審への潜在的含意、ただし人間では bound も
  network も測定・統制不能で LLM 集団なら両方可能、という測定可能性の動機)。
  (4) Discussion の human-α 段落の前に 3 文(理論の入力はすべて行動量で
  機械基質に依存しない;有限実効 α に居る討議集団の運命は理論が指定する)—
  直後の既存の限定(人間の committor は未測定・倫理的に不可)は保持。
- refs.bib に Cowan2001(Behav Brain Sci 24:87–114)追加。
- 再ビルド: 16 頁、エラー 0、Overfull 0。Abstract は 312 語となり PNAS の
  250 語目安を超過 — 投稿直前に短縮パスを行うか要判断(本人へ報告済み)。

### 追記その 11 の修正(2026-08-29、本人レビュー後)

- Significance への追加文は取り下げ、元の 106 語版に復元。
- Abstract 末尾の追加文も削除し、代わりに冒頭へ問題意識として挿入
  (本人と文言を調整の上確定): "Human or machine, a group that debates runs
  on a bounded intake: each member can process only so many of the others'
  contributions." 続く問いの文は "We ask how far their fate is fixed by that
  bound alone, expressed as a crowding parameter α" に変更。
- §1・Discussion の追加(その 11 の (3)(4))は承認どおり維持。
- Abstract は 316 語(PNAS 目安 250 語超過 — 投稿前に短縮パス要否を判断)。
- 教訓: 本文変更は文案をチャットで承認後に適用する(本人指示)。

### 追記その 11 の修正 2(2026-08-30、本人と文言確定)

- Abstract 冒頭文を最終確定: "Human or large language model (LLM), an agent
  in discussion processes only a selected few of the others' contributions,
  bounded by cognition in the one case and by context and cost in the other."
  LLM の略語定義をこの文に移し、第 2 文は "Collectives of LLM agents ..." に
  短縮。dash 不使用・機械側の束縛(context and cost)を明示して
  「AI に限界はないのでは」という反論の入口を塞ぐ(ベッケンシュタイン限界の
  引用は桁違い(~40 桁)のため見送り、と本人合意)。
- Abstract 326 語(250 語目安超過は投稿前短縮パスで対応予定)。
- 再ビルド 16 頁・エラー 0・Overfull 0。

## 追記その 12(2026-08-30): 全体レビュー後の整合修正(本人承認済み)

- (a) §1 に同格挿入: "a finite intake budget --- the message capacity of an
  agent --- at the level of whole messages"(タイトル語 message capacity の
  本文への橋渡し。タイトル語が本文に 0 回出現していた問題への対処)。
- (b)(c) Abstract を 1,910 字 / 293 語の短縮版に差し替え(arXiv 上限 1,920 字
  対応)。削除: "within 2–6% of numerics" / "select the saturating coupling" /
  6,400 の数値(いずれも本文に残存)。予測閾値を 0.62 → 0.62–0.66 に修正
  (本文 §5.4 と整合、観測 0.625 は範囲内)。
- (d) Discussion の human-groups 段落の重複圧縮: Cowan/Hodas の再引用を
  "The cognitive limits cited in the Introduction" に置換(§1 と重複のため)。
- (e) tipping point → transition point を 4 箇所すべて統一(Significance、
  §1、§4、§5.4)。§1 初出のみ "(the tipping point of the social-dynamics
  literature)" を併記して文献検索性を保持。タイトルとの用語統一。
- 01_draft.md: Abstract を短縮版に置換(長文版は履歴に保存と注記)、
  a/d/e を同鏡映。fast_main.tex: Abstract 差し替え + 同格挿入、再ビルド
  (9pp・エラー 0)、zip 再生成。openreview_metadata.md の TL;DR も
  transition point に変更(keywords の "tipping points" は検索性のため維持)。
- main.pdf 再ビルド: 16 頁、エラー 0、Overfull 0。

## 追記その 13(2026-08-30): ニューロン還元の昇格(本人承認 P1–P5)

- Abstract を 1,911 字版に差し替え: 第 4 文で「8B モデルの判断が受信箱の
  重み付き和のロジスティック = divisively normalized な重みを持つ
  stochastic binary neuron に還元される」を測定事実として明示。
  圧縮: fan-in 6.4/31・極性証拠節・"question difficulty" 等(本文に残存)。
- P1: §2.2 の σ 導入文に "--- the update rule of a stochastic binary
  neuron" を追加(Abstract 語彙の本文への橋)。
- P2: §1 ロードマップに "reduce the experimental agent to a stochastic
  binary neuron and" を挿入。
- P3: §4 減衰段落末尾に還元の定量的裏付け 1 文を追加。数値は GX10
  results/ で検証: stage1_decay_models.csv の CV 対数尤度/観測
  (divisive −0.4828, load −0.4826, null −0.5091, chance −0.693)、
  stage2_onestep_calibration.csv の ECE 0.052–0.101(→ 0.05–0.10 と表記)。
- P5: Discussion の divisive normalization 段落の直前に新段落: σ 自体は
  softmax + 温度から機械的に出る/実測の中身はロジット差の加法性
  (条件付き独立証拠の集計と同型)と正規化減衰、という切り分け。
- P4: OpenReview keywords に divisive normalization を追加。
- FAST 版は Abstract + keywords のみ同期(凝縮 Discussion は既に
  "behavioral law with candidate mechanisms left open" を含むため)。
- main.pdf 再ビルド: 17 頁(P3+P5 で 1 頁増)、エラー 0、Overfull 0。
  fast_main 9 頁・エラー 0(既存の数式 Overfull 10.2pt のみ)。

### 追記その 13 の修正(2026-08-30、本人の文案ベース)

- Abstract のニューロン導入を dash 同格から明示的等価に変更(本人指摘:
  唐突さと dash 連続の回避): "..., equivalent to a stochastic binary neuron
  with divisively normalized weights. From its coefficients and degree
  statistics, without fitting to collective data, ..." の 2 文構成。
  併せて "; we ran" / "almost any start" に微修正。1,918 字 / 290 語。
- §2.2 の橋渡しも同形に: "where σ is the logistic function; the measured
  unit is equivalent to a stochastic binary neuron."
- main.pdf 17 頁・エラー 0・Overfull 0。FAST 版は Abstract のみ同期。

### 追記その 13 の修正 2(2026-08-30、本人指示)

- Abstract から "Public data cannot test this (initial fractions track
  difficulty);" を削除(経緯的記述の排除 — 内容は §3 に残存)。
  "exogenously assigned initial opinions" を復元。
- 棄却の報告を織り込み形に: "We ran 1,414 episodes ...; the collectives
  instead reached the wrong consensus from almost any start, including
  75%-correct majorities, rejecting the frozen prediction."(削除ではなく
  統合 — 棄却は結果であり Abstract に必須、と本人合意)。
- "mean fan-in 6.4 of 31" を予測文に復元。1,902 字 / 290 語。
- main 17 頁・FAST 9 頁、エラー 0。draft へも同鏡映。

### 追記その 13 の修正 3(2026-08-30、冷読レビュー後・本人承認)

- Abstract 最終確定(1,913 字 / 293 語): (1) S2 を "even when a majority
  starts correct" に(minority では "even when" の緊張が働かない。75% 多数派
  の敗北が根拠)。(2) S4 に "judgment of a claim" — claim を初出で導入し、
  後続の claim-resolved / assertion / tilt を着地させる。(3) "mean fan-in
  6.4 of 31 sources"。調整で "initial" を1語削除。
- main / draft / FAST の 3 コピーに同鏡映、再ビルド(17頁 / 9頁、エラー 0)。

## 追記その 14(2026-08-31): Abstract を「目的→結果」構成に再編(本人指示)

- 本人が Overleaf で加えた "we found that" / "effectively" を取り込み(Overleaf
  版との差分はこの 2 語のみであることをハッシュ照合で確認)。
- 手続き語(pre-registered / frozen / blindly)を Abstract から全撤去 —
  「予測が先に決められた」は Methods の詳細であり、Abstract は各実験の
  目的と結果の流れだけを運ぶ(本人方針)。本文の pre-registered は維持。
- 各ステップに「何をしたか」を一語で: assigned opinions / replaying every
  inbox / reversed the wording / the pipeline on another 8B model。
- 意味が自明でない数値を削除: 閾値位置の括弧・ρ = 0.68・1.44 → 1.03。
  代替表現: "where computed for three of four claims" / "14 of 16
  claim–capacity conditions" / "match observed attractor positions to
  within 0.005"。
- 締め: "A collective's fate is thus fixed by two single-agent
  measurements: the tilt a claim's wording induces, and the message
  capacity that sets the transition point."(S3 の問いに答え、タイトル語で
  閉じる。tilt は S8 で定義)。
- 1,913 字 / 293 語。main 17 頁・FAST 9 頁、エラー 0。
- 未対応(要判断): Methods の pre-registration 節に「内部凍結・外部
  レジストリ不使用」の定義 1 文を足すか。

## 追記その 15(2026-08-31): 新 Abstract 基準の本文照合と修正(本人承認)

- Methods「Pre-registration timeline」冒頭に定義文を追加(予測と判定基準を
  データ取得前にファイル化、タイムスタンプと SHA-256 をリポジトリに記録;
  外部レジストリ不使用)。FAST 版の同段落にも凝縮版を追加。
- Methods の "Three prediction sets" → "Four"(列挙は (i)–(iv) の 4 件。
  既存の誤記を修正)。
- Abstract: "where computed for three of four claims" → "where computed
  (one claim mispredicted, another in part)" — §5.4 の記述(1 件誤り、
  1 件部分的に誤り)に厳密に合わせる。1,918 字。
- Significance: "pre-registered" / "blindly" を削除(Abstract と同じ方針:
  一般読者向け前付けに手続き語を置かない)。104 語。
- 照合で整合確認済み: message capacity(§1)、tilt(Significance /
  Discussion 末尾)、ニューロン等価(§2.2)、リプレイ診断(§5.2)、文言反転
  (§5.3)、0.005、14/16、70B、§5.4 末尾の結論文。
- main 17 頁 / FAST 9 頁、エラー 0。
- 字数再計測で 1,930 字と超過が判明したため "collective episodes" →
  "episodes"、"attractor positions" → "attractors" に圧縮。確定 1,909 字。

## 追記その 16(2026-09-03): /scientific-writing 全文レビュー 2 ラウンド(本人承認・全適用)

- R1: §5.2 で "coefficient transport" を命名・定義(本文で初めて定義)。
  Discussion の未定義記号 K_shown を平文に。Fig 5・Fig 6 のタイトルを
  記述型に(解釈型を廃止)。Significance の dash 構文を括弧に。
  editorializing 2 句("worth stating precisely" / "worth keeping explicit")を削除。
  本文の "---" は物理系慣行として維持(本人判断; 連鎖ゼロを確認)。
- R2: 初出未定義の解消 — variant A(§2.3 で §4 参照付き gloss)、truth-weight 1、
  REFUTES/SUPPORTS(CLIMATE-FEVER ラベルと明記)、climatology(base-rate Brier)、
  記号 ρ の衝突解消(rewiring fraction を定義、Spearman は r_s に)、
  "arm-B" → "discrimination-arm"。表現: "fully accounts" → "accounts"、
  "decided every outcome" → "decided the outcome in every cell tested"、
  "is free" → "requires no new data"、"in one afternoon" → "in isolation"、
  x* の gloss。構成: §1 第 2 段落を分割。技術: sec:critical / sec:results の
  ラベル追加でハードコード参照を \ref に。
- main 17 頁・FAST 9 頁、エラー 0。draft / FAST へ該当箇所を鏡映。

## 追記その 16(2026-09-03): /scientific-writing 全文レビュー 2 ラウンド(本人承認)

第 1 ラウンド(適用): (1) §5.2 で "coefficient transport" を命名・定義(本文で
未定義だった)。(2) Discussion の未定義記号 K_shown を平文化。(3) Fig 5・Fig 6
のキャプション題を解釈型→記述型に。(4) Significance の dash 構文を括弧に。
(7) §3・Discussion の editorializing 句("worth stating precisely" /
"worth keeping explicit")を削除。本文の "---" 全面除去は本人判断で見送り
(物理系スタイル、1 文 1 構文で連鎖なし)。Abstract 末尾の "Thus," 開始も不採用。
第 2 ラウンド(適用): §2.3 variant A の前方参照に gloss、§2.2 truth-weight の
gloss、REFUTES の gloss、Brier の climatology を平文化、記号 ρ の衝突解消
(rewiring fraction を定義、Spearman を r_s に)、"arm-B" → discrimination-arm、
"fully accounts" → "accounts"、"decided every outcome" → "in every cell tested"、
"is free" → "requires no new data"、"one afternoon" → "in isolation"、
x* の定義句、§1 第 2 段落を分割、ハードコード相互参照 2 件を \label/\ref に
(sec:critical, sec:results)。FAST 版はキャプション 2 件のみ該当。
再ビルド: main 17 頁・エラー 0・Overfull 0・未定義参照 0。

## 追記その 17(2026-09-04): 新 Fig 3「stochastic binary neuron」図の導入(本人承認)

- 目的: abstract の中心結果(単一エージェントの判断が inbox の重み付き和の
  ロジスティック関数に帰着し、divisive normalization 付き確率的二値ニューロン
  と等価)を視覚的に示す。
- 図: (a) 本人作図の更新則スキーマ(figs/fig3_panel_a.png; 数式
  u = c0 + θs + β_T g(k) l + β_F g(k)(k−l), P = σ(u), g(k) = 1/(1+γk) を確認)。
  (b) 78 設計セル(variant × k × l × s、各 408 クエリ)の観測正答率を、
  claim 固定効果付きロジスティック回帰の fitted net input u に対して
  プロット。曲線は σ(u)(フィットではない)。divisive 正規化で全セルが
  曲線上に乗る(RMS 0.054、log-lik −13839)。(c) 定数重みでは k ごとに
  扇状に分離(RMS 0.118、log-lik −14888)。
- 図番号: 新 Fig 3 = fig3_neuron。旧 Fig 3(減衰曲線+係数区間、
  fig3_single_agent.pdf)は SI Figure S1 へ移動(si.tex に graphicspath と
  S 番号付けを追加、タイトルも新タイトルに更新)。
- 本文 §4: 冒頭に Fig 3 と SI Fig S1 の参照を追加、P3 の後に collapse の
  一文を追加。キャプション題は "Single-agent response as a stochastic
  binary neuron."(本人指示によりクエリ数はキャプション本文に記載)。
- スクリプト: scripts/41_neuron_io_fig.py(data/stage1/main_obs.parquet を
  読み、manuscript/tex/figs/ に fig3_neuron.pdf/png を出力)。
- FAST 版: appendix 図を fig3_neuron に差し替え(要約キャプション)。
- 再ビルド: main 17 頁・SI 11 頁・FAST 9 頁、エラー 0。
- 未対応: SI 表 t_stage1_coeffs.tex の variant A θ 行が空(" & [, ] ")。
- 追補(同日): Fig 3(a) の解像度不足を修正。原因は imshow の interpolation="lanczos"
  で PDF 出力時に 160×205 px へ再標本化されていたこと。interpolation="none" に
  変更し、元 PNG(1109×1419 px)をそのまま埋め込むようにした(scripts/41 更新)。
  SI 表 t_stage1_coeffs.tex の variant A θ 行(空欄)は削除(本人判断)。

## 追記その 18(2026-09-04): 新 Fig 3 導入後の /scientific-writing 全文レビュー(本人承認: 1–5, 7, 8)

- (1) Methods Statistics に Fig 3 の解析手順を追加(variant ごとの claim 固定効果付き
  ロジスティック回帰、重み β_T g(k)・β_F g(k)、γ=0.9 固定または g≡1、セルの u は
  予測確率平均の logit、観測率に Wilson 95% 区間)。
- (2) §4 の新文とキャプション (c) の "inside/outside the curve" を
  "between the curve and 0.5 / beyond it" に(冷読で曖昧)。
- (3) "The reduction is visible directly" → "The same reduction is visible directly"。
- (4) Discussion の softmax 段落に (Fig. 3b)、divisive normalization 段落の
  "measured update rule" に (Fig. 3a) を参照付与。
- (5) Fig 3 のキャプション題を記述型に: "Observed correct-side rate against fitted
  net input under divisive and constant message weights."(FAST 付録も同じ題)。
- (7) §4 "showing that the persistence ..." → "indicating that"(推論のヘッジ)。
- (8) §2.2 の応答関数の直後に "(with the per-message weights attenuated by inbox
  size as β g(k); Section 4)" を追加し、Fig 3(a) の式との往復を閉じた。
- (6) 該当なし、(9) 見送り。draft / FAST へ該当箇所を鏡映。
- 再ビルド: main 17 頁・FAST 9 頁、エラー 0・Overfull 0。

## 追記その 19(2026-09-04): カバーレター改訂・FAST 投稿取りやめ

- cover_letter_pnasnexus.md を現行原稿の書き方に合わせて改訂(冒頭を abstract と
  同じ問題意識から開始、ニューロン等価の結果を追加、message capacity /
  transition point / coefficient transport の語彙に統一、dash 構文なし)。
  推薦査読者 3–5 名の placeholder は未記入。
- FAST(NeurIPS 2026 workshop)への投稿は取りやめ(本人判断)。workshop_fast/
  のファイルは記録として残すが、以後の同期対象から外す。カバーレターの
  ワークショップ開示文は不要。
- GitHub 再プッシュ用の指示書 repo_prep/github_update_instructions.md v1.0 を作成
  (GX10 で実行予定)。
- 追補(同日): カバーレターに推薦編集者(D. G. Rand / D. Abbott)と推薦査読者 5 名
  (Baronchelli, Castellano, Burioni, Lerman, Rogers)を記入。El et al. の
  Ganguli / Zou は直接比較対象の著者のため候補から外した(必要なら追加可)。
- GitHub 再プッシュ完了(GX10、notes/19 更新節参照): コミット 1c2e14b、
  fast-forward、本人名義・トレーラなし、private 維持、tar.gz 再作成なし。
- 追補(同日): カバーレターから推薦編集者・査読者欄を外して 1 頁に(PNAS Nexus の
  公式指示ではカバーレター必須項目ではなく、投稿フォームの入力欄に入れるのが通例)。
  推薦リストは manuscript/reviewer_suggestions.md に分離(フォーム貼り付け用、
  メールアドレスは投稿時に確認)。PDF/tex(cover_letter_pnasnexus.pdf/.tex)を更新。

## 追記その 20(2026-09-04): Abstract を PNAS Nexus の 250 語制限に圧縮(本人承認)

- 293 語 → 247 語(1,684 字)。保持: 数値(31,824 / α*=0.435 / 6.4 of 31 / 1,414 /
  75% / 0.005 / 14 of 16 / 70B)、"we found that"、"effectively"、ニューロン等価の
  一文、最終文。
- 削除・短縮: "(mean in-degree (log N)/α)"、"in the one case ... in the other" →
  "or context and cost"、"in the same theory"、"another in part"、
  "claim–capacity conditions" → "conditions"、目的の前置き("To identify the
  driver" / "To test generality")を文頭の動作に畳み込み、"even when a majority
  starts correct" → "even from a correct majority"。
- main.tex / 01_draft.md / Overleaf に反映。arXiv 版も同一 abstract を使う
  (1,920 字制限内)。main 17 頁・エラー 0。

## 追記その 21(2026-09-04): Significance にニューロン等価を「計算できる理由」として追加(本人承認)

- 106 語 → 118 語(上限 120)。"intake budget with a computable critical value" の
  括弧を、「判断が divisive normalization 付き確率的二値ニューロンの入出力則に
  帰着するので転移点が閉形式で従う」の一文に置換。"two quantities" で構造を明示。
  末尾を "AI collectives can be assessed, and designed, before they run." に短縮。
- main.tex / 01_draft.md / Overleaf に反映。main 17 頁・エラー 0。

## 追記その 22(2026-09-04): El et al. データセットの引用項目を追加(投稿要件)

- PNAS Nexus の「使用したデータはすべて参考文献に引用」要件に従い、refs.bib に
  @misc{El2026data}(GitHub batu-el/physics-of-agents、commit f571742、取得
  2026-08-18、Apache-2.0)を追加。§3 冒頭と Methods の Data and code availability に
  \citep{El2026data} を付与。同一著者・同年のため本文引用は 2026a(論文)/
  2026b(データ)に分かれる。両エントリの "Physics of Agents" を波括弧で保護。
- 投稿フォーム記入: Data sharing は「persistent repository upon publication」
  (GitHub → 採択時に Zenodo DOI)+「Previously published data were used」。
  分類は Applied Physical Sciences(primary)+ Psychological and Cognitive
  Sciences(secondary)。「Culture and AI」特集には出さない(範囲外)。
  Competing interests: none。生成 AI 利用の開示文は 83 語版を用意(モデル名待ち)。
- main 17 頁・エラー 0。
- 追補(2026-09-05): Discussion の "a boundary condition for idealized-Bayesian accounts" を "a limiting condition on" に(物理の境界条件との混同回避、本人判断)。

## 追記その 23(2026-09-06): 投稿前レビュー対応の一括改稿(notes/21、revision_plan_v2、本人承認 D1–D4)

- タイトルを "Claim-induced fields and message-capacity limits set the transition
  points of collective truth-finding in language-model networks" に(main / si /
  cover letter / repo_prep README)。
- 修正値のみを記載する方針(D2)。"pre-registered" は (i) α*=0.435 と判定基準、
  (ii) 極性三仮説表、(iii) 8 claim の選抜規則に限定し、claim 別固定点予測は
  「集団実行前に完了した単一エージェント測定から計算、集団データへの当てはめなし、
  ただし事前登録ではない」と Methods に明記。frozen / SHA-256 / 「1 分前」の記述は
  本文・SI から削除(Methods の事前登録の定義文のみ残す)。
- 用語: coefficient transport → field transport(D1)。closed-form → reduced map。
  q(x0) は有限時間の committor 類似量と定義(R4)。
- Abstract 249 語 / 1,629 字、Significance 119 語。"At 70B the assertion bias is
  not detected"(70B 比 1.03 [0.66, 1.64]、同 8 claim の 8b 1.94 [1.39, 2.73]、差
  0.90 [0.00, 1.72]; results/r8_70b_polarity_ci.csv)。
- §4: 較正の事実(裸プロンプトで較正 → 足場で再拡大、平均 0.94)、識別済み per-k
  係数、null の訂正、Fig. 3 を較正図として説明、α* 0.40–0.47。
- §5.1: 8 ラウンド後の判定と操作的定義(決着中 |x8−0.5|>0.4 が主実験 63%、qwen 系
  97–99%; results/r4_outcome_distribution.csv)。
- §5.2: 診断を「場の非転移 + 有限時間」に全面改稿(perk17 Brier 0.10–0.14、ECE 0.03、
  争点残差 −0.02〜+0.01、場 0.16–0.55 対 0.94、x* 0.02–0.11、1569 の誤答盆地 x0≈0.7、
  surrogate RMS 0.09、平均場との差 0.04、盲予測則の有限時間 α*=0.63、α=0.45 で誤答
  67%)。arm B は「divisive 型が近い、定数則は棄却されない」(0.10–0.20 対 0.06–0.10、
  定数 0.25–0.39)。高 x0 残差 0.05–0.17(11/12 セル)。
- §5.3: 方向の取り違えを訂正、真理値反転、否定対の個別記述(2070 は contrary、
  "often" 保持)、90006 を場と極性が対立した鍵の事例として明記、1103 の例外を削除
  (識別済みでは正答側予測、全 10 セル一致)、parametric-prior の棄却を「試験した形」に限定。
- §5.4: qwen 4 claim を識別済み値で(閾値 0.14–0.21 / 0.70–0.71、12/12 一致、CI 内
  5/6)、8 claim は 15/16、CI 内 11/11、平均 |差| 0.04、r_s=0.96(claim 置換 p=0.004)、
  予測側区間(幅 0.08–0.25、全 11 セルで重なる、1146@0.55 の双安定率 0.62)。
  "errors one-sided toward the correct answer" を削除。
- Discussion: 教訓段落(場は対象 claim で測る、判定基準は実験の時間長で計算する)、
  検証範囲の明確化(固定 α の x0 閾値であり α の fold そのものではない)、w_T=1 の文を
  訂正、人間集団の段落を限定、"none ethically could be" 削除、softmax 条件、
  refusal direction "mainly"。
- Methods: 否定文の記述、ネットワーク固定と独立性近似(RMS 0.04)、Statistics に識別・
  固定点探索・予測側区間・Outcome and threshold(リッジ 0.002、claim 置換)を追加、
  CV の held-out claim FE=0 と γ の profile(0.9 / 変種別 0.53, 1.32)を明記、
  事前登録節を 3 項目に。
- §2: λ の文(σ̄′ 定義、対称条件、必要でも十分でもない)、h+Kδg(K)、fold と critical の
  用語、式(1)の適用範囲、検証精度 2.7% / 6.7%(最大 6.0% / 9.9%)、0.435 の登録値と
  精密解 0.439 の併記(results/r6_fold_precision.csv)。
- 図: Fig. 2(b) 精密 fold 値、Fig. 4(a) 盲予測則の 8 ラウンド surrogate 帯、(b) arm B
  観測対 surrogate、Fig. 6 星印を識別済み閾値に・(b) 同 8 claim 比較と CI、Fig. 7 を
  2 キャンペーン 17 セル + 予測側区間、SI Fig. S1 識別済み per-k(scripts/54)。
- SI: 識別済み per-k 表、fold 精密表(t_fold_precision)、outcome 分布表、arm B
  surrogate 表、one-step 表(perk17)、極性実験 10 セル表、qwen 固定点表(識別済み +
  区間)、qwen 48 セル計数表、16 セル表(予測区間・双安定率つき)、「Recorded prediction
  misses」節を削除、70B 区間、右端切れをすべて resizebox で解消。main 19 頁・SI 12 頁、
  エラー 0。
- 01_draft.md はこの改稿から鏡像更新を停止(tex を正本とする)。GitHub 再プッシュは
  別指示で(scripts 53–57・results r4/r5/r6/r8・図・表・原稿を含める)。

## 追記その 24(2026-09-06): 修正版レビュー(M1–M5、§4、S1–S8)への対応

- M1: 原稿フォルダ直下に残っていた旧 fig7_calibration.{pdf,png}(8/27)が figs/ の新図を
  隠していた(graphicx はカレントを先に探す)。旧ファイルを _stale/ に退避し、クリーン
  再ビルドで新 Fig. 7(17 セル、横棒 = 予測側区間)を確認。Overleaf は figs/ のみで混入なし。
- M2: §2.2「λ>1 なら対角線を三度横切る」を固定点構造の記述に置換。§2.3 対称条件を
  h = 0 かつ δ = 0 に。
- M3: 75% 開始の数量化(x0 = 24/32: 正答側 28–45%、誤答側 33–73%、未決着 0–28%)を
  Abstract・§5.2・Fig. 4 キャプション・図中注記("observed: q < 0.5 from every start")・
  Discussion(2 箇所)に統一。「全 claim が単安定」→「3 claim が誤答側単安定、1 claim は
  閾値 ≈0.7 の双安定」。Abstract は 249 語 / 1,623 字("generating the network" を削除)。
- M4: Methods 事前登録節に「単一エージェント測定は集団実験に先行。claim 別予測は集団実験の
  後に、Statistics の推定法で、単一エージェントデータのみを当てはめて計算。前向き登録ではない」
  を明記(本人承認)。§5.4 の "then collectives"、Discussion の "ours predict before the run"
  を修正。「誰でも検証可能」→「ローカル記録であり第三者のタイムスタンプではない」。
- M5: softmax は P(A | A or B) = σ((z_A − z_B)/T) の条件付き確率として記述、集団でのパース
  失敗 0 を根拠に近似と明記。閾値回帰: リッジは有限推定のため、傾きは制約せず非正なら棄却
  (該当なし)、(−1, 2) 外の再標本は除外、と実装どおりに。
- §4: Discussion "collective critical point" → "basin boundaries at fixed capacity; the fold in
  capacity itself remains a theoretical prediction"。Abstract "fixed by" → "largely set by"。
  末尾 "decide the collective's fate" → 残差(0.05–0.17、arm B claim 1569)を伴う "account
  for most of what the collectives did"。
- S1 rewiring の限定を §5.1 にも。S2 claim 1239 の x0 ≤ 0.625 を「正答側確率 ≤ 0.3(平均
  0.00–0.42)」に。S3 最大誤差の帰属(6.0% = h=.7 セット、9.9% = h=.3, θ=2 セット)を本文・
  SI で訂正。S4 SI one-step の文言(arm B に −0.04〜−0.06 の系統的過大予測が残る)。
  S5 ブートストラップ回数を解析別に。S6 否定対を「同じ命題について原文が肯定することを
  言い換えが否定する」に(§5.3・Methods)。S7 70B の場: 8 claim 中 7 が内容整合(|logit|
  3.7–7.2)、90006 は近中立(P(TRUE) = 0.42)と本文・SI に明記。S8 SI ヒストグラム区間を
  [0.45, 0.5](全員一致を含む)に。
- main 20 頁・SI 12 頁、エラー 0、旧図の残存なし(pdftotext で 14/16・0.68 を検索: 0 件)。

## 追記その 25(2026-09-06): 最終確認レビューへの対応

- α* の範囲表記: §4 を「完全写像 F の fold として 0.43–0.48(定数 0.43、divisive 0.48、識別済み
  per-k 0.46)、変種 B は 0.47 対 1.28」に統一し、SI §3 に「本文は F の fold、登録値 0.435 は
  exact E[K] の G-fold」を明記。
- fold と感受率: 「not a critical point with a diverging susceptibility」を「saddle-node
  bifurcation of the mean-field map, corresponding to the disappearance of a metastable basin
  (a spinodal)」に(∂x*/∂h = G_h/(1−G_x) は fold で発散するため)。
- 選定時の解析と掲載予測の区別: §5.4 と Methods に「選定は当時の分類に規則を適用、掲載予測は
  Methods の推定法で再計算、選定 8 claim の分類は 16 セル中 15 で不変」を追記。"unchanged
  pipeline" → "the same pipeline"。
- 70B の場: 有限 logit(−3.7〜−5.8)の記載を外し、空 inbox の観測率(原文 4 件 0.000、言い換え
  3 件 1.000、90006 は 0.42)で記述(本文・SI)。
- SI 目次: 3 回コンパイルで収束(Section 1 = p.2)。Fig. 7: 縦軸を −0.10 まで拡張し 1146 の区間を
  全表示(scripts/54)。ブートストラップ: 500 反復、(−1, 2) 外の除外後の残存率(17 セル中 12 で
  全残存、3 セルで 97–99%、656@0.55 89%、1146@0.55 65%)を Methods に記載。予測側区間は
  claim 内・design cell 内の再標本化であり claim クラスタ bootstrap と別と明記。
- main 20 頁・SI 12 頁、エラー 0。

## 追記その 26(2026-09-06): 通読レビュー(A–E、本人承認)

- Abstract: 50% の分母(of episodes)を明示、"the field" → "the claim-induced field"(タイトル語)、
  語数調整("bounded by cognition, context, or cost"、"after r acceptances"、"as crowding
  parameter α"、"only 28–45% from 75%-correct majorities"、"reproduce the outcomes"、
  "matched in 15 of 16")。TeX 換算 247 語 / 1,621 字、フォーム換算(α* = 0.435 を 3 語)249 語。
- §1 "frozen prediction" → "pre-registered prediction"。§2.2 q(x0) の継承文を有限時間の定義に
  合わせて修正、divisive を "one of the two attenuation forms our data support" に。§4 の
  α* 範囲に登録値 0.435(reduced map)を併記、量子化表記の括弧入れ子解消、"16/17" →
  "Sixteen of the 17"、"uniformly more persuasive" → "more persuasive on average (1.44
  [1.25, 1.65])"、θ の解釈をヘッジ("consistent with")。
- §5.2 末尾 "in every cell tested" → "in the main arm"。§5.3 "key case" 削除。§5.4 "sharper"
  削除、"closes the picture" → "completes the comparison"、三モデルの範囲を限定(集団は 2 モデル、
  第三は極性チャネルのみ)。Fig. 4 題を記述的に。
- Discussion "verified localization" → "replay-based localization"、人間段落 "the theory says"
  → "would say"、ダッシュ二重挿入 4 箇所をコンマ句・コロン・括弧に。Methods 忠実性チェックに
  数値(1.00 対 0.875、0.44 対 0.38)。
- main 20 頁、エラー 0。
