# Stage 2b A-2 言い換え 4 対の承認要求（v1）

日付: 2026-08-25。状態: **承認待ち**。
承認方法: `notes/APPROVAL_RESPONSE_stage2b.md` に `approved` と書く（または端末で直接指示）。
修正する場合: 同ファイルに修正後の文言を書く → 同値判定をやり直し、本ファイルを v2 に更新して再度承認を待つ。

## 言い換え 4 対（論理内容を保ち肯定の向きだけ反転）

原クレームは全て REFUTES（内容が誤り）なので、言い換え版では**正答側 = クレーム肯定側 = TRUE** になる。

### 対 1（原 claim_id 6 → 新 90006）
- 原文: The polar bear population has been growing.
- 言い換え: **The polar bear population has not been growing.**
- 方式: 単純否定挿入。モデルの対立判定: 20 回中 70% が「逆を主張」と判定。

### 対 2（原 claim_id 1569 → 新 91569）
- 原文: Sea level rise is decelerating.
- 言い換え: **Sea level rise is not decelerating.**
- 方式: 単純否定挿入（指示書の例と同型）。対立判定: 85%。

### 対 3（原 claim_id 382 → 新 90382）
- 原文: The amount of energy used to construct solar and wind facilities is greater than they produce in their working lives.
- 言い換え: **The amount of energy used to construct solar and wind facilities is not greater than they produce in their working lives.**
- 方式: 単純否定挿入。対立判定: 70%。

### 対 4（原 claim_id 2070 → 新 92070）
- 原文: When life is considered, ocean acidification is often found to be a non-problem, or even a benefit.
- 言い換え: **When life is considered, ocean acidification is often found to be a problem, and not a benefit.**
- 方式: 直訳否定は「not … non-problem」の二重否定になるため De Morgan 等値変形
  ¬(非問題 ∨ 利益) = (問題 ∧ ¬利益)。対立判定: 85%。

## 参考（承認判断の材料）

- 言い換え版の裸較正 p_q（64 回、TRUE = 正答側）: 90006 → 0.344、91569 → 0.938、
  90382 → 0.938、92070 → 1.000。3 件は場が正答側へ大きく傾く（均衡クレームの否定は
  均衡に留まらない）。これは設計上避けられない性質として結果解釈時に考慮する。
- 92070 はミニ単体測定で分離気味（ほぼ常に TRUE 回答）。集団実験は可能だが
  変動がほぼ見えない天井ケースになる見込み。
