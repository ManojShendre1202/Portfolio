import re

import spacy

# No hardcoded stopword list — spaCy's own per-token `is_stop` flag (its
# built-in linguistic stopword data, same as what tags 'with'/'a'/'that' as
# function words) is used directly in ngram_spans below instead. Checked on
# EVERY token in a span, not just the head — a head-only check lets junk
# like 'how do dataloader' survive purely because it ends on a real noun,
# with the leading 'how'/'do' along for the ride. The one deliberate
# exception: 'with statement' / 'for loop' — a leading ADP/SCONJ is a
# spaCy stopword by definition, but grammatically load-bearing there, so
# the 2-word ADP/SCONJ+NOUN pattern is exempted from the interior check
# (see doc_retrieval.py's note on an earlier, broader hardcoded list
# silently breaking that exact question).

# A span survives only if its last word is one of these (a phrase's
# semantic head is almost always its final noun/verb), OR it's a 2-word
# ADP/SCONJ+NOUN span ('with statement', 'for loop') — see doc_retrieval.py.
_CONTENT_POS = frozenset({"NOUN", "PROPN", "VERB", "ADJ"})

_nlp = spacy.load("en_core_web_sm")


def ngram_spans(question: str, max_n: int = 2) -> list[tuple[int, int, str]]:
    """Every 1..max_n word span of the question, POS-filtered and deduped
    by phrase text (first occurrence's span wins). See doc_retrieval.py's
    _ngram_spans for the full rationale — this is a faithful copy."""
    doc = _nlp(question)

    words = []
    for tok in doc:
        cleaned = re.sub(r"[^a-z0-9_]", "", tok.text.lower())
        if cleaned:
            words.append((tok, cleaned))

    seen: dict[str, tuple[int, int]] = {}
    for n in range(1, max_n + 1):
        for i in range(len(words) - n + 1):
            span = words[i:i + n]
            first_tok, _ = span[0]
            last_tok, _  = span[-1]
            if n == 1:
                keep = first_tok.pos_ in _CONTENT_POS and not first_tok.is_stop
            else:
                is_adp_pattern = (
                    n == 2 and first_tok.pos_ in ("ADP", "SCONJ") and last_tok.pos_ in ("NOUN", "PROPN")
                )
                # every word except the head must itself be stopword-free —
                # unless it's the ADP/SCONJ+NOUN exception above, where the
                # leading preposition is exempt on purpose
                interior_ok = is_adp_pattern or all(not t.is_stop for t, _ in span[:-1])
                keep = interior_ok and last_tok.pos_ in _CONTENT_POS and not last_tok.is_stop
            if not keep:
                continue
            phrase = " ".join(cleaned for _, cleaned in span)
            if phrase not in seen:
                seen[phrase] = (i, i + n - 1)

    return [(start, end, phrase) for phrase, (start, end) in seen.items()]


def extract_keywords(question: str) -> list[str]:
    """Input string -> ranked keyword/keyphrase list.

    No corpus, so no embedding-similarity ranking is possible — spans are
    instead ranked longest-first (a rough proxy for "more specific"). With
    max_n capped at 2 (see ngram_spans), there's no 3-word-phrase-matches-
    nothing-real risk to guard against, so unlike doc_retrieval.py's
    keyword_seed_candidates, standalone single words are NOT exempt from
    the overlap rule here: a word is only kept on its own if it isn't
    already covered by a kept 2-word phrase. 'dataset work' being kept
    means bare 'dataset' and 'work' don't also survive as redundant
    near-duplicates; a word with no surviving 2-word phrase around it
    (e.g. 'dataloader' on its own) still gets its own candidate.
    """
    spans = ngram_spans(question)
    if not spans:
        return []

    # longest phrase first; ties broken by earliest position in the question
    spans.sort(key=lambda s: (-(s[1] - s[0]), s[0]))

    selected = []
    used_word_pos = set()
    for start, end, phrase in spans:
        word_pos = set(range(start, end + 1))
        if word_pos & used_word_pos:
            continue
        used_word_pos |= word_pos
        selected.append(phrase)

    return selected


def main():
    print("Keyword extractor debug REPL (no corpus/embedder — see module docstring).")
    print("Type a question, or 'quit'.")
    while True:
        question = input('\n> ').strip()
        if not question or question.lower() in ('quit', 'exit'):
            break

        keywords = extract_keywords(question)
        print(f"\n{len(keywords)} keyphrase(s):")
        for kw in keywords:
            print(f"  - {kw}")


if __name__ == '__main__':
    main()
