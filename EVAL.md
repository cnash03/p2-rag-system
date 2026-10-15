# Evaluation report

This is the report on what you built and what the numbers let you claim.
Two kinds of text live here.

The tables between a `p2:begin` comment line and its matching `p2:end` comment line are written by `uv run p2 score` from your committed run files and answers files.
Please do not edit anything between those two lines, because `uv run p2 check` recomputes them and fails when they differ.
A table that says no runs or answers exist yet is waiting for data; run `uv run p2 score` after you commit the files it needs.

Everything else is yours.
Each prompt ends with a marker line that you replace with your own writing; `uv run p2 check --final` fails while one is left.
Write what you measured, including what did not work.
What I read for is whether each claim matches its interval, not whether the result is good news.

Words used below: recall@10, MRR@10 and nDCG@10 are the three scores, each averaged over the queries of a set; step 7 of stage 1 in the README defines them, and lecture 14 goes deeper.
A paired interval is the 95% interval of the mean difference between two systems on the same queries, found by resampling the queries 10,000 times.
When an interval includes zero, the gold set cannot tell the two systems apart, and the right words are "not distinguishable on this gold set".
The minimum detectable difference is the smallest gap this many queries could reliably show, so a difference below it is invisible to this gold set, not absent.

---

## 1. Stage 1 - the shared corpus (30 CFR Chapter I)

### What you built

For each of `dense`, `hybrid` and `rerank`, one or two sentences: the embedding model, how documents were chunked, what was fused and how, how many candidates the reranker saw, and anything you changed from the 12 and 13 lab code.

**`dense`** embeds 300-word chunks with bge-small-en-v1.5 and ranks them by cosine similarity, which is a plain dot product because the vectors are unit length. Encoding the corpus's 3,132 chunks took 1.9 minutes once and is cached (3,127 distinct chunk texts, since the vector cache is keyed by text hash). I chose bge
over potion-retrieval-32M because bge reads each word in context while potion averages static token vectors, and context is what a paraphrase query needs. Measuring potion directly confirmed this: with it, `hybrid` fell to 0.522 MRR@10 and
paraphrase MRR@10 to 0.143. One change from the lab code: `dense` snaps near-equal scores. Walking the scores from best to worst, any score within 10⁻⁴ of its group's leader takes the leader's score. bge runs through ONNX, whose kernels
differ between my ARM Mac and CI's x86 Linux by about 3×10⁻⁶, and 30 CFR writes many rules several times, so near-duplicate sections sit inside that noise and could swap order between machines. 10⁻⁴ is above that noise, so duplicates tie, and
below `p2/check.py`'s SCORE_TOLERANCE of 10⁻³, so a flip at the boundary is forgiven.

**`hybrid`** fuses `bm25` and `dense` with reciprocal rank fusion, with two departures from the lab. First, rrf_k = 1 instead of 60: at 60 it scored 0.471 MRR@10, worse than either arm alone, because 1/61 and 1/70 differ by only 13%, so the fused
top 10 filled with documents both arms ranked moderately and dropped the ones a single arm ranked first. Second, it fuses each arm's top 10 rather than all 2,484 documents, which the stub warns against. It scored better this way (0.693 vs 0.668 MRR@10),
because at rrf_k = 1 a document ranked 11th by both arms scores 1/12 + 1/12 = 0.167 and would displace one that a single arm ranked 5th.

**`rerank`** sends `hybrid`'s top 20 to Claude for listwise reordering. The reply schema is bounded to positions 1–20 so an out-of-range reply cannot pass silently, and any malformed reply falls back to the first-stage order; I tested that fallback
offline against 8 malformed replies. Each call uses about 16,400 input tokens on the practice queries and 15,400 on the test queries, about 942,666 for all 60.

### Practice queries (20)

Scores per system.

<!-- p2:begin shared-practice -->
| System | Recall@10 | MRR@10 | nDCG@10 |
| --- | ---: | ---: | ---: |
| bm25 | 0.625 | 0.507 | 0.518 |
| dense | 0.558 | 0.562 | 0.480 |
| hybrid | 0.817 | 0.693 | 0.649 |
| rerank | 0.783 | 0.850 | 0.789 |

