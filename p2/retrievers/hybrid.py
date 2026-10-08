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

The two systems come from p2.retrievers.build(), the cache in __init__.py, so a run of several
systems builds the BM25 index and the chunk vectors once and not once per system or per query.

How deep to read each arm (depth) is the other decision, and the stub's advice to fuse the full
rankings turned out to be wrong on this corpus, in both directions at once. Fusing all 2,484
documents scores 0.668 MRR@10 on the practice queries and fusing each arm's top 10 scores 0.693,
because at rrf_k = 1 a document sitting 11th in both arms scores 1/12 + 1/12 = 0.167 and so
displaces one that a single arm put 5th (1/6 = 0.167, and the tie goes to the docid). The deep
ranks are mostly noise here, and they are also the irreproducible part: dense's cosines for the
near-duplicate sections of parts 56, 57, 75 and 77 sit within 1e-5 of each other, the bge model's
ONNX arithmetic differs by about that much between ARM and x86, and a single swap at rank 30 moves
the rank of everything below it and so changes every fused score. Perturbing the scores by 1.5e-5
over 30 trials of the 20 practice queries changes the committed run on 62 of 300 query-runs at full
depth and 0 of 600 at depth 10. Hence depth 10, measured rather than assumed; see dense.py.

reach() never reads less deep than the k being asked for, so the reranker still gets a pool of 20
candidates from search_chunks(text, 20) while the k = 10 run file fuses at depth 10.

The systems, their weights, the constant and the depth are read from the optional [hybrid] table of
p2.toml, so they can be changed without editing this file:

    [hybrid]
    systems = ["bm25", "dense"]     # any two or more systems in this folder
    weights = [1.0, 1.0]            # one per system, in the same order; higher counts for more
                                    # (default: 1.0 each, whatever the number of systems)
    rrf_k = 60                      # the lab's constant
    depth = 10                      # how deep to read each arm; full depth is len(corpus.docs)

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
DEPTH = 10  # how deep to read each arm; see the note on depth below


class Hybrid:
    def __init__(self, corpus, cfg):
        self.corpus = corpus
        self.cfg = cfg
        settings = cfg.table("hybrid")
        self.names = [str(n) for n in settings.get("systems", SYSTEMS)]
        self.weights = [float(w) for w in settings.get("weights", WEIGHT * len(self.names))]
        self.rrf_k = float(settings.get("rrf_k", RRF_K))
        self.depth = int(settings.get("depth", DEPTH))
        if self.depth < 1:
            raise ValueError(f"[hybrid] depth must be at least 1, not {self.depth}.")
        if len(self.names) < 2:
            raise ValueError(f"[hybrid] systems needs at least two systems to fuse, not {self.names}.")
        if len(self.weights) != len(self.names):
            raise ValueError(f"[hybrid] has {len(self.weights)} weight(s) for {len(self.names)} system(s); give one weight per system.")
        if self.rrf_k <= 0:
            raise ValueError(f"[hybrid] rrf_k must be above 0, not {self.rrf_k}.")
        # Through retrievers.build, so each arm's index is built once per run and not once per query.
        self.systems = [retrievers.build(name, corpus, cfg) for name in self.names]

    def fuse(self, rankings: list[list[tuple[str, float]]]) -> list[tuple[str, float]]:
        """Reciprocal rank fusion over one ranking per system; equal scores in id order."""
        scores: dict[str, float] = {}
        for weight, ranking in zip(self.weights, rankings):
            for rank, (ident, _score) in enumerate(ranking, 1):
                scores[ident] = scores.get(ident, 0.0) + weight / (self.rrf_k + rank)
        return order(scores.items())

    def reach(self, k: int) -> int:
        """How deep to read each arm: self.depth, but never less than the k being asked for."""
        return max(self.depth, k)

    def search(self, text: str, k: int) -> list[tuple[str, float]]:
        """The k best documents, fusing each system's top self.reach(k)."""
        reach = self.reach(k)
        return self.fuse([system.search(text, reach) for system in self.systems])[:k]

    def search_chunks(self, text: str, k: int) -> list[tuple[str, float]]:
        """The k best chunks, the same fusion one level down, which is what `p2 answer` asks for."""
        reach = self.reach(k)
        return self.fuse([system.search_chunks(text, reach) for system in self.systems])[:k]


def build(corpus, cfg):
    return Hybrid(corpus, cfg)
