# Pre-registration (598E)

This file is for 598E students; it is the second half of the 598E rider, and 498E students can ignore it or delete it.

A pre-registration is a claim you write down, with the test that will judge it, before you can see the answer.
Its value is that the claim can be wrong in a way anyone can check, and that you cannot adjust it afterwards to fit the numbers.
A well-powered result that says "no effect as large as the one I cared about" scores as well as a confirmation, so you have no reason to bend the claim.

**Git history is how I will know the order.**
Commit this file, filled in through section 4, before the first commit that puts a judgment line into `eval/own/qrels.txt` (or any other file under `eval/own/`).
`uv run p2 check` reads `git log` to find the first commit in which sections 1 to 4 have no TODO marker left and some words of yours in each, and confirms that it comes before your first judgment; a copy that was filled in afterwards fails.
Right after that commit, `p2 check` names it and waits for your first judgment; it asks for section 5 separately, once you have scored your own corpus.
You may ingest your corpus and write queries first, but not the relevance judgments.
After that first commit, do not edit sections 1 to 4, because `p2 check` compares them with the commit where you filled them in.
If something must change, add a dated entry in section 6 and leave the original as it was.

You need your stage 1 scores for section 3, so score the shared corpus first.

---

## 1. Hypothesis

One sentence, about your own corpus, naming two of your systems and a direction.
For example: "On my corpus of Kubernetes documentation, `rerank` has a higher MRR@10 than `hybrid`, because the queries are paraphrases that a first-stage fusion ranks too low."
It should be something you could be wrong about.

On my corpus of USGS Mineral Commodity Summaries (2024–2026, 267 chapters), rerank has a higher nDCG@10 than hybrid, because the queries are relevant to the documents and the reranker can better capture the semantic relationships.

---

## 2. The smallest effect that matters

Name one metric, MRR@10 or nDCG@10, and choose it now so you cannot pick the better one afterwards.
Then say how large a difference between the two systems would matter to a person using the search, and why that size.
A difference of 0.02 is usually not worth a reranker's cost in time and tokens.
In this course, choose a Δ of at least 0.15 unless you argue for a larger one, because a smaller gap takes more queries than one project can judge.
Call your number Δ (delta).

Metric: nDCG@10. Δ = 0.15.

A reranker adds a second model call and extra latency to every query, so it only earns its place if users see clearly better top results. To make 0.15 concrete:
for a query with a single relevant document, moving it from rank 2 to rank 1 raises nDCG@10 from 0.63 to 1.00, a gain of 0.37. An average gain of 0.15 is therefore roughly that improvement on 4
queries in 10, which a user would notice. A gain much smaller than that would not justify the extra cost. Δ = 0.15 is also the course minimum, and it keeps the gold set to a size
I can judge in the time I have.