20 judged queries; nDCG uses binary labels; a random ranking of the 2,484 documents would get recall@10 near 0.004.
<!-- p2:end shared-practice -->

The same scores per query class.

<!-- p2:begin shared-practice-classes -->
| System | Metric | identifier (n=7) | paraphrase (n=7) | mixed (n=6) |
| --- | --- | ---: | ---: | ---: |
| bm25 | Recall@10 | 1.000 | 0.000 | 0.917 |
| bm25 | MRR@10 | 0.810 | 0.000 | 0.746 |
| bm25 | nDCG@10 | 0.857 | 0.000 | 0.728 |
| dense | Recall@10 | 0.214 | 0.595 | 0.917 |
| dense | MRR@10 | 0.333 | 0.714 | 0.653 |
| dense | nDCG@10 | 0.211 | 0.593 | 0.661 |
| hybrid | Recall@10 | 1.000 | 0.548 | 0.917 |
| hybrid | MRR@10 | 0.695 | 0.643 | 0.750 |
| hybrid | nDCG@10 | 0.720 | 0.497 | 0.746 |
| rerank | Recall@10 | 0.857 | 0.595 | 0.917 |
| rerank | MRR@10 | 0.857 | 0.714 | 1.000 |
| rerank | nDCG@10 | 0.828 | 0.626 | 0.936 |
<!-- p2:end shared-practice-classes -->

Differences between every pair of systems, each with its paired interval and the minimum detectable difference.

<!-- p2:begin shared-practice-pairs -->
| Comparison | Metric | Mean difference | 95% interval | MDD | Reading |
| --- | --- | ---: | ---: | ---: | --- |
| dense minus bm25 | Recall@10 | -0.067 | [-0.350, +0.225] | 0.415 | not distinguishable |
| dense minus bm25 | MRR@10 | +0.055 | [-0.225, +0.343] | 0.412 | not distinguishable |
| dense minus bm25 | nDCG@10 | -0.039 | [-0.302, +0.231] | 0.385 | not distinguishable |
| hybrid minus bm25 | Recall@10 | +0.192 | [+0.050, +0.358] | 0.223 | hybrid higher |
| hybrid minus bm25 | MRR@10 | +0.186 | [+0.008, +0.390] | 0.283 | hybrid higher |
| hybrid minus bm25 | nDCG@10 | +0.131 | [-0.008, +0.290] | 0.219 | not distinguishable |
| hybrid minus dense | Recall@10 | +0.258 | [+0.083, +0.450] | 0.270 | hybrid higher |
| hybrid minus dense | MRR@10 | +0.131 | [-0.008, +0.289] | 0.215 | not distinguishable |
| hybrid minus dense | nDCG@10 | +0.170 | [+0.034, +0.318] | 0.204 | hybrid higher |
| rerank minus bm25 | Recall@10 | +0.158 | [-0.042, +0.358] | 0.294 | not distinguishable |
| rerank minus bm25 | MRR@10 | +0.343 | [+0.100, +0.576] | 0.344 | rerank higher |
| rerank minus bm25 | nDCG@10 | +0.271 | [+0.050, +0.480] | 0.313 | rerank higher |
| rerank minus dense | Recall@10 | +0.225 | [+0.075, +0.400] | 0.238 | rerank higher |
| rerank minus dense | MRR@10 | +0.287 | [+0.117, +0.471] | 0.259 | rerank higher |
| rerank minus dense | nDCG@10 | +0.310 | [+0.157, +0.476] | 0.233 | rerank higher |
| rerank minus hybrid | Recall@10 | -0.033 | [-0.150, +0.050] | 0.150 | not distinguishable |
| rerank minus hybrid | MRR@10 | +0.157 | [-0.029, +0.333] | 0.268 | not distinguishable |
| rerank minus hybrid | nDCG@10 | +0.140 | [-0.018, +0.280] | 0.219 | not distinguishable |

The interval is a paired bootstrap (10,000 resamples of the queries); MDD is the smallest difference this many queries detect 80% of the time.
<!-- p2:end shared-practice-pairs -->

