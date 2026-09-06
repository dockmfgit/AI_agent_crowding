# 原稿ビルド指示(GX10 / Claude Code 用)v1.0 — arXiv 投稿版の一括組み立て

作成: 2026-08-27。前提: `manuscript/01_draft.md`(v0.3)が科学的内容の確定版。
**本作業では科学的な主張・数値を一切変更しない。** 作業は組版・図・Methods/SI の
組み立て・文献・数値照合のみ。LLM 呼び出しは不要。読む順: `manuscript/00_outline.md`
→ `01_draft.md` → `notes/12` → `notes/14`(数値の出典として全 notes を参照)。

## 0. 成果物とレイアウト

```
manuscript/tex/
  main.tex        # 本文(article class、単段組、arXiv 向け)
  si.tex          # Supplementary Information
  refs.bib
  figs/           # PDF(ベクタ)+ PNG(300dpi)の両方
manuscript/main.pdf, si.pdf      # コンパイル済み
notes/15_manuscript_build.md     # ビルド記録・数値照合表・[USER] 項目一覧
```

LaTeX 環境がなければ texlive を導入してよい(導入内容を記録)。コンパイル不能なら
.tex 完成 + エラーの記録まで。

## 1. 本文(main.tex)

- `01_draft.md` v0.3 を忠実に LaTeX 化する。文言の編集は文法・体裁の最小限のみ。
  節構成・主張文・数値は不変。
- 用語規約の継承: "attention" は §1 の区別文 1 箇所のみ。correct-side/wrong-side。
  α = crowding parameter。
- タイトルは現行(Input crowding and the tipping point of collective truth-finding
  in networks of language-model agents)を仮置きし、著者名は
  `Makoto Fukushima\thanks{[USER: affiliation]}` とする。
- 図の参照(Fig. 1–6)を §2 の指定に合わせて挿入。
- Abstract は draft の Abstract を 250 語以内に圧縮(削除のみで圧縮し、
  数値は落とさない。圧縮版と原文の両方を notes/15 に記録)。

## 2. 図(6 点、様式統一)

共通様式: 青 #2E6FB7 / 赤橙 #C8442C の 2 色を基調(3 色目が必要な場合は
グレー #8a8a8a)、直接ラベル、フォント統一、両テーマで判読可能な明背景、
PDF + 300dpi PNG。既存 fig/ の素材は下敷きにしてよいが全図を再生成する。

1. **Fig 1 — 枠組み**: (a) 受容過程 e^{−αr} と P_{α,N}(k)(α 3 水準の分布)、
   (b) 測定 → 縮約 → HMF → 集団予測のパイプライン模式(簡潔なブロック図で可)。
2. **Fig 2 — 理論**: (a) 分岐図(fig/xc_vs_alpha_logistic.png の再生成、4 パラメータ組)、
   (b) α\* 閉形式の検証散布(fig/alpha_star_analytic_validation.png の再生成)。
3. **Fig 3 — 単体測定**: (a) β_T(k), β_F(k) と減衰モデル比較(stage1_beta_vs_k の再生成
   + CV 表の要点)、(b) 変法 A/B の係数(CI つき)。
4. **Fig 4 — 集団第一波**: committor 族(α 6 水準)+ 修正入力予測の重ね描き
   (プール予測の失敗と修正予測の一致が一目でわかる構成)+ アーム B のアトラクタ
   位置(予測 0.067/0.093 vs 観測)。
5. **Fig 5 — 極性判別**: 原クレーム vs 否定形言い換えの平均 x₈ 対比(対ごとの矢印
   または対比バー)+ SUPPORTS 3 件。事前登録表の判定が視覚で追える構成。
6. **Fig 6 — モデル一般性**: (a) qwen の観測 x̄₈ ヒートマップ(クレーム × α × x₀)に
   凍結予測の不安定固定点を重ねる(claim 6 と 1239 の閾値一致が主役)、
   (b) 極性比のモデル比較(1.44 / — / 1.03)。

## 3. Methods(main.tex 末尾または si.tex 冒頭)

notes から機械的に組み立てる。必須項目:

