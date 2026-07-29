"""Tests for the logic and word puzzle modules.

Positive cases are the actual puzzles published on the site, asserted
against their published solutions.
"""

from puzzle_analyzer import balance, cryptogram, truthlie, wordladder, zebra


class TestZebra:
    def test_reliquary_matches_published_solution(self, fixture):
        data = fixture("reliquary")
        verdict = zebra.validate(zebra.parse(data["spec"]))
        assert verdict.unique
        assert verdict.solution == data["expected"]

    def test_switchyard_matches_published_solution(self, fixture):
        data = fixture("switchyard")
        verdict = zebra.validate(zebra.parse(data["spec"]))
        assert verdict.unique
        assert verdict.solution == data["expected"]

    def test_switchyard_clues_are_a_minimal_set(self, fixture):
        # The page claims removing any intercepted fact leaves multiple
        # sequences.  The seven structured clues encode five facts; drop
        # the "Sable after Amber" fact and uniqueness must break.
        spec = fixture("switchyard")["spec"]
        spec["clues"] = [c for c in spec["clues"] if c["kind"] != "before"]
        verdict = zebra.validate(zebra.parse(spec))
        assert verdict.solution_count >= 2

    def test_unknown_item_is_malformed(self, fixture):
        spec = fixture("reliquary")["spec"]
        spec["clues"].append({"kind": "before", "a": "Nobody", "b": "Elish"})
        verdict = zebra.validate(zebra.parse(spec))
        assert not verdict.well_formed

    def test_clue_missing_operand_is_malformed(self, fixture):
        # Same defect class as the Codex truthlie finding: a known kind
        # with a missing operand must be a verdict, not a KeyError.
        spec = fixture("reliquary")["spec"]
        spec["clues"].append({"kind": "before", "a": "Elish"})
        verdict = zebra.validate(zebra.parse(spec))
        assert not verdict.well_formed
        assert any("missing field" in issue for issue in verdict.issues)

    def test_unknown_clue_kind_is_malformed(self, fixture):
        spec = fixture("reliquary")["spec"]
        spec["clues"].append({"kind": "psychic", "item": "Elish"})
        verdict = zebra.validate(zebra.parse(spec))
        assert not verdict.well_formed


class TestTruthLie:
    def test_choir_matches_published_solution(self, fixture):
        data = fixture("choir")
        verdict = truthlie.validate(truthlie.parse(data["spec"]))
        assert verdict.unique
        assert verdict.solution == data["expected"]

    def test_dropping_a_log_leaves_multiple_solutions(self, fixture):
        # The page claims all nine logs are necessary.
        spec = fixture("choir")["spec"]
        for drop in range(len(spec["statements"])):
            trimmed = dict(spec)
            trimmed["statements"] = [
                s for i, s in enumerate(spec["statements"]) if i != drop
            ]
            # One fewer statement, same three lies required.
            verdict = truthlie.validate(truthlie.parse(trimmed))
            assert verdict.solution_count != 1, f"log {drop + 1} seems redundant"

    def test_absent_candidate_makes_relational_claims_false(self):
        puzzle = truthlie.parse(
            {
                "candidates": ["A", "B", "C"],
                "sequence_length": 2,
                "false_count": 0,
                "statements": [{"kind": "before", "a": "A", "b": "C"}],
            }
        )
        assert not truthlie.holds(puzzle.statements[0], ("A", "B"))
        assert truthlie.holds(puzzle.statements[0], ("A", "C"))

    def test_statement_missing_operand_is_malformed(self, fixture):
        # Codex review finding (PR #5): {"kind": "before", "a": ...} used
        # to pass check() and then KeyError inside holds().
        spec = fixture("choir")["spec"]
        spec["statements"].append({"kind": "before", "a": "Ark"})
        verdict = truthlie.validate(truthlie.parse(spec))
        assert not verdict.well_formed
        assert any("missing field" in issue for issue in verdict.issues)

    def test_impossible_false_count_is_malformed(self, fixture):
        spec = fixture("choir")["spec"]
        spec["false_count"] = 99
        verdict = truthlie.validate(truthlie.parse(spec))
        assert not verdict.well_formed