The 40 test queries have no answer key in this repo.
Your test run files are scored by the course and the score comes back to you as feedback, so nothing goes here for them.

### What the intervals let you claim

Which differences are distinguishable from zero and which are not?
What is the minimum detectable difference at 20 queries, and what does that say about any gap smaller than it?
Which claim from lecture 12 or 13 did your numbers support, and which did they leave open?

**Not distinguishable on this gold set.** `dense` against `bm25` on every score; `hybrid` against `bm25` on nDCG@10 and against `dense` on MRR@10;
`rerank` against `bm25` on recall@10; and `rerank` against `hybrid` on every score. The last is the one that matters most: `rerank` is 0.157 ahead on MRR@10 and
0.140 on nDCG@10, at about 16,400 input tokens and 3.9 seconds per query, but both intervals include zero ([−0.029, +0.333] and [−0.018, +0.280]).

**What 20 queries can see.** The minimum detectable difference ranges from 0.150 (`rerank` vs `hybrid`, recall@10) to 0.415 (`dense` vs `bm25`, recall@10), and is above
0.2 for most pairs. Any gap smaller than that is invisible to this gold set, not shown to be absent. `rerank` vs `hybrid` is the clearest case: its observed gaps (0.157
and 0.140) are well below their MDDs (0.268 and 0.219), so the data neither show a gain nor rule one out. `dense` vs `bm25` is the extreme: an MDD of about 0.41 against
a mean MRR@10 gap of 0.055, because the two systems disagree so strongly query by query that 20 queries cannot resolve anything smaller.

**Lecture 12's claim that no retriever wins everywhere** is supported, though descriptively, since the per-class tables have no intervals and only 6–7 queries per
class. `bm25` found a relevant section in the top 10 for all 7 identifier queries and none of the 7 paraphrases, while `dense` reached identifier recall@10 of only 0.214.
`hybrid` kept identifier recall@10 at 1.000 while scoring 0.643 MRR@10 on paraphrases. **Whether `hybrid` beats both of its arms is only partly supported**: it is
distinguishable from both on recall@10, but not from `bm25` on nDCG@10 or from `dense` on MRR@10. **Whether reranking is worth its cost is left open** at this gold-set size.
One more pattern: `rerank` has the best MRR@10 (0.850) but lower recall@10 than `hybrid` (0.783 vs 0.817). It tends to move one relevant section to rank 1 while pushing others
out of the top 10, though that recall difference (−0.033) is itself not distinguishable from zero.

---

## 2. Stage 1 - cited answers on the 12 shared questions

<!-- p2:begin answers -->
| Label | System | Verified (in) | 95% interval | not_found (in) | Declined (out) | 95% interval | Quotes found |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| hybrid | hybrid | 7 of 8 (88%) | [0.529, 0.978] | 1 of 8 (12%) | 4 of 4 (100%) | [0.510, 1.000] | 10 of 10 |
<!-- p2:end answers -->

Which system answered, and why that one?
What did you change in `prompts/answer.txt`, if anything, and did the verified share or the declined share move?

Then read three in-corpus answers that `uv run p2 verify` passed.
For each one, open the cited chunk and say whether the quote really supports the claim next to it.
The check proves a quote is a real piece of the chunk and cannot prove that it supports the claim, so this reading is the part only you can do.

**Which system, and why.** `hybrid` answered. Answering is a recall problem: the right chunk only has to reach the prompt, and all five retrieved
chunks go into it regardless of order, so `rerank`'s ranking advantage is something the answer prompt never uses. `hybrid` also has slightly higher recall@10
(0.817 vs 0.783), and `rerank`'s gains over it were not distinguishable from zero. On cost, the 12 answers took 12 Claude calls and about 104,000 input tokens;
answering from `rerank` would have added a reranking call per question, roughly 230,000 tokens in total.