- モデルとサービング: llama3.1:8b (Q4_K_M), qwen3:8b (タグ 500a1f067a9f, think:false),
  llama3.3:70b。ollama、温度 0.7、seed 全記録、並列設定の変更履歴(notes/07 §0、
  notes/13 D-2 の運用記録)。
- プロンプト全文: Stage 1 足場(判定・メッセージ生成)、変法 A/B、El et al. 形式の
  踏襲と相違点(ラベルなし有向グラフ、TRUE/FALSE 本文明示)。scripts/stage1_lib.py・
  scripts/20 系から逐語で抽出。
- クレーム: CLIMATE-FEVER、較正手順(二段階、A/B 割付ランダム化)、選定基準、
  全クレーム本文と言い換え 4 対(si へ)。
- ネットワーク生成・エピソード手順・外生割付(stage2 指示書 §3 から)。
- 統計: クレーム単位 wild/pairs bootstrap、5-fold CV(クレーム分割)、
  per-k フィット、fold 条件の数値解法。
- 事前登録の時系列表: 何をいつ凍結したか(予測ファイルの mtime と notes の日付から。
  α\* 予測 → Stage 2、三仮説表 → Stage 2b、qwen 盲予測 → D-1 の 3 件)。
- データ・コード可用性: リポジトリ一式の manifest(scripts/, results/, notes/,
  data の公開可能部分とサイズ。El et al. データは再配布せず出典リンクとする)。
  実際の公開リポジトリ作成は本作業では行わない。

## 4. SI(si.tex)

- 全数値表: Stage 0.5 の再解析要約(内生性の分散分解、w_T クラスタ CI)、Stage 1 係数表
  (クラスタ CI)、減衰モデル比較表、α\* 検証表(11 組)、Stage 2 committor 全表、
  アーム B、ρ、一段較正、Stage 2b A-1/A-2 全表、qwen 凍結予測 vs 観測の全表、
  70B 係数、E ブロック(メッセージ統計・再投入プローブ・反復曝露・有限時間・
  ラベル残差・不応係数・分岐比・非同期カスケード)。
- 外れの一覧(1103@0.55、qwen-1569、91569@0.30 部分)を独立の表として明示。
- 言い換え 4 対と同値判定率、SUPPORTS 3 件の本文。

## 5. 文献(refs.bib)

本文が言及するもののみ。ネット検索で書誌を確認して正確に(確認できた URL を
notes/15 に記録):

- El et al. 2026 (arXiv:2608.16578)
- synaptic crowding 論文(著者本人の Sci Rep)→ **[USER: 正確な書誌]** の
  プレースホルダにする(勝手に推定しない)
- CLIMATE-FEVER (Diggelmann et al.)
- Carandini & Heeger, Normalization as a canonical neural computation
- Taniguchi et al., CPC-MS (RSOS 2025 / arXiv:2409.00102)
- Marzo et al.(合意のサイズ制限)、Science Advances の LLM 集団規範論文
  (Ashery et al. adu9368)など、draft が触れている先行研究
- Lost in the Middle (Liu et al.) は §6 で触れる場合のみ

## 6. 数値照合(必須・最重要)

main.tex / si.tex 中の**すべての数値**について、「本文の値 → 出典ファイル → 出典値」の
三列照合表を作り notes/15 に載せる(例: "α\*=0.435 → results/stage1_alpha_star.csv
→ 0.425–0.468 の変法 A" のように)。照合不能・丸め以外の不一致が 1 件でもあれば
本文を直すのではなく notes/15 に不一致として列挙し、ビルドは完了させる
(科学的数値の変更はユーザ判断)。

## 7. [USER] 項目(notes/15 冒頭に一覧化)

- タイトル最終確定(候補 3 案を再掲)
- so-what 一文(00_outline の候補 a–f を再掲。本文には入れず注記のみ)
- 所属・謝辞・資金情報
- synaptic crowding 論文の正確な書誌
- 公開リポジトリの場所と範囲

## 8. 禁止事項

- 科学的な主張・数値・節構成の変更。新しい解析の実行。
- 文献の創作(書誌が確認できないものは [unverified] を付けて notes/15 に報告)。
- `external/` の変更。既存 results/ の変更(図の再生成は figs/ に出力)。