class TestBalance:
    def test_assay_matches_published_solution(self, fixture):
        data = fixture("assay")
        verdict = balance.validate(balance.parse(data["spec"]))
        assert verdict.unique
        assert verdict.solution == data["expected"]

    def test_dropping_an_equation_breaks_uniqueness(self, fixture):
        spec = fixture("assay")["spec"]
        spec["equations"] = spec["equations"][:-1]
        verdict = balance.validate(balance.parse(spec))
        assert verdict.solution_count >= 2

    def test_too_many_distinct_symbols_is_malformed(self):
        verdict = balance.validate(
            balance.parse(
                {
                    "symbols": ["A", "B", "C"],
                    "max": 2,
                    "equations": [{"left": ["A"], "right": ["B"]}],
                }
            )
        )
        assert not verdict.well_formed


class TestCryptogram:
    def test_seals_decodes_to_published_phrase(self, fixture):
        data = fixture("seals")
        verdict = cryptogram.validate(cryptogram.parse(data["spec"]))
        assert verdict.unique
        assert verdict.solution == data["expected"]

    def test_dead_language_decodes_to_published_phrase(self, fixture):
        data = fixture("cipher")
        verdict = cryptogram.validate(cryptogram.parse(data["spec"]))
        assert verdict.unique
        assert verdict.solution == data["expected"]

    def test_ambiguous_wordlist_yields_multiple_solutions(self, fixture):
        # SHARK fits everywhere SHARP does (H occurs only in that word), so
        # adding it to the lexicon makes the cryptogram improper.
        spec = fixture("cipher")["spec"]
        spec["wordlist"] = [*spec["wordlist"], "SHARK"]
        verdict = cryptogram.validate(cryptogram.parse(spec))
        assert verdict.solution_count >= 2

    def test_unmatchable_word_reports_zero_solutions(self):
        verdict = cryptogram.validate(
            cryptogram.parse({"ciphertext": "XYZZY", "wordlist": ["HELLO"]})
        )
        assert verdict.well_formed and verdict.solution_count == 0

    def test_injective_mapping_enforced(self):
        # AB cannot decode to OO: two symbols may not share a letter.
        verdict = cryptogram.validate(
            cryptogram.parse({"ciphertext": "AB", "wordlist": ["OO"]})
        )
        assert verdict.solution_count == 0

    def test_no_self_map(self):
        verdict = cryptogram.validate(
            cryptogram.parse(
                {"ciphertext": "AB", "wordlist": ["AB", "BA"], "no_self_map": True}
            )
        )
        # "AB" would map every glyph to itself; only "BA" survives.
        assert verdict.unique and verdict.solution == "BA"


class TestWordLadder:
    def test_stair_is_the_unique_ladder(self, fixture):
        data = fixture("stair")
        verdict = wordladder.validate(wordladder.parse(data["spec"]))
        assert verdict.unique
        assert verdict.solution == data["expected"]

    def test_richer_wordlist_can_break_uniqueness(self, fixture):
        spec = fixture("stair")["spec"]
        spec["wordlist"] = [*spec["wordlist"], "MATE", "MARE"]
        verdict = wordladder.validate(wordladder.parse(spec))
        assert verdict.solution_count >= 2

    def test_endpoint_search_without_steps(self, fixture):
        spec = fixture("stair")["spec"]
        endpoints = {
            "start": "MAZE",
            "end": "HERE",
            "length": 9,
            "wordlist": spec["wordlist"],
        }
        verdict = wordladder.validate(wordladder.parse(endpoints))
        assert verdict.unique
        assert verdict.solution == fixture("stair")["expected"]

    def test_broken_step_is_malformed(self, fixture):
        spec = fixture("stair")["spec"]
        spec["steps"] = list(spec["steps"])
        spec["steps"][1] = "RACE"  # MAZE -> RACE changes two letters
        verdict = wordladder.validate(wordladder.parse(spec))
        assert not verdict.well_formed

    def test_word_outside_lexicon_is_malformed(self, fixture):
        spec = fixture("stair")["spec"]
        spec["wordlist"] = [w for w in spec["wordlist"] if w != "RITE"]
        verdict = wordladder.validate(wordladder.parse(spec))
        assert not verdict.well_formed
