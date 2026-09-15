# arXiv v2 draft: readability revision of the main text (2026-09-12)

Scope: main text only (abstract through Methods). The SI, figures, tables,
references and every reported number are unchanged. Verified programmatically:
the set of numbers appearing in the main text before and after the revision is
identical (none lost, none added); the SI part of `main.tex` is unchanged apart from
the new glossary section S1 and the resulting renumbering.

Readability metrics (main text, glossary excluded):
- mean sentence length 37.6 -> 33.3 words; median 33 -> 30
- sentences over 60 words: 23 -> 11 (the remaining ones are enumerations of numbers)
- double-dash parentheticals: 44 -> 0
- word count (detex): 8,759 -> about 9,600 (Introduction +250, plain-language topic
  sentences and the Conclusion for the rest; the glossary sits in the SI)
- PDF: 36 pages (main text 21, SI from p. 22); 0 errors, 0 overfull lines

## Rhythm pass (2026-09-14): the author's four-beat paragraph
- Sections 2-4, Discussion and Conclusion rewritten sentence by sentence on the style extracted from
  Fukushima 2014 (J Neurosci), 2015 (RSOS) and 2015 (Sci Rep): purpose/question first with the actor
  named, method in brief, result with numbers (one comparison per sentence), interpretive closer
  ("This shows/suggests ...", "Thus, ..."); transitions announced; alternatives raised and dismissed in
  place; declarative Results subsection headings (4.2 "The pre-registered prediction fails", 4.3 "The
  failure traces to the threshold, not to the message weights", 4.4 "The discrimination arm favors
  the normalized rule but does not reject the constant one", 4.5 "The field follows the assertion, not
  the truth ..."); the Discussion opens with a past-tense recap of what was done and found.
- Introduction, Methods, captions and SI unchanged. Numbers and citations verified identical.
- Main text (Intro-Conclusion, captions excluded): median sentence length 32 -> 24 words; sentences over
  40 words 30% -> 11%; sentences opening with We/This/Thus per 200: 7/5/1 -> 10/8/6 (the three papers:
  12-20 / 10-22 / 6-12). 38 pages.
- Style profile: style_profile_fukushima_2014-2015.md (also proposed as an addition to the
  fukushima-writing skill).

## Terminology pass (2026-09-14)
- The field h is now described in the binary-neuron vocabulary as the unit's threshold with its
  sign reversed (defined in Section 2.2 with the sign convention and the gain/threshold split);
  the metaphor "tilt" is gone (18 occurrences).
- "threshold" for the collective's transition point (about 25 occurrences) is now "transition
  point" throughout the main text (title term); the outcome cutoff and the 20% level are
  "criterion"; K* is the "critical degree"; "hard-threshold unit" (the step unit) is kept.
- SI text and tables keep "threshold" for the transition point; a sentence in the SI preface
  says so. Glossary entries updated (Field h (threshold); transition point synonyms; outcome
  criterion).
- Overleaf edits by the author merged: the reanalysis is now Section 3.1 of "Measuring the
  response function of the experimental agent" (3.2 The experimental agent); roadmap and
  Section 2.2 pointers updated; SI literal section numbers updated (3, 4.2, 4.2-4.4);
  Conclusion "equivalent to a stochastic binary neuron".
- Abstract 300 words / 1,856 characters; Significance 119 words; 37 pages.

## Changed passages

### Abstract (rewritten, same content; 292 words / 1,803 characters, arXiv limit 1,920)
- Fourth pass: the message capacity is described by what it does (no alpha symbol, no acceptance
  formula, no alpha* value); the transition point is given in messages ("fewer than 6.4 of their
  31 sources"); the network is said to be generated from the capacity.
- "basin" defined at first use ("the set of starting states that end in wrong consensus (its basin)").
- The acceptance rule is explained in words ("so larger alpha means fewer messages read").
- Numbers anchored: "6.4 of 31 sources read"; "the correct side won in fewer than 50% of
  episodes from every start, and in only 28-45% when 75% of agents started correct".
- "we found that" and "effectively" retained; final sentence begins "Thus".
- Note: exceeds the journal's 250-word cap; a 250-word cut can be derived for a journal revision.

### Significance statement (rewritten, 120 words)
- "reduced map" -> "one equation"; "divisively normalized inputs" -> "each message counting
  less as the inbox grows".

### Introduction (rewritten; approved text)
- Order: the problem (reading bound; wrong consensus from a correct majority) -> two
  ingredients (crowding parameter turns the bound into a network; the measured agent is a
  stochastic binary neuron) -> the quantitative question and precedents -> the two design
  confounds -> human relevance -> roadmap.
- Third pass: the Introduction now states only the problem, the two ingredients, the question,
  the design, the human relevance and the organization; no result of the paper is stated in it
  (the "as shown below" sentence, the measured-form sentences, the reanalysis result and the
  roadmap summary of findings were removed or reframed).
- Second pass (scientific-writing checklist): section pointers now appear only in the roadmap
  paragraph; the binary-neuron paragraph states the modelling choice and its justification without
  a pointer; committor glossed in words; roadmap shortened to organization plus a two-sentence
  summary.
- New glossary of 17 terms, placed in the SI as its first section (S1, Table S1) with a pointer
  sentence at the end of the Introduction; the former SI sections S1-S10 are now S2-S11 and the
  main-text references were renumbered accordingly (S2 reanalysis, S10 fidelity check, S11
  Extended Methods).

### Section 2 Theory
- New opening sentence naming the two ingredients and the question of 2.3.
- 2.2: a plain paragraph before the map ("In words, the population dynamics is a map that
  takes the fraction x ... A fixed point ... a stable fixed point is a consensus, an unstable
  one ... is the transition point").
- 2.3: a plain sentence on what a fold is before the formal definition.
- Long sentences split (construction / outcome observable; closure accuracy / worst cases).

### Section 4 Single-agent measurement
- New opening sentence ("A theory needs the agent's rule measured rather than assumed; this
  section is that measurement").
- The 250-word "three measured facts" paragraph split into three paragraphs (coefficients,
  load attenuation, prediction), each opening with the finding in words.
- "did not transfer ... which is why" sentence split.

### Section 5 Collective experiment
- 5.1 Design split into four paragraphs: protocol; the two arms; the three accompanying
  analyses (rewiring control, yoked one-step replay, surrogate rollout); decision criteria.
- 5.2 Results: plain-language sentence added after "The diagnosis localizes the failure to
  the wording-induced field" ("In plain terms, the message weights measured on the
  calibration claims were right, but the tilt of the four experimental claims was not what
  the calibration set implied"); horizon sentence split; parenthetical dash removed.
- 5.3: the negated-rewrite design sentence split into three; "follow the assertion, not the
  truth" sentence split from its consequence.
- 5.4 retitled "A second model shows predicted transition points; a third lacks the
  assertion bias"; four long sentences split (pipeline description; the twelve-cell
  summary; the eight-claim campaign; the 70B paragraph).

### Discussion
- New opening paragraph beginning "The reading bound does not decide a collective's fate on
  its own. Across three models it did so together with one more single-agent quantity."
- "What the collectives verified" restated in three labeled parts (verified / predicted and
  not observed / observed as capacity dependence).
- All dash parentheticals converted to commas, colons or sentence breaks (paragraphs on
  alpha outside the experiment; dialogue and error; polarity origin; human groups and
  limitations; relation to El et al.).
- The residual paragraph now opens "One residual remains to be explained" and closes the
  Discussion.
- New unnumbered section "Conclusion" (the practical rule and the residual summary moved
  here verbatim; final sentence begins "Thus").

### Methods
- Unchanged apart from the earlier shortening (no dash constructions remained).

## Not changed on purpose
- Every number, interval, claim and hedge; figure captions; the SI; the reference list.
- Terminology already settled in the journal version (field, tilt, assertion bias,
  transition point) is kept; the glossary maps the remaining synonyms to these.

## 2026-09-15: two content revisions (author request)
- Introduction, first paragraph: the cognitive bound now cites working-memory capacity (Cowan 2001; Luck & Vogel 1997) and selective attention (Cherry 1953 cocktail-party effect; Treisman 1964 attenuation) before Hodas & Lerman 2012. Three references added to refs.bib.
- Discussion, "Dialogue does not correct error" paragraph: the Taniguchi et al. (2025) clause no longer implies that their framework proposes communication as a remedy; it now states the boundary condition on decentralized-Bayesian accounts and quotes their own caveat that the framework does not guarantee convergence to truth.
- 38 pages, 0 errors; numbers unchanged; citations added: Cherry1953, LuckVogel1997, Treisman1964.
- Follow-up: the Taniguchi sentence now uses a parenthetical citation ("The framework itself does not guarantee convergence to the truth (Taniguchi et al., 2025); the present result gives one measurable condition under which convergence fails."). No \citet remains in the body.
- 2026-09-15 (later): Taniguchi paragraph shortened to three sentences with a single citation. Three stale literal pointers in the SI corrected (S4: "main text Section 4" -> 3.2, twice; S5: "Section 4.2" -> 4.4). 38 pages, 0 errors, numbers unchanged.
