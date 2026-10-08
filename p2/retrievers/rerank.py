"""Reranking: a first stage proposes 20 candidates, and Claude puts them in order.

It is the 13 lab's rerank_one() and command_rerank() (class/13-rag-pipeline/lab/starter/pipeline.py)
moved onto p2's systems. One query is one claude -p call:

- the first stage (hybrid, through p2.retrievers.build, so its arms are built once per run) ranks the
  whole corpus, and its top CANDIDATES documents become the passages;
- the passages go in numbered 1 to n, each cut to PASSAGE_CHARS characters, with the query under them,
  and the reply is forced into {"order": [n numbers]} by the schema that schema() builds;
- the reply becomes the new order of those n documents, and the first stage's documents below them
  keep their order underneath, so a run file still has k lines when k is above n.

Two things the schema and the check are for:
- the lab's schema fixes only how many numbers come back, so a reply such as [12, 2, 60, ...] would
  name a passage that does not exist; here each item also has "minimum": 1 and "maximum": n, which is
  what stops that reply from being produced at all;
- a reply that is still not each of 1 to n exactly once (a repeat, a short list, a number out of range)
  is not usable as an order, so permutation() returns None and the first-stage order is kept for that
  query, with a warning line under it. Nothing is dropped and nothing raises: the worst case is a run
  that is exactly the first stage's.

There is no `except Exception` around the call on purpose. claude.call already turns a timeout or an
unreadable reply into reply.error, which is the fallback above; what is left (no claude command, a bad
setting) should stop the run loudly, and p2.claude.ClaudeBlocked, which `p2 check` relies on to learn
that this system calls Claude, is a BaseException that an `except Exception` would have hidden.

NEEDS_CLAUDE = True tells p2 that searching calls claude -p: CI and `p2 check` never run this system
for real, they check the committed run file against the trace that `p2 run` writes beside it in
traces/, so commit the trace with the run.

The settings are read from the optional [rerank] table of p2.toml, with the defaults below in code:

    [rerank]
    candidates = 20                 # how many of the first stage's documents Claude orders
    passage_chars = 600             # how much of each document it sees (the lab's cut)
    first_stage = "hybrid"          # any other system in this folder

The table is named after this file, so a copy of it reads its own table: stretch option 3's
rerank_c10.py (CANDIDATES = 10) reads [rerank_c10] and is not changed by a [rerank] table.

Every call draws on your own Claude plan, about one call per query, so 20 calls for the practice
queries and 40 for the test queries. Try two queries first (README, "Build rerank").
"""

from __future__ import annotations

from p2 import claude, retrievers

NEEDS_CLAUDE = True

CANDIDATES = 20  # the lab's shortlist: how many passages one call puts in order
PASSAGE_CHARS = 600  # the lab's cut; 20 of these is most of a call's prompt, the rest is Claude Code's own
FIRST_STAGE = "hybrid"  # which system proposes the candidates
TABLE = __name__.rsplit(".", 1)[-1]  # this file's name, so a copy reads its own table and not [rerank]

PROMPT = """Below are {n} passages from a document collection, numbered 1 to {n}, and a search query.
Order the passages from the most useful for answering the query to the least useful.
Reply with all {n} passage numbers, each exactly once, best first.

Query: {query}

{passages}"""


def schema(n: int) -> dict:
    """The reply's shape: n integers under "order", each of them a passage number that exists.

    The lab's RERANK_SCHEMA with "minimum" and "maximum" added to the items (see the module docstring)."""
    return {
        "type": "object",
        "properties": {"order": {"type": "array", "items": {"type": "integer", "minimum": 1, "maximum": n}, "minItems": n, "maxItems": n}},
        "required": ["order"],
    }


def permutation(value, n: int) -> list[int] | None:
    """`value` as an order of n passages, or None when it is not each of 1 to n exactly once.

    None is the fallback signal: the caller then keeps the first-stage order. The type check comes
    before sorted(), because sorted() on a list of mixed types raises instead of answering."""
    if not isinstance(value, list) or len(value) != n:
        return None
    if any(isinstance(i, bool) or not isinstance(i, int) for i in value):  # True sorts as 1 in Python
        return None
    if sorted(value) != list(range(1, n + 1)):
        return None
    return list(value)


