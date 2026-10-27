"""Ablation of dense: the same system with every document kept whole as one chunk.

The one change is the chunk size, [chunking] words = 0 instead of p2.toml's 300 (overlap has no
effect when a document is one chunk). The model, the query handling and the score snapping are
dense.py's, unchanged, so any difference in the scores comes from the chunking.

bge-small-en-v1.5 reads at most 512 tokens of a text and drops the rest, so a whole chapter of about
1,070 words is embedded from its first 380 words or so.
"""

from __future__ import annotations

from p2.retrievers.dense import Dense

NEEDS_CLAUDE = False

BASE = "dense"


def build(corpus, cfg):
    return Dense(corpus, cfg.replace(chunk_words=0))
