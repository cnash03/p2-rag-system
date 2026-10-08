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
DECIMALS = 5  # the precision the cosine reproduces on another machine; see score_chunks


class Dense(ChunkScorer):
    def __init__(self, corpus, cfg):
        super().__init__(corpus, cfg)
        settings = cfg.table("dense")
        self.model = str(settings.get("model", MODEL))
        self.query_instruction = str(settings.get("query_instruction", ""))
        self.decimals = int(settings.get("decimals", DECIMALS))
        self.embedder = embed.load(self.model)
        # One row per chunk, in the order of self.chunks, from the cache where possible.
        self.vectors = embed.doc_vectors(self.embedder, [c.text for c in self.chunks], cfg.root)

    def score_chunks(self, text: str) -> list[float]:
        """Cosine of the query against every chunk, rounded to the precision that reproduces.

        The rounding is what makes a run file reproducible on a machine that is not this one, and
        `p2 check` and CI both regenerate the runs and compare them line by line. This corpus writes
        the same rule once for each of parts 56, 57, 75 and 77, so it is full of near-duplicate
        sections whose cosines land within a millionth of each other: on p07, cfr30-74.7 scored
        0.7060505 and cfr30-57.5005t 0.7060485, a gap of 2e-6. The embedding arithmetic differs by
        about that much between this laptop's ARM chip and CI's x86 Linux, so the two sections swap
        places there, which moves them between ranks 10 and 11 and changes which one hybrid's fused
        top 10 keeps. runfile.order already settles exact ties by docid, so rounding to a precision
        coarser than the noise turns a coin flip into that deterministic tie-break.

        5 decimals was measured, not guessed: perturbing every score by +/-3e-6 over 30 trials of
        the 20 practice queries moves the top 10 on 9 of 600 query-runs unrounded and 0 of 600 at
        5 decimals, while the per-class scores are identical to three decimals at every precision
        from 2 to 6. It holds to 3e-6 and starts to slip at 5e-6, so if CI ever disagrees with a
        committed run again, this is the number to lower.
        """
        if not self.chunks:
            return []
        query = self.embedder.encode([self.query_instruction + text])[0]
        return [round(float(s), self.decimals) for s in self.vectors @ query]


def build(corpus, cfg):
    return Dense(corpus, cfg)