I chose nDCG@10 over MRR@10 because many questions about this corpus have more than one relevant document (the same commodity's chapter in 2024, 2025 and 2026), and nDCG@10 credits all
of them rather than only the first. For this pair it also needs 43 queries instead of 64.

---

## 3. How many queries you need

The size of the gold set follows from three numbers: how large a difference you want to detect (Δ), how variable the per-query differences are (sd), and the usual choices of a 5% false-alarm rate and 80% power.

```
n = ((1.96 + 0.84) * sd / Δ)^2
```

Here sd is the standard deviation of the per-query differences between your two systems, which `results/results.json` holds for the shared practice queries.
Compute it from your stage 1 runs for the same two systems, or the nearest pair you have, and say which pair you used.
With only 20 practice queries the sd is itself noisy, so be generous and round up.

Some numbers to calibrate against.
At sd 0.3 and Δ 0.10 the formula gives about 71 queries, and with the t distribution's small-sample correction it is a few more, about 73.
At sd 0.3, a gold set of 30 queries can only detect a difference of about 0.15, which is why 30 queries cannot support a claim about a gap of 0.10.
The spreads you will measure on the shared practice queries are mostly larger than 0.3: from about 0.31 for `hybrid` against `bm25` to about 0.66 for `dense` against `bm25`.
For `rerank` against `hybrid` the sd is about 0.39, so a Δ of 0.10 needs about 120 queries, 0.15 about 55, and 0.20 about 31.
So the course's Δ of 0.15 means about 55 queries for that pair; at an sd of 0.66 it would mean about 150, so compare a pair whose spread you can afford.
Choose Δ and the size of your gold set together: the smallest effect that matters to a user, and a number of queries you can write and judge in the time you have.
If the two do not meet, say which one you gave ground on and why.

After you score the own corpus, the minimum detectable difference that `uv run p2 score` prints for your two systems is this same calculation run the other way.
It should come out at or below your Δ.
If it does not, your queries varied more than your stage 1 sd suggested, and you will say so in the outcome.

Pair: rerank vs hybrid (the same pair as my hypothesis), from my stage 1 runs on the shared practice queries.
sd of per-query nDCG@10 differences: 0.349.
n = ((1.96 + 0.84) × 0.349 / 0.15)² = (6.515)² ≈ 42.4, rounded up to 43.
Queries I will write and judge: 50. The stage 1 sd is estimated from only 20 practice queries on a different corpus, so my own queries may vary more; 50 leaves a 
margin of 7 (about 15%) above n. I did not give ground on Δ, and 50 queries is a number I can write and judge before the deadline.

---

## 4. The test, and what each result will mean

The test is the paired 95% interval of the mean difference between your two systems on your own gold set, from the `own-pairs` table that `uv run p2 score` writes in `EVAL.md`.
Write the rule now.
This is the default rule, and you can tighten it, but do not loosen it after you see your numbers.

| The interval is | I will say |
|---|---|
| entirely above zero in the direction I predicted | supported: the difference is distinguishable from zero |
| entirely on the other side of zero | contradicted: the opposite of my hypothesis holds on this gold set |
| around zero, with both ends inside plus or minus Δ | well-powered null: a difference as large as Δ is ruled out |
| around zero, with an end beyond plus or minus Δ | inconclusive: the gold set could not settle it, and I say so |

I adopt this default rule as written. The comparison is rerank minus hybrid on nDCG@10, with Δ = 0.15, so "the direction I predicted" means the interval lies entirely above zero.

---

## 5. Outcome (write this after the fact)

What was the interval?
Which row of the table in section 4 is it?
Did your gold set reach the size section 3 asked for, and what was the minimum detectable difference that `uv run p2 score` printed?
What would you do next, and what would you want a reader to take from this?


**Interval.** rerank minus hybrid on nDCG@10 is +0.142, with a 95% paired interval of [+0.073, +0.215] over 50 queries (EVAL.md, own-pairs).

**Row.** The interval is entirely above zero in the predicted direction, so by my section 4 rule the hypothesis is **supported: the 
difference is distinguishable from zero.** That is all the rule claims. The mean (+0.142) is just under my Δ of 0.15, and the interval contains Δ, so 
this gold set does not show that the gain is at least as large as the smallest effect I said would matter to a user. It also does not rule that out.

**Gold-set size.** Section 3 called for 43 queries, and I judged 50. The per-query sd on my corpus was 0.258, lower than the 0.349 I estimated from 
the stage 1 practice queries, so the minimum detectable difference that `p2 score` printed was 0.102, well under Δ. At that sd, about 23 queries would 
have been enough.

**What a reader should take from it.** On this corpus, reranking hybrid's top 20 with Claude reliably improves nDCG@10, at a cost of about 8,900 input tokens 
and 5.2 seconds per query. Most of the gain is on paraphrase queries (hybrid 0.390 → rerank 0.673), against 0.853 → 0.946 on identifier queries and 0.969 → 0.998 on mixed. That is consistent 
with my reason in section 1, though the per-class means have no intervals and each class has only 15–18 queries. The 22 queries rerank helped, against 4 it hurt, point the same way.

**Next.** This result says rerank beats hybrid, not that it beats it by at least Δ. To test that, I would pre-register the stronger claim (lower interval end above 0.15)
and judge more queries, or narrow it to paraphrase queries, where the gain is concentrated. Separately, the failure analysis in EVAL.md section 6 shows the reranker is not the
bottleneck on the paraphrase misses: in three of them, no relevant chapter reached hybrid's top 20. So I would also test a deeper first stage (fusing more than each arm's top 10,
or passing the reranker more than 20 candidates) before spending on a better reranker.
---

## 6. Amendments

Dated entries only, one per change, each saying what changed and why.
Leave this section as it is if nothing changed.
