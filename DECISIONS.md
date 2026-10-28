# Decision log

Your methods section, in your own words.
About one to two pages in total.

Answer these as you go, not the night before it is due.
Each answer is easier to write while the decision is still fresh, and prompt 1 only works if you write it before you see your own-corpus numbers.
Specifics beat polish: a short, honest answer with a number in it is worth more than a long vague one.

Each prompt ends with a marker line.
Replace that line with your answer.
`uv run p2 check` reports a marker as unfinished work, and `uv run p2 check --final` fails while any marker is left, so a finished log is part of being done.

Please do not let the agent write these for you.
These answers are about what you chose and what you knew, and the agent cannot know that.
Prompt 3 in particular only works in your own words.

---

## 1. Why this corpus, and what you expected

Why did you pick the corpus you used in stage 2, and why does it belong to a field or a question you care about?
Then say what you expected before you measured anything: which of `bm25`, `dense`, `hybrid` and `rerank` do you think will win on it, and which will do worst, and why?

Commit this answer before your first `uv run p2 score` on the own corpus.
Git history then shows that the expectation came first, which is what lets it be wrong in a way that teaches you something.
If you were surprised later, say so in prompt 4 or in EVAL.md; do not come back and rewrite this one.

For stage 2 I used the USGS Mineral Commodity Summaries that contains 267 chapters covering the 2024 through 2026, about 1,060 words each. 
I picked it partly because it contrasts with the stage 1 corpus. 30 CFR is numbered legal text full of identifiers. The USGS chapters are 
short prose with production tables, so I can test whether hybrid’s stage 1 advantage holds once exact identifiers mostly disappear. 
The texts are also federal public-domain works, so licensing check was a simple pass. It matters to me because mines focuses on critical minerals and 
one of my old roommates works in the geology industry which I have learned much about in my time living with her. I expect rerank to win.
It performed well on stage 1 (nDCG@10 0.789), and a cross-encoder that reads the query and chapter together should handle the specific production 
and price questions this corpus invites. I expect dense to do worst. It was already lowest on stage 1 nDCG@10 (0.480). Here, the chapters for the same 
commodity in different years will embed almost identically, so dense will have little basis for putting the right year first. 

---

## 2. A fork in the road

Name one real design choice where you could have gone two ways: the chunk size, the embedding model, how the two systems are fused, how many documents the reranker sees, a sentence in `prompts/answer.txt`, how you cleaned the corpus.

Say which you picked, what the alternative was, and what you gave up by not taking it.
If you measured both, give both numbers.
If you rejected the alternative without measuring it, say why that was a fair call, and what it cost you in time, tokens or complexity.

"There was no alternative" is not an answer.
Find the fork.

The fork I chose to test was chunked retrieval versus embedding each whole chapter as a single vector. The 300-word chunk size was the template default (p2/config.py:35), 
not a size I independently selected after comparing alternatives. I kept that default for the chunked baseline and compared it with whole chapters in the ablation 
(EVAL.md §5). I committed the hypothesis before the run: whole chapters would lower MRR@10, because bge-small truncates long input and the later sections of a chapter, 
such as Events and Trends and Substitutes, would never be embedded. On my own corpus, dense_whole scored lower than chunked dense on MRR@10 by −0.092 [−0.188, −0.008], 
which is distinguishable and in the direction I predicted. On nDCG@10 (0.666 vs. 0.717, a gap of −0.051 [−0.128, +0.015]) and on recall@10, the two could not be told apart;
 the nDCG@10 MDD for this ablation is 0.104, so the observed gap is smaller than that threshold. I read this as weak support for chunking, not a clear win. The measured 
 truncation point turned out to be about 282–326 words, not the 380 I assumed in the hypothesis. Whole chapters won four queries (q25, q36, q38, q42), all about Domestic 
 Production and Use, because the title and commodity name shared a vector with the answer, and chunking separates them. Chunking also needs more vectors and more encoding 
 time than the 267 whole-chapter vectors. Since I only compared the template’s 300-word default with whole chapters and never tried sizes like 150 or 500, I can say that 
 this chunked setup beat whole chapters on MRR@10, not that 300 words is the right chunk size.

---

## 3. Where you overruled the agent

One time Claude suggested, wrote or claimed something and you did not take it.
It might be a relevance judgment you disagreed with, a retriever it called finished when a run file showed otherwise, a number it summarized wrongly, or a license it said was fine.

What did it do?
How did you notice?
What did you do instead?

If it genuinely never happened, say so plainly, and then say what you would have had to check in order to notice.
Being honest here costs you far less than a story you cannot defend when you record your video.