**The prompt.** I did not change `prompts/answer.txt`, so there is no before-and-after to report. With it as given, 7 of 8 in-corpus questions were verified
(88%, interval [0.529, 0.978]), 1 of 8 came back not_found, all 4 out-of-corpus questions were declined (interval [0.510, 1.000]), and all 10 quotes were found
in the chunks they cite. Both intervals are wide because 8 and 4 questions are very few: 4 of 4 is consistent with a true decline rate as low as about half.

**The one not_found (a06).** The question asked for the noise permissible exposure level. The gold section, cfr30-62.101, did reach the prompt (at chunk rank 4 of 5),
but it is a 632-word Definitions section split into three chunks, and the chunk that was retrieved, #0, holds the action level (85 dBA TWA8), not the answer.
The permissible exposure level (90 dBA) is in chunk #1, which was not retrieved. Chunk #0 outranked #1 because the action-level definition matches the question's
wording almost exactly while being the wrong definition. Claude declined rather than report 85 dBA, which is the grounding working as intended; the failure is in
chunking and retrieval, not in the answer step.

**Three-answer audit.**

The test for each claim: does the quote, read in its cited chunk, establish everything the claim says, or does the claim add something the chunk does not contain?

- **a02**, the minimum incombustible content of combined dust in an underground coal mine where no methane is present.
  - a02-c1: "The incombustible content of the combined coal dust, rock dust, and other dust must be not less than 80 percent (increased only where methane is present)." 
  Quote: "maintained in such quantities that the incombustible content of the combined coal dust, rock dust, and other dust shall be not less than 80 percent." 
  Cited chunk: `cfr30-75.403#0`.
   **Supported.** The quote states the 80 percent minimum, which is the whole answer to a question that rules methane out. The quote stops before the methane condition in the claim's parenthetical, but the next sentence of the same chunk makes the increase conditional on methane, so the chunk supports the parenthetical even though the quote alone does not.
- **a04**, how often an underground metal or nonmetal mine must hold evacuation drills.
  - a04-c1: "Underground metal and nonmetal mines must hold mine evacuation drills at least once every six months." 
  Quote: "At least once every six months, mine evacuation drills shall be held". 
  Cited chunk: `cfr30-57.4361#0`.
   **Supported.** The quote states both the frequency and the requirement; "shall be held" and "must hold" mean the same thing, and the claim adds nothing the quote lacks.
  - a04-c2: "The drills must be held for each shift, at some time other than a shift change, and involve all persons underground." 
  Quote: "Be held for each shift at some time other than a shift change and involve all persons underground;". 
  Cited chunk: `cfr30-57.4361#0`. 
  **Supported.** Each of the claim's three requirements (every shift, not at a shift change, all persons underground) appears in the quote with no added condition. The quote is a list item with no subject of its own; the claim's subject, "the drills", comes from the lead-in to that list in the same chunk, so the claim reads the quote correctly rather than attaching it to something else.
- **a07**, how high berms or guardrails must be on the banks of roadways at metal and nonmetal mines.
  - a07-c1: "Berms or guardrails must be at least mid-axle height of the largest self-propelled mobile equipment that usually travels the roadway (30 CFR 56.9300, surface metal/nonmetal mines)." 
  Quote: "Berms or guardrails shall be at least mid-axle height of the largest self-propelled mobile equipment which usually travels the roadway." 
  Cited chunk: `cfr30-56.9300#0`. 
  **Partly.** The height requirement is word for word in the quote. The parenthetical goes further: "surface metal/nonmetal mines" is in neither the quote nor the chunk, and comes from knowing that Part 56 covers surface mines. The fact is correct, but the citation does not establish it.
  - a07-c2: "The same height requirement appears in 30 CFR 57.9300 (underground metal/nonmetal mines)." 
  Quote: the same sentence as a07-c1. 
  Cited chunk: `cfr30-57.9300#0`. 
  **Partly.** The main claim holds: the identical sentence appears in the 57.9300 chunk, so the citation shows that the same requirement is written there. But "(underground metal/nonmetal mines)" fails the same test as a07-c1, since it is in neither the quote nor the chunk. It is also imprecise: Part 57 covers both the underground and the surface areas of underground mines.


---

## 3. Stage 2 - your corpus and your gold set

### The corpus

