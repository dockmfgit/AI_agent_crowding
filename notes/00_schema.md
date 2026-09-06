# El et al. (arXiv:2608.16578) 公開データ スキーマ確認

日付: 2026-08-22。データ取得元:

- GitHub: `github.com/batu-el/physics-of-agents` → `external/physics-of-agents/` に clone。
  **生データ（全メッセージ本文込み）はリポジトリ内 `data/models/` に直接格納されている**（モデルごと 712–923 MB）。
- HuggingFace: org `physics-of-agents` には 2 データセットのみ:
  - `physics-of-agents/agent-opinions` — `lib/clean_data.ipynb` が `data/models/` の全ファイルを**無フィルタで**結合して push したもの（列: model, mode, statement, J, spins_history, spins_raw_history, replica, ground_truth, political_lean）。**qid・graph_id・メッセージ本文は落ちている**ため、本解析では GitHub の生 JSON を直接使う。
  - `physics-of-agents/agent-opinions-async` — 非同期実験（今回対象外）。

## ファイル単位

1 JSON ファイル = 1 集団（= 1 エピソード）: `data/models/{model_dir}/objective_energy/{qid}__{graph}__rep{r}.json`

- `model_dir` ∈ {gpt-4o-mini, gemma-3n-e4b-it, qwen3.5-9b, meta-llama-3-8b-instruct}。
  注意: ディレクトリ名は `meta-llama-3-8b-instruct` だが `res/utils.py` の MODELS では
  `meta-llama/Llama-3.1-8B-Instruct`（表示名 "Llama-3-8B"）。ユーザ指定の llama-3.1-8b-instruct に対応。
- `qid` = `math_{train|test}_{id}`。客観問題は全 40 問（train 20 + test 20）。
- `graph` ∈ {J0..J7, Jf0..Jf3, square, triangular}。1 問あたり 10 グラフ:
  - train 問: J0–J7 + square + triangular
  - test 問: J0–J3（seen）+ Jf0–Jf3（fresh）+ square + triangular
  - **「低ランク 6」というグラフ族はこのデータセットには存在しない**（`lib/datagen/graph.py` にはランダム対称グラフと格子のみ）。graph family は random（J*/Jf*, 計 12 個の符号付きランダムグラフ）/ square / triangular の 3 族とする。
- `rep` ∈ {00..03} = エピソード（trajectories=4）。

行数照合: 1 モデル 1,600 ファイル × 4 モデル = **6,400 集団 = 4 モデル × 40 問 × 10 グラフ × 4 エピソード**（論文の数字と一致）。

## ファイル内スキーマ

- `meta`: num_agents=32, num_steps=8, k=5（thermal resamples）, temperature=0.7, num_edges=112, seed=0 など。
- `statement`: 問題文。`choices`: {"A": …, "B": …}。
- `J`: 32×32 対称、値 ∈ {−1,0,+1}。
  - ランダムグラフ（J*/Jf*): 符号付き（負エッジ約半分）、次数 |J| 行和は 0〜9 に分布。
  - square: 4×8 非周期格子、正エッジのみ、次数 2〜4。triangular: 次数 2〜6。
    → **格子でも P(k) は δ 関数ではない**（非周期境界のため角・辺で次数が下がる）。
- `spins_history`: 長さ 9（t=0..8）× 32。各要素 ∈ {−1,+1}（まれに 0 = パース失敗）。
  k=5 サンプルの**多数決**（同点は第 1 サンプル）。
- `spins_raw_history`: 長さ 9 × 32 × 5。生サンプル ∈ {−1,+1}（0 = パース失敗）。
  **ō_i(t) = spins_raw_history[t][i] の平均**（`res/utils.py` の `opinions()` と同じ）。値域 {−1,−0.6,−0.2,+0.2,+0.6,+1}（0 混入時はその限りでない）。
- `messages_history`: 長さ 8。各要素は dict `"i,j" → メッセージ本文（全文）`。B.5 の「完全なログ公開」は確認（メッセージ本文はリポジトリ生 JSON にのみ含まれ、HF データセットには含まれない）。

## 正解ラベル

- spin 符号: **A → +1, B → −1**（`lib/datagen/samplers.py` `_parse_spin_objective`）。
- `data/obj/{train,test}.jsonl` の `answer` ∈ {A,B} が正解。y_gt = +1 (A) / −1 (B)
  （`res/utils.py` `load_data`: `truth = {"A":1,"B":-1}[answer]`）。

## 結合定数（res/couplings.json、objective）

五結合（Table 3 相当）と β⁺_T/β⁺_F 比:

| model | β⁺_T | β⁺_F | β⁻_T | β⁻_F | β₀ | w_T = β⁺_T/β⁺_F |
|---|---|---|---|---|---|---|
| gpt | 2.294 | 1.979 | 0.702 | 0.848 | 0.928 | 1.159 |
| gma | 0.342 | 0.200 | 0.169 | 0.364 | 0.965 | 1.712 |
| qwn | 1.028 | 0.772 | 0.402 | 0.798 | 1.007 | 1.332 |
| lma | 1.152 | 0.837 | 0.590 | 0.606 | 0.974 | 1.377 |

ユーザ指定（GPT 1.16, Gemma 1.70, Qwen 1.34, Llama 1.37）と一致。

三結合（rollout 診断に使用）: `w = [field(16) | β⁺, β⁻, β₀]`、
更新則 u_i = φ_i·w_field + β⁺(J⁺s)_i + β⁻(J⁻s)_i + β₀(|J|s)_i、
P(s_i(t+1)=+1) = σ(u_i)（`res/utils.py` `discrete_rollout`, k=3）。
field は persona 埋め込み PCA3 × 問題埋め込み PCA3 の [bias|p|q|p⊗q]（`static_field`）。

## 注意点（解析に効く制約）

- ランダムグラフの負エッジ: HMF 閾値モデル（全入力が引力と仮定）はランダム族では
  グラフの符号構造を無視することになる。仕様どおり k_i = Σ_j |J_ij| で P(k) を作るが、
  この近似の粗さは findings に記録する。
- x0 は高エントロピー問題選定のため 0.5 付近に集中している見込み（実測は手順 3 で確認）。