**What it did** Some of my queries ask about a specific year, and the year-named queries did not all follow one consistent labeling pattern. I asked Claude about the labels 
that did not fit the pattern. I listed the examples, said I was not claiming the labels were wrong and that the decision was mine, and asked whether I wanted to review 
them or commit them as they were. Claude had pointed out an inconsistency; it had not told me to relabel every query to fit a pattern.

**How I noticed** I reconsidered the labels by asking what each passage actually states, rather than treating the year pattern as a rule. For q22, which asks for the 2024 
percentage decrease in cement production, the 2025 cement chapter states directly that production decreased by 4% to an estimated 84 million tons. The 2026 chapter’s text 
covers 2025; its table gives a 2024 estimate but does not state the 4% decrease. The 2026 text says an estimated 83 million tons, while the table shows e85,000 thousand 
tons. A passage that does not state the percentage decrease does not answer q22, so I concluded the 2025-only label was appropriate. I checked the relevant sentences 
myself; that verification happened outside this session, so it is my judgment to stand behind. q23, q25 and q43 follow the same reasoning: the asked-for fact is in the 
2025 text only. For q19, which asks for cobalt import sources in 2020–23, the 2025 edition is relevant because its import-source discussion covers 2020–23. The 2024 
edition’s discussion covers 2019–22, so its inclusion needs a separate justification: it would count only if that passage also states information that answers the query 
about the 2020–23 period. I have not established that from the explanation here, so q19 remains a label I should recheck against the actual passage.

**What I did instead** I did not relabel the queries simply to make the year pattern consistent. I treated the pattern as a prompt to inspect the wording, then kept labels
where the passage states the fact the query asks for. The q19 label for the 2024 edition is the unresolved case and should be checked before I defend the full set of labels.

---

## 4. A number you do not trust

Pick one number in `EVAL.md` that you do not fully trust, and say why.
It could be a mean over a small query class, a difference whose interval includes zero, a verified share of 100%, a score on a gold set you wrote yourself, or a result you got only once.

What would have to be true for you to trust it?
Did you do anything to test it, and what did that show?

One number in EVAL.md I don’t fully trust is rerank’s nDCG@10 of 0.864, a +0.142 gap over the next system. That looks like a strong result, but rerank surfaced 52 top-10 
results outside the judging pool, according to the count I made in this chat. Those documents were not judged, so the scorer may treat them as not relevant even when they 
could answer a query. That makes rerank’s score uncertain; I do not have evidence here that hybrid has the same pool problem, since its 500 top-10 results all fell within 
the pool. I also cannot reproduce the exact count of 52 from my saved records: qrels.txt records documents marked relevant, and the keyword search’s top 10 is not saved, 
so the closest reconstruction is up to 59. My records cannot distinguish “judged not relevant” from “never seen.” To trust the rerank result, I would need to judge its 
unpooled results, save rejected judgments as well as positive ones, rescore with `uv run p2 score`, and log the new judgments as a dated entry in PREREG.md §6 rather than 
editing earlier sections. So far I have checked one query, q08. All three iron-ore chapters are relevant, matching qrels.txt, and its one unpooled result, a manganese 
chapter at rank 10, mentions iron only in passing. Rerank already ranks the three relevant chapters 1–3 on q08, so this check could not show the pool problem lowering 
its score. A real test would need queries where rerank scored low and its unpooled results rank high.

---

## 5. What is still wrong

One thing in your system, your corpus or your gold set that is not right, not finished, or that you do not fully understand.

What would you do next, and how would you find out whether it matters?
Name the file, the query or the document where someone could look.

One thing in my gold set that isn’t right is that two sets of labels break my own labeling rule. For q04, eval/own/qrels.txt marks mcs2024-aluminum, mcs2025-bismuth 
and mcs2026-bismuth as relevant. But the failure table in EVAL.md (around line 478) shows that the bismuth chapters mention alumina only as a substitute for bismuth, 
and that the aluminum-packaging sentence appears in all three aluminum editions while only 2024 is labeled. The second set is mcs2024-silver_old, a duplicate of the 
2024 silver chapter. In my ablation write-up (EVAL.md, around lines 457–459), I say that by my rule it should carry the same label as the chapter it copies. It is unlabeled 
for q15 and q16, and that is why q16 counted as a drop. I haven’t fixed either one yet, because changing qrels.txt after the pre-registration means rescoring and 
rechecking every number EVAL.md and DECISIONS.md quote. My next step would be to relabel q04 and the silver duplicate by my rule, log the change as a dated entry in 
PREREG.md §6 Amendments, and rerun uv run p2 score. I would know it matters if the rerank-minus-hybrid interval moves, if q04 stops appearing as a failure, or if q16’s 
ablation drop disappears. If q04 still misses after relabeling, that would point to first-stage recall rather than the labels. Someone checking this could start with 
eval/own/qrels.txt, the q04 and q16 rows, and the mcs2024-silver_old document.