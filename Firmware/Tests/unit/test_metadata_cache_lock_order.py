"""
Test lock acquisition order documentation in MetadataCache.

This module verifies that:
1. Lock acquisition order is properly documented
2. No deadlock-prone nested lock acquisitions exist
3. All lock usage follows the documented order

Lock Order (must always be followed):
    1. _l1_lock (first)
    2. _l2_lock (second)
    3. _stats_lock (last)

Related to: Issue #100 - Metadata cache thread safety
"""

import inspect
import re
from pathlib import Path

import pytest

from webui.backend.services.metadata_cache import MetadataCache


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create temporary cache directory"""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def cache(temp_cache_dir):
    """Create MetadataCache instance"""
    return MetadataCache(
        cache_dir=temp_cache_dir,
        l1_max_size=100,
        l2_max_size=1000,
        cache_version="1.0"
    )


def test_lock_order_documented_in_class_docstring(cache):
    """
    Test that lock acquisition order is documented in class docstring.

    Critical for preventing deadlocks when future developers add features.
    """
    class_doc = inspect.getdoc(MetadataCache)

    # Verify lock order is documented
    assert "LOCK ACQUISITION ORDER" in class_doc, \
        "Class docstring should document lock acquisition order"

    # Verify the order is specified
    assert "_l1_lock" in class_doc, "Lock order should mention _l1_lock"
    assert "_l2_lock" in class_doc, "Lock order should mention _l2_lock"
    assert "_stats_lock" in class_doc, "Lock order should mention _stats_lock"

    # Verify deadlock warning is present
    assert "deadlock" in class_doc.lower(), \
        "Documentation should warn about deadlocks"


def test_lock_order_is_correct_in_documentation(cache):
    """
    Test that documented lock order matches the recommended pattern.

    The order should be: _l1_lock → _l2_lock → _stats_lock
    """
    class_doc = inspect.getdoc(MetadataCache)

    # Verify _l1_lock comes before _l2_lock in the full docstring
    l1_pos = class_doc.find('_l1_lock')
    l2_pos = class_doc.find('_l2_lock')
    stats_pos = class_doc.find('_stats_lock')

    assert l1_pos != -1, "_l1_lock should be in class documentation"
    assert l2_pos != -1, "_l2_lock should be in class documentation"
    assert stats_pos != -1, "_stats_lock should be in class documentation"

    # Find the numbered list in the lock order section
    # Look for "1. _l1_lock", "2. _l2_lock", "3. _stats_lock" pattern
    assert "1. _l1_lock" in class_doc or "1._l1_lock" in class_doc.replace(' ', ''), \
        "Documentation should specify _l1_lock as first lock"
    assert "2. _l2_lock" in class_doc or "2._l2_lock" in class_doc.replace(' ', ''), \
        "Documentation should specify _l2_lock as second lock"
    assert "3. _stats_lock" in class_doc or "3._stats_lock" in class_doc.replace(' ', ''), \
        "Documentation should specify _stats_lock as third lock"


def test_no_nested_lock_acquisitions_in_source():
    """
    Test that there are no nested lock acquisitions in the source code.

    Nested locks are the primary cause of deadlocks. All current methods
    use locks independently without nesting.
    """
    # Read the source file
    source_file = Path("webui/backend/services/metadata_cache.py")
    with open(source_file) as f:
        content = f.read()

    # Parse into methods
    methods = re.split(r'\n    def ', content)

    nested_locks_found = []

    for method in methods[1:]:  # Skip first split (before any method)
        lines = method.split('\n')
        method_name = lines[0].split('(')[0] if lines else "unknown"

        # Track lock acquisition by indentation
        lock_stack = []
        for i, line in enumerate(lines):
            indent = len(line) - len(line.lstrip())
            lock_match = re.search(r'with self\.(_\w+_lock):', line)

            if lock_match:
                lock_name = lock_match.group(1)

                # Clean stack of locks at same or deeper indentation
                lock_stack = [(l, ind) for l, ind in lock_stack if ind < indent]

                # If stack not empty, we have nesting
                if lock_stack:
                    nested_locks_found.append({
                        'method': method_name,
                        'outer_lock': lock_stack[-1][0],
                        'inner_lock': lock_name,
                        'line': i
                    })

                lock_stack.append((lock_name, indent))

    assert len(nested_locks_found) == 0, \
        f"Found nested lock acquisitions (deadlock risk): {nested_locks_found}"


def test_lock_usage_patterns_documented(cache):
    """
    Test that current lock usage patterns are documented.

    Helps future developers understand when to use each lock.
    """
    class_doc = inspect.getdoc(MetadataCache)

    # Verify usage patterns are documented
    assert "Current lock usage patterns" in class_doc or "lock usage" in class_doc.lower(), \
        "Class should document current lock usage patterns"

    # Verify specific methods are mentioned
    assert "get()" in class_doc, "get() lock usage should be documented"
    assert "set()" in class_doc, "set() lock usage should be documented"


def test_guidelines_for_future_modifications(cache):
    """
    Test that guidelines are provided for future code modifications.

    Essential for maintaining thread safety as code evolves.
    """
    class_doc = inspect.getdoc(MetadataCache)

    # Check for guidelines section
    assert "Guidelines" in class_doc or "future" in class_doc.lower(), \
        "Should provide guidelines for future modifications"

    # Verify key guidelines are present
    assert "narrow" in class_doc.lower() or "scope" in class_doc.lower(), \
        "Should mention keeping lock scope narrow"


def test_all_three_locks_exist(cache):
    """
    Test that all three locks mentioned in documentation exist.
    """
    assert hasattr(cache, '_l1_lock'), "Cache should have _l1_lock"
    assert hasattr(cache, '_l2_lock'), "Cache should have _l2_lock"
    assert hasattr(cache, '_stats_lock'), "Cache should have _stats_lock"


def test_locks_are_independent_not_reentrant(cache):
    """
    Test that locks are standard (non-reentrant) threading.Lock objects.

    Standard locks will deadlock if the same thread tries to acquire twice,
    which helps catch bugs early.
    """
    # Verify locks have acquire/release (standard lock interface)
    for lock_name in ['_l1_lock', '_l2_lock', '_stats_lock']:
        lock = getattr(cache, lock_name)
        assert hasattr(lock, 'acquire'), f"{lock_name} should have acquire method"
        assert hasattr(lock, 'release'), f"{lock_name} should have release method"
        # Non-reentrant locks don't have 'owner' attribute (RLock does)
        assert not hasattr(lock, '_owner'), \
            f"{lock_name} should be non-reentrant Lock, not RLock"


def test_documentation_warns_about_external_code(cache):
    """
    Test that documentation warns against calling external code while holding locks.

    Calling external code (especially user code) while holding locks can:
    - Cause deadlocks if external code tries to acquire the same lock
    - Cause performance issues (lock held for unpredictable time)
    - Make reasoning about thread safety difficult
    """
    class_doc = inspect.getdoc(MetadataCache)

    assert "external" in class_doc.lower(), \
        "Documentation should warn about external code while holding locks"