What is it, where did it come from, how many documents and how many megabytes, and what is the license basis for publishing it?
Name the one or two documents you were least sure about and what you decided.
Say which of the allowed sources in the brief it comes from.

TODO: describe your corpus and its license basis.

### The gold set

How many queries, how many with origin `hand` and how many with origin `claude`, and which query classes did you use and why?
How did you decide that a document is relevant: write your relevance rule in two or three sentences, the way the brief does for the shared corpus.
How did you find candidates (the systems' top 10, a keyword search, reading), and did you read every document before you labeled it?
Your labels are binary (`rel` 1) unless you say otherwise: if you use graded labels, declare the scale here, for example 2 means the document answers the query fully and 1 means it helps.

TODO: describe your gold set and your relevance rule.

---

## 4. Stage 2 - results on your corpus

Scores per system on your gold set.

<!-- p2:begin own -->
_No scored runs here yet: run `uv run p2 run --corpus own --system bm25` (or `--all`), then `uv run p2 score`._
<!-- p2:end own -->

The same scores per query class.

<!-- p2:begin own-classes -->
_No scored runs here yet: run `uv run p2 run --corpus own --system bm25` (or `--all`), then `uv run p2 score`._
<!-- p2:end own-classes -->

The same scores for the queries you wrote yourself (`hand`) and the ones a model drafted (`claude`), with the difference between the two groups and its interval.
Once both groups have queries, the table also says whether `bm25`'s lead over `dense` differs between them, and what share of each query's content words its best relevant document contains, which is stretch option 6.

<!-- p2:begin own-origins -->
_No scored runs here yet: run `uv run p2 run --corpus own --system bm25` (or `--all`), then `uv run p2 score`._
<!-- p2:end own-origins -->

Differences between every pair of systems.

<!-- p2:begin own-pairs -->
_No scored runs here yet: run `uv run p2 run --corpus own --system bm25` (or `--all`), then `uv run p2 score`._
<!-- p2:end own-pairs -->

Which differences are distinguishable and which are not, at your gold-set size?
Do the `hand` queries and the `claude` queries tell the same story?
Did your prediction in `DECISIONS.md` prompt 1 hold?

TODO: write what your own-corpus intervals let you claim.

---

## 5. The ablation

Change one thing and keep everything else the same.
Write your hypothesis here before you run it, in one sentence with a direction: "I expect X to raise MRR@10 on my corpus because Y."
The run file for it lives in `runs/own/ablation/`.

<!-- p2:begin own-ablation -->
_No ablation runs yet: `uv run p2 run --corpus own --system NAME --ablation` writes one to runs/own/ablation/, then `uv run p2 score` fills this table._
<!-- p2:end own-ablation -->

The queries your ablation helped and hurt, against the system it varies, by reciprocal rank.
`p2 score` finds that system from a line such as `BASE = "bm25"` in your variant's file, or else from its name: `bm25_lab` varies `bm25`.

<!-- p2:begin own-ablation-queries -->
_No ablation runs yet: `uv run p2 run --corpus own --system NAME --ablation` writes one to runs/own/ablation/, then `uv run p2 score` fills this table._
<!-- p2:end own-ablation-queries -->

What did you change, what happened, and does the interval support the claim you want to make?
If the result is not distinguishable, say what size of effect your gold set could have seen.
Read the queries at the top of each list in the second table, and say whether your change explains them.

TODO: write the ablation: the one change, the hypothesis, the result and the claim.

---

## 6. Failure analysis

Pick the queries where your best system on your own corpus failed: the relevant document is missing from the top 10, or sits far below the top.
Take at least five, and read what the system returned next to what was relevant.
Then sort the failures by cause, for example a vocabulary mismatch, near-duplicate documents, a chunk that cut the answer in half, a query that is ambiguous, or a label that was wrong, because sometimes the gold set is what failed.

| qid | what the best system returned | what was relevant | cause | what you would try |
|---|---|---|---|---|

TODO: add one row for each failure you analyzed, and write two or three sentences on the pattern you see across them.

---

## 7. Cross-corpus comparison

The two tables to compare are the shared-corpus scores in section 1 and your own-corpus scores in section 4, with their intervals.
If you want them side by side, copy the rows you need into a table here and say that you copied them.

Did the winner change between the shared corpus and yours?
Why, or why not: what is different about the two collections (document length, vocabulary, identifiers, near-duplicates, how the queries were written), and which of your explanations did you test and which are guesses?
Say what 20 queries on one side and your gold-set size on the other cannot support.

TODO: write the cross-corpus comparison.

---

## 8. Stretch

498E: the stretch is one of the six options in the brief's "One stretch" section, and that section says what earns the 25 points for each.
It is optional, so `uv run p2 check --final` never waits on this section.
598E: the rider is your stretch, so write "rider" below and put its results in section 9; the other options add no points, because the project is capped at 150.

Whichever option you chose, write these five things:

1. The option's name.
2. What you did, and the files that hold it.
3. The table `p2 score` wrote for it, by name: one of the three below, `own-ablation` and `own-ablation-queries` in section 5 for a second ablation, `own-origins` in section 4 for the hand and claude queries, or `repeats` in section 9 for the rider.
4. What its interval lets you claim, and what it does not.
5. One thing you would do next, and what result would tell you it worked.

For a second ablation, write its hypothesis here before you run it, and commit it, so your history shows that it came first.
For the hand and claude queries, do the same with your prediction before you score.

### Claim-level faithfulness check (option 2)

Claude's verdicts from `p2 judge` against your own verdicts in the calibration file.

<!-- p2:begin stretch-judge -->
_No judged answers yet (stretch option 2): `uv run p2 judge answers/shared/LABEL.json` writes them, your own verdicts go in answers/shared/LABEL.calibration.tsv, and then `uv run p2 score` fills this table._
<!-- p2:end stretch-judge -->

### Cost and latency (option 3)

The Claude calls, tokens and seconds in every trace you committed, and what a cheaper system or answers file saves against what it loses.

<!-- p2:begin stretch-cost -->
Every trace in traces/ that records a Claude call:

| Trace | System | Spans | Claude calls | Saved | Input tokens | Output tokens | Seconds | Input per span | Output per span | Seconds per span |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| traces/answers-hybrid.jsonl | hybrid | 12 | 12 | 2 | 103,664 | 3,061 | 52.9 | 8,639 | 255 | 4.4 |
| traces/shared-practice-rerank.jsonl | rerank | 20 | 20 | 0 | 327,780 | 2,266 | 77.1 | 16,389 | 113 | 3.9 |
| traces/shared-practice-rerank.r1.jsonl | rerank | 20 | 20 | 0 | 209,921 | 2,313 | 79.2 | 10,496 | 116 | 4.0 |
| traces/shared-practice-rerank.r2.jsonl | rerank | 20 | 20 | 0 | 182,207 | 2,006 | 73.6 | 9,110 | 100 | 3.7 |
| traces/shared-practice-rerank.r3.jsonl | rerank | 20 | 20 | 0 | 244,753 | 2,300 | 78.8 | 12,238 | 115 | 3.9 |
| traces/shared-test-rerank.jsonl | rerank | 40 | 40 | 0 | 614,886 | 4,416 | 150.6 | 15,372 | 110 | 3.8 |

A span is one query of a run, one question of an answers file, or one claim of a judged file. A saved reply costs nothing now, so it counts the tokens and the seconds of the call that made it.

Every pair of systems on the same queries where at least one calls Claude, the one with fewer Claude input tokens per query first:

| Cheaper minus dearer | Queries | MRR@10 difference | 95% interval | Input tokens saved per query | Seconds saved per query | Reading |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| shared practice: bm25 minus rerank | 20 | -0.343 | [-0.576, -0.100] | 16,389 | 3.9 | rerank higher |
| shared practice: dense minus rerank | 20 | -0.287 | [-0.471, -0.117] | 16,389 | 3.9 | rerank higher |
| shared practice: hybrid minus rerank | 20 | -0.157 | [-0.333, +0.029] | 16,389 | 3.9 | not distinguishable |

The difference is the cheaper system's score minus the dearer one's, with its paired interval; the savings count Claude calls only, so a system that makes none saves all of the other's.

Systems that do not call Claude, from traces/retrieval/ on the machine that last ran `p2 score` (git ignores that folder, so `p2 check` does not compare this part):

| Trace | System | Queries | Seconds | Milliseconds per query |
| --- | --- | ---: | ---: | ---: |
| traces/retrieval/shared-practice-bm25.jsonl | bm25 | 20 | 0.04 | 1.9 |
| traces/retrieval/shared-practice-dense.jsonl | dense | 20 | 0.17 | 8.5 |
| traces/retrieval/shared-practice-hybrid.jsonl | hybrid | 20 | 0.22 | 11.0 |
| traces/retrieval/shared-test-bm25.jsonl | bm25 | 40 | 0.08 | 2.0 |
| traces/retrieval/shared-test-dense.jsonl | dense | 40 | 0.35 | 8.8 |
| traces/retrieval/shared-test-hybrid.jsonl | hybrid | 40 | 0.45 | 11.3 |
<!-- p2:end stretch-cost -->

### The grep agent (option 5)

Your stretch run on some of your own queries against the four systems on the same queries.

<!-- p2:begin stretch-agent -->
_No stretch runs yet (stretch option 5): `uv run p2 run --corpus own --queries eval/own/agent.queries.tsv --system agent --stretch` writes one to runs/own/stretch/, then `uv run p2 score` fills this table._
<!-- p2:end stretch-agent -->

### Your stretch

Write the five things here.

---

## 9. 598E only - repeats and the pre-registered claim

498E students can leave this section as it is; nothing checks it.
598E students replace each line that starts with "598E: write", and `uv run p2 check --final` counts those lines as work still to do until they are gone.

### Repeats on the shared corpus

Three runs of the reranker on the practice queries, and three answers files, with their run-to-run spread and Wilson intervals.

<!-- p2:begin repeats -->
Repeated runs of rerank on shared/practice:

| Run | Recall@10 | MRR@10 | nDCG@10 |
| --- | ---: | ---: | ---: |
| rerank.r1 | 0.783 | 0.850 | 0.796 |
| rerank.r2 | 0.783 | 0.850 | 0.796 |
| rerank.r3 | 0.783 | 0.850 | 0.796 |
| range (max minus min) | 0.000 | 0.000 | 0.000 |

| Comparison | Metric | Mean difference | 95% interval | Reading |
| --- | --- | ---: | ---: | --- |
| rerank.r1 minus hybrid | Recall@10 | -0.033 | [-0.150, +0.050] | not distinguishable |
| rerank.r2 minus hybrid | Recall@10 | -0.033 | [-0.150, +0.050] | not distinguishable |
| rerank.r3 minus hybrid | Recall@10 | -0.033 | [-0.150, +0.050] | not distinguishable |
| rerank.r1 minus hybrid | MRR@10 | +0.157 | [-0.029, +0.333] | not distinguishable |
| rerank.r2 minus hybrid | MRR@10 | +0.157 | [-0.029, +0.333] | not distinguishable |
| rerank.r3 minus hybrid | MRR@10 | +0.157 | [-0.029, +0.333] | not distinguishable |
| rerank.r1 minus hybrid | nDCG@10 | +0.146 | [-0.010, +0.283] | not distinguishable |
| rerank.r2 minus hybrid | nDCG@10 | +0.146 | [-0.010, +0.283] | not distinguishable |
| rerank.r3 minus hybrid | nDCG@10 | +0.146 | [-0.010, +0.283] | not distinguishable |
<!-- p2:end repeats -->

Does the reranker's gain over its first stage survive the run-to-run variation?
Write what the spread is, how it compares with the gain, and what the Wilson intervals on the verified share and the declined share say about 8 and 4 questions.

598E: write the repeats result here.

### The pre-registered claim

The claim, the smallest effect, the gold-set size and the test are in `PREREG.md`, committed before your own gold-set judgments.
Here, say whether you followed the plan, what the interval turned out to be, and what that means.
The outcome section of `PREREG.md` holds the short version.

598E: write the claim and its outcome here.
