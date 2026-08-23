"""Correction 1: deterministic canonical hashing of unordered collections (set/frozenset).

Python's iteration order for ``set``/``frozenset`` depends on hash randomization and
insertion history, so it is not guaranteed stable across processes -- these tests prove the
canonical payload/hash is invariant to that, while list/tuple order remains scientifically
meaningful and still affects the hash.
"""

from __future__ import annotations

import os
import subprocess
import sys

from kdaa.evaluation.paper_b.hashing import canonical_payload, content_hash


def test_equal_sets_built_in_different_orders_hash_identically() -> None:
    set_a = {"gamma", "alpha", "beta", "delta", "epsilon"}
    set_b = {"epsilon", "delta", "beta", "alpha", "gamma"}
    assert canonical_payload(set_a) == canonical_payload(set_b)
    assert content_hash({"tags": set_a}) == content_hash({"tags": set_b})


def test_equal_frozensets_built_in_different_orders_hash_identically() -> None:
    frozen_a = frozenset({"z", "y", "x", "w"})
    frozen_b = frozenset({"w", "x", "y", "z"})
    assert canonical_payload(frozen_a) == canonical_payload(frozen_b)
    assert content_hash(frozen_a) == content_hash(frozen_b)


def test_canonical_payload_of_set_is_sorted_deterministically() -> None:
    value = {"c", "a", "b"}
    assert canonical_payload(value) == ["a", "b", "c"]


def test_set_of_unorderable_elements_does_not_raise() -> None:
    # Plain Python `<` cannot compare an int to a str (TypeError); sorting by each
    # element's own canonical JSON string instead means this never raises, and is
    # deterministic: '"plain-string"' < '3' lexicographically, so the string sorts first.
    mixed = frozenset({"plain-string", 3})
    assert canonical_payload(mixed) == ["plain-string", 3]


def test_nested_sets_are_stable() -> None:
    nested_a = {frozenset({"b", "a"}), frozenset({"d", "c"})}
    nested_b = {frozenset({"c", "d"}), frozenset({"a", "b"})}
    assert canonical_payload(nested_a) == canonical_payload(nested_b)
    assert content_hash(nested_a) == content_hash(nested_b)


def test_set_nested_inside_list_and_dict_is_stable() -> None:
    payload_a = {"items": [{"labels": {"x", "y", "z"}}, {"labels": {"m", "n"}}]}
    payload_b = {"items": [{"labels": {"z", "y", "x"}}, {"labels": {"n", "m"}}]}
    assert content_hash(payload_a) == content_hash(payload_b)


def test_list_order_still_changes_the_hash() -> None:
    ordered_a = ["one", "two", "three"]
    ordered_b = ["three", "two", "one"]
    assert canonical_payload(ordered_a) != canonical_payload(ordered_b)
    assert content_hash(ordered_a) != content_hash(ordered_b)


def test_tuple_order_still_changes_the_hash() -> None:
    ordered_a = ("one", "two", "three")
    ordered_b = ("three", "two", "one")
    assert content_hash(ordered_a) != content_hash(ordered_b)


def test_set_hash_differs_from_hash_of_a_genuinely_different_set() -> None:
    assert content_hash({"a", "b"}) != content_hash({"a", "b", "c"})


def _hash_in_subprocess(hash_seed: str) -> str:
    script = (
        "from kdaa.evaluation.paper_b.hashing import content_hash\n"
        "value = {'tags': {'gamma', 'alpha', 'beta', 'delta', 'epsilon', 'zeta'}, "
        "'nested': [{'inner': {'x', 'y', 'z'}}, {'inner': {'p', 'q', 'r'}}]}\n"
        "print(content_hash(value))\n"
    )
    env = dict(os.environ)
    env["PYTHONHASHSEED"] = hash_seed
    result = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def test_hash_is_stable_across_processes_with_different_hash_seeds() -> None:
    # PYTHONHASHSEED controls Python's per-process string hash randomization, which is
    # exactly the source of set/frozenset iteration-order nondeterminism this correction
    # fixes. Running with two very different seeds in separate subprocesses is the closest
    # practical local proxy for "different environments" without an actual multi-machine run.
    hash_with_seed_0 = _hash_in_subprocess("0")
    hash_with_seed_1 = _hash_in_subprocess("1")
    hash_with_seed_large = _hash_in_subprocess("4000000000")
    assert hash_with_seed_0 == hash_with_seed_1 == hash_with_seed_large
