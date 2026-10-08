"""Hybrid retrieval: fuse the full rankings of two systems with reciprocal rank fusion.

It is the 13 lab's rrf() and command_fuse() (class/13-rag-pipeline/lab/starter/pipeline.py) moved
onto p2's systems. Each system ranks every document; a document's fused score is the sum, over the
systems, of its weight divided by (rrf_k + its rank there):

    score(d) = sum over systems of  weight / (rrf_k + rank of d in that system)     rank 1 is best

That is all reciprocal rank fusion is: it reads positions, not scores, so bm25's raw sums and
dense's cosines never have to be put on one scale, and a document that both systems like a little
can beat one that only bm25 loves. rrf_k = 60 is the lab's constant; a larger value flattens the
curve, so the deep ranks matter more, and a smaller one sharpens it, so a first place in one system
survives a bad rank in the other. The constant is worth measuring here: with 2,484 documents,
1 / (60 + 1) and 1 / (60 + 10) differ by 13%, so at 60 the fused top 10 is made almost entirely of
documents both systems place reasonably well, which is the opposite of keeping each system's best
find. Try it both ways with the [hybrid] table below and put the numbers in EVAL.md.

Two details decide whether the fusion is worth anything:
- the two systems come from p2.retrievers.build(), the cache in __init__.py, so a run of several
  systems builds the BM25 index and the chunk vectors once and not once per system or per query;
- the rankings fused are FULL rankings, every document (and for search_chunks every chunk), not the
  top 10. A document that sits 11th in both systems belongs in the fused top 10, and cutting the
  inputs at 10 first would throw it away. That is the one easy thing to get wrong here.

The systems, their weights and the constant are read from the optional [hybrid] table of p2.toml,
so they can be changed without editing this file:

    [hybrid]
    systems = ["bm25", "dense"]     # any two or more systems in this folder
    weights = [1.0, 1.0]            # one per system, in the same order; higher counts for more
                                    # (default: 1.0 each, whatever the number of systems)
    rrf_k = 60                      # the lab's constant

bm25 and dense are fused by default because the practice queries split cleanly between them: bm25
answers the identifier queries and finds nothing on the paraphrases, and dense is the mirror image.
Whether fusing them keeps both strengths or only averages them is the measurement, not a given.
Changing any of these values changes the scores, so re-run `p2 run` and `p2 score` afterwards.
"""

from __future__ import annotations

from p2 import retrievers
from p2.runfile import order

NEEDS_CLAUDE = False

SYSTEMS = ("bm25", "dense")  # the two arms: keyword search and embeddings
WEIGHT = (1.0,)  # one weight per system by default: equal say, as the lab's rrf() gives
RRF_K = 60  # the lab's constant: the rank at which a hit is worth half of a first place


class Hybrid:
    def __init__(self, corpus, cfg):
        self.corpus = corpus
        self.cfg = cfg
        settings = cfg.table("hybrid")
        self.names = [str(n) for n in settings.get("systems", SYSTEMS)]
        self.weights = [float(w) for w in settings.get("weights", WEIGHT * len(self.names))]
        self.rrf_k = float(settings.get("rrf_k", RRF_K))
        if len(self.names) < 2:
            raise ValueError(f"[hybrid] systems needs at least two systems to fuse, not {self.names}.")
        if len(self.weights) != len(self.names):
            raise ValueError(f"[hybrid] has {len(self.weights)} weight(s) for {len(self.names)} system(s); give one weight per system.")
        if self.rrf_k <= 0:
            raise ValueError(f"[hybrid] rrf_k must be above 0, not {self.rrf_k}.")
        # Through retrievers.build, so each arm's index is built once per run and not once per query.
        self.systems = [retrievers.build(name, corpus, cfg) for name in self.names]
        # How deep to ask each arm: every document, and every chunk (the corpus caches its chunks).
        self.all_docs = len(corpus.docs)
        self.all_chunks = len(corpus.chunks(cfg.chunk_words, cfg.chunk_overlap))

    def fuse(self, rankings: list[list[tuple[str, float]]]) -> list[tuple[str, float]]:
        """Reciprocal rank fusion over one ranking per system; equal scores in id order."""
        scores: dict[str, float] = {}
        for weight, ranking in zip(self.weights, rankings):
            for rank, (ident, _score) in enumerate(ranking, 1):
                scores[ident] = scores.get(ident, 0.0) + weight / (self.rrf_k + rank)
        return order(scores.items())

    def search(self, text: str, k: int) -> list[tuple[str, float]]:
        """The k best documents, fusing each system's ranking of the whole corpus."""
        return self.fuse([system.search(text, self.all_docs) for system in self.systems])[:k]

    def search_chunks(self, text: str, k: int) -> list[tuple[str, float]]:
        """The k best chunks, the same fusion one level down, which is what `p2 answer` asks for."""
        return self.fuse([system.search_chunks(text, self.all_chunks) for system in self.systems])[:k]


def build(corpus, cfg):
    return Hybrid(corpus, cfg)