def scored(ids: list[str]) -> list[tuple[str, float]]:
    """Positions turned into scores, 1.0 down to 1/n, so the order survives the run file.

    A reranked order has no scores of its own, and a run file is read by score (ties go to the
    document id), so each position needs a score of its own: the step is 1/n, which stays visible at
    the six decimals a run file keeps for any n up to a million."""
    n = len(ids)
    return [(ident, (n - rank) / n) for rank, ident in enumerate(ids)]


class Rerank:
    def __init__(self, corpus, cfg):
        self.corpus = corpus
        self.cfg = cfg
        self.model = cfg.model  # read by p2 run for the trace's model field
        settings = cfg.table(TABLE)
        self.candidates = int(settings.get("candidates", CANDIDATES))
        self.passage_chars = int(settings.get("passage_chars", PASSAGE_CHARS))
        self.first_stage_name = str(settings.get("first_stage", FIRST_STAGE))
        if self.candidates < 2:
            raise ValueError(f"[{TABLE}] candidates must be at least 2, not {self.candidates}; there is nothing to order below that.")
        if self.passage_chars < 1:
            raise ValueError(f"[{TABLE}] passage_chars must be above 0, not {self.passage_chars}.")
        if self.first_stage_name == TABLE:
            raise ValueError(f"[{TABLE}] first_stage is {TABLE} itself, which would rerank forever; name another system.")
        # Through retrievers.build, so the first stage's index is built once per run and not once per query.
        self.first_stage = retrievers.build(self.first_stage_name, corpus, cfg)

    def passages(self, ids: list[str], texts: dict[str, str]) -> str:
        """The candidates as the numbered passages of the prompt, in the lab's "[1] text" form."""
        return "\n\n".join(f"[{i}] {texts[ident][: self.passage_chars]}" for i, ident in enumerate(ids, 1))

    def reorder(self, query: str, ids: list[str], texts: dict[str, str]) -> list[str]:
        """The ids with their first self.candidates put in Claude's order; the first-stage order on any
        reply that is not an order, with a warning line naming the query's problem."""
        head, tail = ids[: self.candidates], ids[self.candidates :]
        if len(head) < 2:
            return ids  # nothing to order: no call, no cost
        prompt = PROMPT.format(n=len(head), query=query, passages=self.passages(head, texts))
        reply = claude.call(prompt, schema(len(head)), model=self.cfg.model, cache_dir=claude.cache_folder(self.cfg))
        got = permutation((reply.output or {}).get("order"), len(head)) if reply.error is None else None
        if got is None:
            why = reply.error or f"the reply was not each of 1 to {len(head)} exactly once: {(reply.output or {}).get('order')!r}"
            print(f"      WARNING: {why}; kept the first-stage order", flush=True)
            return ids
        return [head[i - 1] for i in got] + tail

    def search(self, text: str, k: int) -> list[tuple[str, float]]:
        """The k best documents: the first stage's top candidates reordered by Claude.

        The first stage is asked for max(k, candidates) documents, so the shortlist is always full and
        the documents below it are still there to pad the run file up to k."""
        first = [docid for docid, _ in self.first_stage.search(text, max(k, self.candidates))]
        texts = {docid: self.corpus.docs[docid].text for docid in first}
        return scored(self.reorder(text, first, texts)[:k])

    def search_chunks(self, text: str, k: int) -> list[tuple[str, float]]:
        """The k best chunks, the same reranking one level down, which is what `p2 answer` asks for."""
        first = [cid for cid, _ in self.first_stage.search_chunks(text, max(k, self.candidates))]
        texts = self.corpus.chunk_texts(self.cfg.chunk_words, self.cfg.chunk_overlap)
        return scored(self.reorder(text, first, {cid: texts[cid] for cid in first})[:k])


def build(corpus, cfg):
    return Rerank(corpus, cfg)
