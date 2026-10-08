"""Dense retrieval: embed every chunk once, embed the query, and rank chunks by cosine similarity.

It is the 12 lab's embedding arm (retrieve.py: load_bge, cached_doc_vectors, dense_rankings) moved
onto chunks, with the helpers in p2/embed.py doing the loading and the caching:
- embed.load(name) loads the model, bge-small-en-v1.5 through fastembed or a static model through
  model2vec, and every vector it returns has length 1;
- embed.doc_vectors(model, texts, cfg.root) encodes the chunk texts and keeps them in
  .cache/vectors/<model>.npz keyed by each text's hash, so the chunks of the shared corpus (2,484
  sections) are encoded once and not once per query, and a later run or a changed chunking setting
  only encodes what is new.

Because both sides are unit vectors, the cosine similarity is a plain dot product, and one query is
one matrix product against the whole corpus (numpy, exact search, no vector database):
    score(c) = v(query) . v(chunk c)        between -1 and 1, higher means more relevant
A document's score is its best chunk's, which ChunkScorer does for search().

The model is read from the optional [dense] table of p2.toml, so it can be changed without editing
this file:

    [dense]
    model = "minishlab/potion-retrieval-32M"     # default: BAAI/bge-small-en-v1.5
    query_instruction = "Represent this sentence for searching relevant passages: "

bge-small's model card recommends that instruction in front of the query and not the documents;
the lab left it as a measurement to make, so it is off unless the table switches it on. Changing
either value changes the scores, so re-run `p2 run` and `p2 score` afterwards.
"""

from __future__ import annotations

from p2 import embed
from p2.retrievers import ChunkScorer

NEEDS_CLAUDE = False

MODEL = embed.BGE  # bge-small-en-v1.5: reads each word in context, which is what the paraphrase queries need
DECIMALS = 5  # decimals kept in a snapped score, so the run file's own numbers reproduce
TOLERANCE = 1e-3  # scores closer than this are one score; see score_chunks


class Dense(ChunkScorer):
    def __init__(self, corpus, cfg):
        super().__init__(corpus, cfg)
        settings = cfg.table("dense")
        self.model = str(settings.get("model", MODEL))
        self.query_instruction = str(settings.get("query_instruction", ""))
        self.decimals = int(settings.get("decimals", DECIMALS))
        self.tolerance = float(settings.get("tolerance", TOLERANCE))
        self.embedder = embed.load(self.model)
        # One row per chunk, in the order of self.chunks, from the cache where possible.
        self.vectors = embed.doc_vectors(self.embedder, [c.text for c in self.chunks], cfg.root)

    def score_chunks(self, text: str) -> list[float]:
        """Cosine of the query against every chunk, with near-equal scores snapped to one value.

        Why any of this: `p2 check` and CI regenerate every run that does not call Claude and
        compare it with the committed one, and CI runs on x86 Linux while this laptop is ARM.
        bge-small is a transformer run through ONNX, whose matrix-multiply kernels differ between
        the two, so the same chunk's cosine comes out about 3e-6 different there. That is far too
        small to change what the corpus means, and more than enough to swap two documents whose
        scores are closer together than that.

        30 CFR writes the same rule once for each of parts 56, 57, 75 and 77, so this corpus is
        made of near-duplicate sections, and they are exactly the pairs that sit inside the noise.
        On test query t15 ("Can a worker who shows up drunk or stoned stay on shift?"):

            cfr30-57.20001   0.681917608     <- these two are 6.08e-06 apart
            cfr30-56.20001   0.681911528
            cfr30-56.19067   0.653286457     <- the next gap down is 2.86e-02, 4,700x larger

        Rounding to a fixed number of decimals does not fix that, which took two red CI runs to
        learn. Both values sit within 3e-6 of the 5-decimal line at 0.681915, so on Linux both
        round to 0.68191, they tie, the docid tie-break puts part 56 first, and cfr30-57.20001
        falls from dense rank 1 to rank 2. Grid rounding only ties scores that share a cell.

        That one swap is nearly invisible in this system's own run file and loud in hybrid's. The
        score written here moves by 1e-5, which the checker forgives, while hybrid reads the rank
        and its fused score moves from 1/2 to 1/3, which the checker does not.

        So snap by GAP instead of by position. Walking the scores from best to worst, a score
        within self.tolerance of its group's leader becomes the leader's score, and anything
        further away starts a new group. Near-duplicates then tie exactly wherever they fall,
        runfile.order settles exact ties by docid, and the order is the same on every machine.
        Comparing against the leader rather than the previous score keeps a group no wider than the
        tolerance, so a long chain of small steps cannot collapse a whole range.

        The tolerance was measured on hybrid's docid-to-score map, the thing the checker compares,
        over 40 trials of all 60 shared queries. Perturbing every score by +/-3e-6, the noise above,
        changes it on 24 of 2,400 query-runs under the 5-decimal rounding that failed CI, and 0 of
        2,400 at this tolerance, which also holds at 1e-5. The practice scores are identical to
        three decimals at 1e-4 and 1e-3 (hybrid 0.693 MRR@10, 0.817 recall@10); 1e-2 is too coarse
        and costs real accuracy (0.671). If CI ever disagrees with a committed run again, raise this
        before touching anything else.
        """
        if not self.chunks:
            return []
        query = self.embedder.encode([self.query_instruction + text])[0]
        return self.snap((self.vectors @ query).tolist())

    def snap(self, scores: list[float]) -> list[float]:
        """Every score within self.tolerance of its group's leader becomes the leader's score."""
        out = [0.0] * len(scores)
        leader = None
        for i in sorted(range(len(scores)), key=lambda i: -scores[i]):
            if leader is None or leader - scores[i] > self.tolerance:
                leader = scores[i]
            out[i] = round(leader, self.decimals)
        return out


def build(corpus, cfg):
    return Dense(corpus, cfg)
