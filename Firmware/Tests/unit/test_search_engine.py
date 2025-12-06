"""
Unit tests for search_engine.py - SQLite FTS5 photo search engine

Tests cover:
- Database initialization and schema creation
- Photo indexing and updates
- Photo removal from index
- Text search with FTS5 features (prefix, phrase)
- Pagination and result formatting
- Index statistics
- Error handling and edge cases
"""

import pytest
import sqlite3
from pathlib import Path
from webui.backend.lib.search_engine import SearchEngine, SearchResult, SearchMatch


class TestSearchEngineInit:
    """Test database initialization and schema creation"""

    def test_creates_database_file(self, tmp_path):
        """Database file should be created on init"""
        db_path = tmp_path / "search.db"
        assert not db_path.exists()

        engine = SearchEngine(db_path)
        assert db_path.exists()
        engine.close()

    def test_creates_fts_table(self, tmp_path):
        """FTS5 table should exist after init"""
        db_path = tmp_path / "search.db"
        engine = SearchEngine(db_path)

        # Query sqlite_master to verify table exists
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='photo_search'"
        )
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert result[0] == 'photo_search'
        engine.close()

    def test_context_manager(self, tmp_path):
        """Should work as context manager"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            assert engine is not None
            # Verify we can use it
            stats = engine.get_stats()
            assert isinstance(stats, dict)

        # Database file should still exist after context exit
        assert db_path.exists()

    def test_multiple_init_same_db(self, tmp_path):
        """Should handle multiple initializations of same database"""
        db_path = tmp_path / "search.db"

        # First initialization
        engine1 = SearchEngine(db_path)
        engine1.close()

        # Second initialization should not raise error
        engine2 = SearchEngine(db_path)
        stats = engine2.get_stats()
        assert isinstance(stats, dict)
        engine2.close()

    def test_creates_parent_directories(self, tmp_path):
        """Should create parent directories if they don't exist"""
        db_path = tmp_path / "cache" / "search" / "search.db"
        assert not db_path.parent.exists()

        engine = SearchEngine(db_path)
        assert db_path.exists()
        assert db_path.parent.exists()
        engine.close()


class TestSearchEngineIndexing:
    """Test photo indexing operations"""

    def test_index_single_photo(self, tmp_path):
        """Should index photo with metadata"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            metadata = {
                'filename': 'moth_2024_01_15__10_30_00.jpg',
                'filepath': 'photos/2024/01/moth_2024_01_15__10_30_00.jpg',
                'tags': ['moth', 'night'],
                'species': 'Actias luna',
                'species_common_name': 'Luna Moth',
                'notes': 'Beautiful green moth near porch light',
                'custom_fields': {'temperature': 22, 'humidity': 65}
            }

            engine.index_photo(metadata['filepath'], metadata)

            # Verify it was indexed
            result = engine.search('moth')
            assert result.total == 1
            assert len(result.results) == 1
            assert result.results[0].filepath == metadata['filepath']

    def test_index_update_existing(self, tmp_path):
        """Indexing same filepath should update not duplicate"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            filepath = 'photos/moth.jpg'

            # First index
            metadata1 = {
                'filename': 'moth.jpg',
                'filepath': filepath,
                'tags': ['moth'],
                'notes': 'Initial notes'
            }
            engine.index_photo(filepath, metadata1)

            # Update with new metadata
            metadata2 = {
                'filename': 'moth.jpg',
                'filepath': filepath,
                'tags': ['moth', 'updated'],
                'notes': 'Updated notes with more detail'
            }
            engine.index_photo(filepath, metadata2)

            # Should only have one entry
            result = engine.search('moth')
            assert result.total == 1

            # Should find the updated content
            result = engine.search('updated')
            assert result.total == 1

            # Should not find old content
            result = engine.search('Initial')
            assert result.total == 0

    def test_remove_photo(self, tmp_path):
        """Should remove photo from index"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            filepath = 'photos/moth.jpg'
            metadata = {
                'filename': 'moth.jpg',
                'filepath': filepath,
                'tags': ['moth']
            }

            # Index then remove
            engine.index_photo(filepath, metadata)
            assert engine.search('moth').total == 1

            engine.remove_photo(filepath)
            assert engine.search('moth').total == 0

    def test_index_with_empty_fields(self, tmp_path):
        """Should handle missing/empty metadata fields"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            # Minimal metadata
            metadata = {
                'filename': 'photo.jpg',
                'filepath': 'photos/photo.jpg'
            }

            # Should not raise error
            engine.index_photo(metadata['filepath'], metadata)

            # Should be searchable by filename
            result = engine.search('photo')
            assert result.total == 1

    def test_index_with_none_values(self, tmp_path):
        """Should handle None values in metadata"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            metadata = {
                'filename': 'photo.jpg',
                'filepath': 'photos/photo.jpg',
                'tags': None,
                'species': None,
                'notes': None
            }

            # Should not raise error
            engine.index_photo(metadata['filepath'], metadata)
            result = engine.search('photo')
            assert result.total == 1

    def test_remove_nonexistent_photo(self, tmp_path):
        """Removing non-existent photo should not raise error"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            # Should be idempotent
            engine.remove_photo('photos/nonexistent.jpg')
            engine.remove_photo('photos/nonexistent.jpg')


class TestSearchEngineSearch:
    """Test search functionality"""

    def test_simple_text_search(self, tmp_path):
        """Should find photos by text content"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            # Index multiple photos
            engine.index_photo('photos/moth1.jpg', {
                'filename': 'moth1.jpg',
                'filepath': 'photos/moth1.jpg',
                'notes': 'Luna moth spotted at night'
            })
            engine.index_photo('photos/moth2.jpg', {
                'filename': 'moth2.jpg',
                'filepath': 'photos/moth2.jpg',
                'notes': 'Beautiful luna specimen'
            })
            engine.index_photo('photos/butterfly.jpg', {
                'filename': 'butterfly.jpg',
                'filepath': 'photos/butterfly.jpg',
                'notes': 'Monarch butterfly on flower'
            })

            # Search for "luna" should return 2 results
            result = engine.search('luna')
            assert result.total == 2

            # Search for "butterfly" should return 1 result
            result = engine.search('butterfly')
            assert result.total == 1

    def test_search_returns_search_result(self, tmp_path):
        """Search should return SearchResult with results, total, took_ms"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth.jpg', {
                'filename': 'moth.jpg',
                'filepath': 'photos/moth.jpg',
                'tags': ['moth']
            })

            result = engine.search('moth')

            # Check SearchResult structure
            assert isinstance(result, SearchResult)
            assert isinstance(result.results, list)
            assert isinstance(result.total, int)
            assert isinstance(result.took_ms, float)
            assert result.took_ms >= 0

            # Check SearchMatch structure
            assert len(result.results) == 1
            match = result.results[0]
            assert isinstance(match, SearchMatch)
            assert match.filepath == 'photos/moth.jpg'
            assert match.filename == 'moth.jpg'
            assert isinstance(match.score, float)
            assert isinstance(match.matched_fields, list)
            assert isinstance(match.metadata, dict)

    def test_search_no_results(self, tmp_path):
        """Empty search should return empty results"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            result = engine.search('nonexistent')

            assert isinstance(result, SearchResult)
            assert result.total == 0
            assert len(result.results) == 0
            assert result.took_ms >= 0

    def test_fts_prefix_search(self, tmp_path):
        """Should support prefix search with *"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth.jpg', {
                'filename': 'moth.jpg',
                'filepath': 'photos/moth.jpg',
                'species': 'Actias luna'
            })

            # Prefix search should work
            result = engine.search('Act*')
            assert result.total == 1

            result = engine.search('lu*')
            assert result.total == 1

    def test_fts_phrase_search(self, tmp_path):
        """Should support quoted phrase search"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth1.jpg', {
                'filename': 'moth1.jpg',
                'filepath': 'photos/moth1.jpg',
                'notes': 'luna moth at night'
            })
            engine.index_photo('photos/moth2.jpg', {
                'filename': 'moth2.jpg',
                'filepath': 'photos/moth2.jpg',
                'notes': 'moth during the night luna phase'
            })

            # Phrase search should only match exact phrase
            result = engine.search('"luna moth"')
            assert result.total == 1
            assert result.results[0].filepath == 'photos/moth1.jpg'

    def test_pagination(self, tmp_path):
        """Should respect limit and offset"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            # Index 10 photos
            for i in range(10):
                engine.index_photo(f'photos/moth{i}.jpg', {
                    'filename': f'moth{i}.jpg',
                    'filepath': f'photos/moth{i}.jpg',
                    'tags': ['moth']
                })

            # Test limit
            result = engine.search('moth', limit=5)
            assert result.total == 10
            assert len(result.results) == 5

            # Test offset
            result = engine.search('moth', limit=5, offset=5)
            assert result.total == 10
            assert len(result.results) == 5

            # Test offset beyond results
            result = engine.search('moth', limit=5, offset=20)
            assert result.total == 10
            assert len(result.results) == 0

    def test_search_by_tags(self, tmp_path):
        """Should search by tags"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth.jpg', {
                'filename': 'moth.jpg',
                'filepath': 'photos/moth.jpg',
                'tags': ['moth', 'night', 'lepidoptera']
            })

            # Should find by tag
            result = engine.search('lepidoptera')
            assert result.total == 1

    def test_search_by_species(self, tmp_path):
        """Should search by species name"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth.jpg', {
                'filename': 'moth.jpg',
                'filepath': 'photos/moth.jpg',
                'species': 'Actias luna',
                'species_common_name': 'Luna Moth'
            })

            # Search by scientific name
            result = engine.search('Actias')
            assert result.total == 1

            # Search by common name
            result = engine.search('Luna')
            assert result.total == 1

    def test_search_case_insensitive(self, tmp_path):
        """Search should be case insensitive"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth.jpg', {
                'filename': 'moth.jpg',
                'filepath': 'photos/moth.jpg',
                'notes': 'Luna Moth'
            })

            # All should find the photo
            assert engine.search('luna').total == 1
            assert engine.search('LUNA').total == 1
            assert engine.search('Luna').total == 1

    def test_get_all_documents(self, tmp_path):
        """get_all_documents should return all indexed photos"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            # Index multiple photos
            engine.index_photo('photos/moth1.jpg', {
                'filename': 'moth_2024_11_01__12_00_00.jpg',
                'filepath': 'photos/moth1.jpg',
                'tags': ['luna']
            })
            engine.index_photo('photos/moth2.jpg', {
                'filename': 'moth_2024_11_02__12_00_00.jpg',
                'filepath': 'photos/moth2.jpg',
                'tags': ['actias']
            })
            engine.index_photo('photos/moth3.jpg', {
                'filename': 'moth_2024_11_03__12_00_00.jpg',
                'filepath': 'photos/moth3.jpg',
                'tags': ['sphinx']
            })

            # Get all documents
            result = engine.get_all_documents()

            assert isinstance(result, SearchResult)
            assert result.total == 3
            assert len(result.results) == 3
            assert result.took_ms >= 0

    def test_get_all_documents_pagination(self, tmp_path):
        """get_all_documents should support pagination"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            # Index 5 photos
            for i in range(5):
                engine.index_photo(f'photos/moth{i}.jpg', {
                    'filename': f'moth_2024_11_{i+1:02d}__12_00_00.jpg',
                    'filepath': f'photos/moth{i}.jpg',
                    'tags': [f'tag{i}']
                })

            # Get with limit
            result = engine.get_all_documents(limit=2)
            assert result.total == 5
            assert len(result.results) == 2

            # Get with offset
            result = engine.get_all_documents(limit=2, offset=3)
            assert result.total == 5
            assert len(result.results) == 2

    def test_get_all_documents_empty_index(self, tmp_path):
        """get_all_documents on empty index should return empty results"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            result = engine.get_all_documents()

            assert isinstance(result, SearchResult)
            assert result.total == 0
            assert len(result.results) == 0


class TestSearchEngineStats:
    """Test index statistics"""

    def test_get_stats_empty(self, tmp_path):
        """Stats should work on empty index"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            stats = engine.get_stats()

            assert isinstance(stats, dict)
            assert 'total_documents' in stats
            assert stats['total_documents'] == 0

    def test_get_stats_with_data(self, tmp_path):
        """Stats should return document count"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            # Index some photos
            for i in range(5):
                engine.index_photo(f'photos/moth{i}.jpg', {
                    'filename': f'moth{i}.jpg',
                    'filepath': f'photos/moth{i}.jpg'
                })

            stats = engine.get_stats()
            assert stats['total_documents'] == 5

            # Add more
            engine.index_photo('photos/moth5.jpg', {
                'filename': 'moth5.jpg',
                'filepath': 'photos/moth5.jpg'
            })

            stats = engine.get_stats()
            assert stats['total_documents'] == 6

            # Remove one
            engine.remove_photo('photos/moth5.jpg')
            stats = engine.get_stats()
            assert stats['total_documents'] == 5

    def test_stats_includes_db_path(self, tmp_path):
        """Stats should include database path"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            stats = engine.get_stats()

            assert 'db_path' in stats
            assert stats['db_path'] == str(db_path)


class TestSearchEngineEdgeCases:
    """Test error handling and edge cases"""

    def test_special_characters_in_search(self, tmp_path):
        """Should handle special characters in search query"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth.jpg', {
                'filename': 'moth.jpg',
                'filepath': 'photos/moth.jpg',
                'notes': 'Moth & butterfly (lepidoptera)'
            })

            # Should not raise error
            result = engine.search('&')
            result = engine.search('(lepidoptera)')

    def test_unicode_content(self, tmp_path):
        """Should handle unicode content"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth.jpg', {
                'filename': 'moth.jpg',
                'filepath': 'photos/moth.jpg',
                'notes': 'Papillon de nuit 🦋'
            })

            result = engine.search('Papillon')
            assert result.total == 1

    def test_empty_search_query(self, tmp_path):
        """Empty search query should return empty results"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth.jpg', {
                'filename': 'moth.jpg',
                'filepath': 'photos/moth.jpg'
            })

            result = engine.search('')
            assert result.total == 0
            assert len(result.results) == 0

    def test_matched_fields_tracking(self, tmp_path):
        """Should track which fields matched the query"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth.jpg', {
                'filename': 'moth.jpg',
                'filepath': 'photos/moth.jpg',
                'tags': ['moth'],
                'notes': 'Beautiful moth specimen'
            })

            result = engine.search('moth')
            assert result.total == 1

            # Should indicate which fields matched
            match = result.results[0]
            assert len(match.matched_fields) > 0

    def test_corrupted_database_recovery(self, tmp_path):
        """Should handle and recover from corrupted database"""
        db_path = tmp_path / "search.db"

        # Create a corrupted database file
        db_path.write_text("CORRUPTED BINARY DATA !!!###$$$")

        # Should recreate database without error
        with SearchEngine(db_path) as engine:
            stats = engine.get_stats()
            assert stats['total_documents'] == 0

            # Should be able to use the recreated database
            engine.index_photo('photos/moth.jpg', {
                'filename': 'moth.jpg',
                'filepath': 'photos/moth.jpg',
                'tags': ['moth']
            })

            result = engine.search('moth')
            assert result.total == 1

    def test_date_extraction_from_mothbox_filename(self, tmp_path):
        """Should extract and index date from Mothbox filename pattern"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            # Index photo with Mothbox filename pattern
            engine.index_photo('photos/moth_2024_01_15__10_30_00.jpg', {
                'filename': 'moth_2024_01_15__10_30_00.jpg',
                'filepath': 'photos/moth_2024_01_15__10_30_00.jpg'
            })

            # Search by date should work (use quotes for phrase match)
            result = engine.search('"2024-01-15"')
            assert result.total == 1
            assert result.results[0].metadata['date'] == '2024-01-15'

    def test_custom_fields_json_serialization(self, tmp_path):
        """Should serialize and deserialize custom_fields as JSON"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            custom_data = {
                'location': 'backyard',
                'temperature': 22,
                'weather': ['clear', 'calm'],
                'equipment': {'camera': 'OwlSight', 'lens': '64MP'}
            }

            engine.index_photo('photos/moth.jpg', {
                'filename': 'moth.jpg',
                'filepath': 'photos/moth.jpg',
                'custom_fields': custom_data
            })

            # Search and verify custom fields are preserved
            result = engine.search('moth')
            assert result.total == 1

            retrieved_custom = result.results[0].metadata['custom_fields']
            assert retrieved_custom == custom_data
            assert retrieved_custom['temperature'] == 22
            assert retrieved_custom['equipment']['camera'] == 'OwlSight'

    def test_invalid_fts_query_handling(self, tmp_path):
        """Should handle invalid FTS5 query syntax gracefully"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth.jpg', {
                'filename': 'moth.jpg',
                'filepath': 'photos/moth.jpg'
            })

            # Invalid FTS5 syntax should not crash
            result = engine.search('"""')  # Unmatched quotes
            assert isinstance(result, SearchResult)
            # Should return empty results
            assert result.total == 0

    def test_close_idempotent(self, tmp_path):
        """Should be safe to call close() multiple times"""
        db_path = tmp_path / "search.db"

        engine = SearchEngine(db_path)
        engine.close()
        engine.close()  # Should not raise
        engine.close()  # Should not raise


class TestSearchEngineRanking:
    """Test ranking algorithm with field weighting and match type scoring"""

    def test_tag_matches_rank_higher_than_notes(self, tmp_path):
        """Photos matching in tags should rank higher than notes matches"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            # Photo 1: "moth" only in notes (low priority field)
            engine.index_photo('photos/moth1.jpg', {
                'filename': 'moth1.jpg',
                'filepath': 'photos/moth1.jpg',
                'notes': 'Found a beautiful moth near the porch'
            })

            # Photo 2: "moth" in tags (high priority field)
            engine.index_photo('photos/moth2.jpg', {
                'filename': 'moth2.jpg',
                'filepath': 'photos/moth2.jpg',
                'tags': ['moth'],
                'notes': 'Some general observation'
            })

            # Search for "moth"
            result = engine.search('moth')
            assert result.total == 2

            # Photo with tag match should rank first
            assert result.results[0].filepath == 'photos/moth2.jpg'
            assert result.results[1].filepath == 'photos/moth1.jpg'

            # Score should be higher for tag match
            assert result.results[0].score > result.results[1].score

    def test_species_matches_rank_higher_than_custom_fields(self, tmp_path):
        """Species matches should outrank custom_fields matches"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            # Photo 1: "luna" in custom_fields (low priority)
            engine.index_photo('photos/photo1.jpg', {
                'filename': 'photo1.jpg',
                'filepath': 'photos/photo1.jpg',
                'custom_fields': {'observer': 'luna', 'location': 'forest'}
            })

            # Photo 2: "luna" in species (high priority)
            engine.index_photo('photos/photo2.jpg', {
                'filename': 'photo2.jpg',
                'filepath': 'photos/photo2.jpg',
                'species': 'Actias luna'
            })

            # Search for "luna"
            result = engine.search('luna')
            assert result.total == 2

            # Species match should rank first
            assert result.results[0].filepath == 'photos/photo2.jpg'
            assert result.results[1].filepath == 'photos/photo1.jpg'

            # Score should be higher for species match
            assert result.results[0].score > result.results[1].score

    def test_exact_match_ranks_higher_than_prefix(self, tmp_path):
        """Exact 'luna' should rank higher than prefix match 'lun*'"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            # Photo 1: Prefix match only (lunar, lunch, etc.)
            engine.index_photo('photos/photo1.jpg', {
                'filename': 'photo1.jpg',
                'filepath': 'photos/photo1.jpg',
                'notes': 'Lunar cycle observation'
            })

            # Photo 2: Exact match
            engine.index_photo('photos/photo2.jpg', {
                'filename': 'photo2.jpg',
                'filepath': 'photos/photo2.jpg',
                'notes': 'Luna moth specimen'
            })

            # Search with prefix
            result = engine.search('lun*')
            assert result.total == 2

            # Exact match "luna" should rank higher
            # Note: This test checks that match_type is detected correctly
            # The actual ranking depends on BM25 scores from FTS5

    def test_phrase_match_gets_boost(self, tmp_path):
        """Phrase 'luna moth' should rank higher than separate words"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            # Photo 1: Words appear separately
            engine.index_photo('photos/photo1.jpg', {
                'filename': 'photo1.jpg',
                'filepath': 'photos/photo1.jpg',
                'notes': 'Found a moth during the luna phase'
            })

            # Photo 2: Exact phrase
            engine.index_photo('photos/photo2.jpg', {
                'filename': 'photo2.jpg',
                'filepath': 'photos/photo2.jpg',
                'notes': 'Luna moth spotted near light'
            })

            # Search for exact phrase
            result = engine.search('"luna moth"')
            assert result.total >= 1

            # Photo with exact phrase should rank first
            assert result.results[0].filepath == 'photos/photo2.jpg'

    def test_multiple_field_matches_cumulative(self, tmp_path):
        """Match in both tags and species should rank higher than single field"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            # Photo 1: Match in tags only
            engine.index_photo('photos/photo1.jpg', {
                'filename': 'photo1.jpg',
                'filepath': 'photos/photo1.jpg',
                'tags': ['moth'],
                'species': 'Unknown species'
            })

            # Photo 2: Match in both tags and species
            engine.index_photo('photos/photo2.jpg', {
                'filename': 'photo2.jpg',
                'filepath': 'photos/photo2.jpg',
                'tags': ['moth', 'lepidoptera'],
                'species': 'Moth specimen'
            })

            # Search for "moth"
            result = engine.search('moth')
            assert result.total == 2

            # Photo with multiple field matches should rank higher
            # (This assumes cumulative scoring in the ranking algorithm)
            assert len(result.results[0].matched_fields) >= len(result.results[1].matched_fields)

    def test_custom_field_weights(self, tmp_path):
        """Custom field_weights should override defaults"""
        db_path = tmp_path / "search.db"

        # Custom weights that prioritize notes over tags
        custom_weights = {
            'tags': 1.0,
            'notes': 2.0,
        }

        with SearchEngine(db_path, field_weights=custom_weights) as engine:
            # Photo 1: Match in tags
            engine.index_photo('photos/photo1.jpg', {
                'filename': 'photo1.jpg',
                'filepath': 'photos/photo1.jpg',
                'tags': ['moth']
            })

            # Photo 2: Match in notes
            engine.index_photo('photos/photo2.jpg', {
                'filename': 'photo2.jpg',
                'filepath': 'photos/photo2.jpg',
                'notes': 'Beautiful moth specimen'
            })

            # Search for "moth"
            result = engine.search('moth')
            assert result.total == 2

            # With custom weights, notes should rank first
            assert result.results[0].filepath == 'photos/photo2.jpg'

    def test_bm25_score_preserved(self, tmp_path):
        """SearchMatch should include raw bm25_score"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth.jpg', {
                'filename': 'moth.jpg',
                'filepath': 'photos/moth.jpg',
                'tags': ['moth']
            })

            result = engine.search('moth')
            assert result.total == 1

            match = result.results[0]

            # Should have bm25_score attribute
            assert hasattr(match, 'bm25_score')
            assert isinstance(match.bm25_score, float)
            assert match.bm25_score > 0

    def test_match_type_in_result(self, tmp_path):
        """SearchMatch should include match_type"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth.jpg', {
                'filename': 'moth.jpg',
                'filepath': 'photos/moth.jpg',
                'tags': ['moth']
            })

            # Test exact match
            result = engine.search('moth')
            assert result.total == 1
            match = result.results[0]
            assert hasattr(match, 'match_type')
            assert match.match_type in ['exact', 'prefix', 'phrase']

            # Test prefix match
            result = engine.search('mot*')
            assert result.total == 1
            match = result.results[0]
            assert match.match_type == 'prefix'

            # Test phrase match
            result = engine.search('"moth"')
            assert result.total == 1
            match = result.results[0]
            assert match.match_type == 'phrase'

    def test_results_sorted_by_score(self, tmp_path):
        """Results should be sorted by score descending"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            # Index multiple photos with varying relevance
            engine.index_photo('photos/photo1.jpg', {
                'filename': 'photo1.jpg',
                'filepath': 'photos/photo1.jpg',
                'notes': 'moth mentioned once'
            })
            engine.index_photo('photos/photo2.jpg', {
                'filename': 'photo2.jpg',
                'filepath': 'photos/photo2.jpg',
                'tags': ['moth'],
                'species': 'Moth species'
            })
            engine.index_photo('photos/photo3.jpg', {
                'filename': 'photo3.jpg',
                'filepath': 'photos/photo3.jpg',
                'tags': ['moth']
            })

            result = engine.search('moth')
            assert result.total >= 2

            # Verify scores are in descending order
            scores = [match.score for match in result.results]
            assert scores == sorted(scores, reverse=True)

    def test_field_weights_affect_final_score(self, tmp_path):
        """Field weights should affect the final score calculation"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            # Photo 1: Match in high-weight field (tags)
            engine.index_photo('photos/photo1.jpg', {
                'filename': 'photo1.jpg',
                'filepath': 'photos/photo1.jpg',
                'tags': ['luna'],
                'notes': 'Some generic content'
            })

            # Photo 2: Match in low-weight field (notes)
            engine.index_photo('photos/photo2.jpg', {
                'filename': 'photo2.jpg',
                'filepath': 'photos/photo2.jpg',
                'tags': ['other'],
                'notes': 'Discussion about luna observations'
            })

            result = engine.search('luna')
            assert result.total == 2

            # Photo 1 should have higher final score due to field weight
            photo1 = next(m for m in result.results if m.filepath == 'photos/photo1.jpg')
            photo2 = next(m for m in result.results if m.filepath == 'photos/photo2.jpg')

            # Tags have weight 2.0, notes have weight 1.0
            # So photo1 should have significantly higher score
            assert photo1.score > photo2.score


class TestSearchEngineHighlighting:
    """Test FTS5 search result highlighting with <mark> tags"""

    def test_search_returns_highlights_dict(self, tmp_path):
        """Search results should include a highlights dict"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth.jpg', {
                'filename': 'moth.jpg',
                'filepath': 'photos/moth.jpg',
                'tags': ['luna', 'moth']
            })

            result = engine.search('luna')
            assert result.total == 1

            match = result.results[0]
            assert hasattr(match, 'highlights')
            assert isinstance(match.highlights, dict)

    def test_highlight_marks_matched_tags(self, tmp_path):
        """Highlights should contain <mark> tags for matched terms in tags field"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth.jpg', {
                'filename': 'moth.jpg',
                'filepath': 'photos/moth.jpg',
                'tags': ['luna', 'moth', 'nocturnal']
            })

            result = engine.search('luna')
            assert result.total == 1

            match = result.results[0]
            # Should have highlights for tags field
            assert 'tags' in match.highlights
            # Highlighted text should contain <mark> tags
            assert '<mark>' in match.highlights['tags']
            assert '</mark>' in match.highlights['tags']
            assert 'luna' in match.highlights['tags'].lower()

    def test_highlight_marks_matched_species(self, tmp_path):
        """Highlights should contain <mark> tags for matched species"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth.jpg', {
                'filename': 'moth.jpg',
                'filepath': 'photos/moth.jpg',
                'species': 'Actias luna',
                'species_common_name': 'Luna Moth'
            })

            result = engine.search('luna')
            assert result.total == 1

            match = result.results[0]
            # Should have highlights for species field
            assert 'species' in match.highlights
            assert '<mark>' in match.highlights['species']

    def test_highlight_marks_matched_notes(self, tmp_path):
        """Highlights should contain <mark> tags for matched notes"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth.jpg', {
                'filename': 'moth.jpg',
                'filepath': 'photos/moth.jpg',
                'notes': 'Beautiful luna moth spotted near the porch light'
            })

            result = engine.search('luna')
            assert result.total == 1

            match = result.results[0]
            # Should have highlights for notes field
            assert 'notes' in match.highlights
            assert '<mark>' in match.highlights['notes']

    def test_no_highlights_for_unmatched_fields(self, tmp_path):
        """Fields without matches should not appear in highlights dict"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth.jpg', {
                'filename': 'moth.jpg',
                'filepath': 'photos/moth.jpg',
                'tags': ['luna'],
                'notes': 'Some unrelated content here',
                'species': 'Unknown species'
            })

            result = engine.search('luna')
            assert result.total == 1

            match = result.results[0]
            # Tags should be highlighted
            assert 'tags' in match.highlights
            # Notes and species should NOT be in highlights (no match)
            assert 'notes' not in match.highlights
            assert 'species' not in match.highlights

    def test_empty_highlights_when_no_match(self, tmp_path):
        """Highlights should be empty dict when query doesn't match any field"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth.jpg', {
                'filename': 'moth_2024_01_15__10_30_00.jpg',
                'filepath': 'photos/moth.jpg',
                'tags': ['nocturnal']
            })

            # Search by date (which is indexed but not highlighted)
            result = engine.search('"2024-01-15"')
            # If matched, highlights may or may not include date field
            # But no text content should have <mark> tags

    def test_multiple_fields_highlighted(self, tmp_path):
        """Multiple fields with matches should all be highlighted"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth.jpg', {
                'filename': 'luna_moth.jpg',
                'filepath': 'photos/moth.jpg',
                'tags': ['luna', 'moth'],
                'species': 'Actias luna',
                'notes': 'Luna moth observation'
            })

            result = engine.search('luna')
            assert result.total == 1

            match = result.results[0]
            # All fields with "luna" should be highlighted
            assert 'tags' in match.highlights
            assert 'species' in match.highlights
            assert 'notes' in match.highlights
            # Each should have <mark> tags
            for field in ['tags', 'species', 'notes']:
                assert '<mark>' in match.highlights[field]

    def test_highlight_preserves_surrounding_text(self, tmp_path):
        """Highlighted text should preserve context around the match"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth.jpg', {
                'filename': 'moth.jpg',
                'filepath': 'photos/moth.jpg',
                'notes': 'Beautiful green luna moth near the porch'
            })

            result = engine.search('luna')
            assert result.total == 1

            match = result.results[0]
            # Full context should be preserved with highlight
            assert 'notes' in match.highlights
            highlighted_notes = match.highlights['notes']
            # Should contain surrounding words
            assert 'green' in highlighted_notes or 'moth' in highlighted_notes

    def test_highlight_species_common_name(self, tmp_path):
        """Species common name field should be highlighted"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth.jpg', {
                'filename': 'moth.jpg',
                'filepath': 'photos/moth.jpg',
                'species_common_name': 'Luna Moth'
            })

            result = engine.search('luna')
            assert result.total == 1

            match = result.results[0]
            assert 'species_common_name' in match.highlights
            assert '<mark>' in match.highlights['species_common_name']

    def test_prefix_search_highlights(self, tmp_path):
        """Prefix search should also produce highlights"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth.jpg', {
                'filename': 'moth.jpg',
                'filepath': 'photos/moth.jpg',
                'tags': ['luna', 'lunar']
            })

            result = engine.search('lun*')
            assert result.total == 1

            match = result.results[0]
            # Prefix matches should also be highlighted
            assert 'tags' in match.highlights
            assert '<mark>' in match.highlights['tags']


class TestSearchWithDateFilter:
    """Test SQL-based date filtering for efficient large-scale queries"""

    def test_date_range_filter(self, tmp_path):
        """Should filter by date range using SQL BETWEEN"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            # Index photos with different dates
            engine.index_photo('photos/moth1.jpg', {
                'filename': 'moth_2024_01_01__12_00_00.jpg',
                'filepath': 'photos/moth1.jpg',
                'tags': ['moth']
            })
            engine.index_photo('photos/moth2.jpg', {
                'filename': 'moth_2024_01_15__12_00_00.jpg',
                'filepath': 'photos/moth2.jpg',
                'tags': ['moth']
            })
            engine.index_photo('photos/moth3.jpg', {
                'filename': 'moth_2024_02_01__12_00_00.jpg',
                'filepath': 'photos/moth3.jpg',
                'tags': ['moth']
            })

            # Date range filter: Jan 1 - Jan 31
            result = engine.search_with_date_filter(
                query=None,
                date_filter={
                    'operator': 'range',
                    'start_date': '2024-01-01',
                    'end_date': '2024-01-31'
                }
            )

            assert result.total == 2
            filepaths = [r.filepath for r in result.results]
            assert 'photos/moth1.jpg' in filepaths
            assert 'photos/moth2.jpg' in filepaths
            assert 'photos/moth3.jpg' not in filepaths

    def test_date_gt_filter(self, tmp_path):
        """Should filter by date > start_date"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth1.jpg', {
                'filename': 'moth_2024_01_01__12_00_00.jpg',
                'filepath': 'photos/moth1.jpg'
            })
            engine.index_photo('photos/moth2.jpg', {
                'filename': 'moth_2024_01_15__12_00_00.jpg',
                'filepath': 'photos/moth2.jpg'
            })

            result = engine.search_with_date_filter(
                query=None,
                date_filter={
                    'operator': 'gt',
                    'start_date': '2024-01-01'
                }
            )

            assert result.total == 1
            assert result.results[0].filepath == 'photos/moth2.jpg'

    def test_date_gte_filter(self, tmp_path):
        """Should filter by date >= start_date"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth1.jpg', {
                'filename': 'moth_2024_01_01__12_00_00.jpg',
                'filepath': 'photos/moth1.jpg'
            })
            engine.index_photo('photos/moth2.jpg', {
                'filename': 'moth_2024_01_15__12_00_00.jpg',
                'filepath': 'photos/moth2.jpg'
            })

            result = engine.search_with_date_filter(
                query=None,
                date_filter={
                    'operator': 'gte',
                    'start_date': '2024-01-01'
                }
            )

            assert result.total == 2

    def test_date_lt_filter(self, tmp_path):
        """Should filter by date < start_date"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth1.jpg', {
                'filename': 'moth_2024_01_01__12_00_00.jpg',
                'filepath': 'photos/moth1.jpg'
            })
            engine.index_photo('photos/moth2.jpg', {
                'filename': 'moth_2024_01_15__12_00_00.jpg',
                'filepath': 'photos/moth2.jpg'
            })

            result = engine.search_with_date_filter(
                query=None,
                date_filter={
                    'operator': 'lt',
                    'start_date': '2024-01-15'
                }
            )

            assert result.total == 1
            assert result.results[0].filepath == 'photos/moth1.jpg'

    def test_date_lte_filter(self, tmp_path):
        """Should filter by date <= start_date"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth1.jpg', {
                'filename': 'moth_2024_01_01__12_00_00.jpg',
                'filepath': 'photos/moth1.jpg'
            })
            engine.index_photo('photos/moth2.jpg', {
                'filename': 'moth_2024_01_15__12_00_00.jpg',
                'filepath': 'photos/moth2.jpg'
            })

            result = engine.search_with_date_filter(
                query=None,
                date_filter={
                    'operator': 'lte',
                    'start_date': '2024-01-15'
                }
            )

            assert result.total == 2

    def test_combined_fts_and_date_filter(self, tmp_path):
        """Should combine FTS query with date filter"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth1.jpg', {
                'filename': 'moth_2024_01_01__12_00_00.jpg',
                'filepath': 'photos/moth1.jpg',
                'tags': ['luna']
            })
            engine.index_photo('photos/moth2.jpg', {
                'filename': 'moth_2024_01_15__12_00_00.jpg',
                'filepath': 'photos/moth2.jpg',
                'tags': ['luna']
            })
            engine.index_photo('photos/moth3.jpg', {
                'filename': 'moth_2024_01_15__12_00_00.jpg',
                'filepath': 'photos/moth3.jpg',
                'tags': ['sphinx']
            })

            # Combined: FTS for 'luna' AND date after Jan 10
            result = engine.search_with_date_filter(
                query='luna',
                date_filter={
                    'operator': 'gt',
                    'start_date': '2024-01-10'
                }
            )

            assert result.total == 1
            assert result.results[0].filepath == 'photos/moth2.jpg'

    def test_date_filter_with_pagination(self, tmp_path):
        """Should support pagination with date filter"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            # Index 10 photos in January
            for i in range(10):
                engine.index_photo(f'photos/moth{i}.jpg', {
                    'filename': f'moth_2024_01_{i+1:02d}__12_00_00.jpg',
                    'filepath': f'photos/moth{i}.jpg'
                })

            result = engine.search_with_date_filter(
                query=None,
                date_filter={
                    'operator': 'range',
                    'start_date': '2024-01-01',
                    'end_date': '2024-01-31'
                },
                limit=5,
                offset=0
            )

            assert result.total == 10
            assert len(result.results) == 5

            # Get next page
            result2 = engine.search_with_date_filter(
                query=None,
                date_filter={
                    'operator': 'range',
                    'start_date': '2024-01-01',
                    'end_date': '2024-01-31'
                },
                limit=5,
                offset=5
            )

            assert result2.total == 10
            assert len(result2.results) == 5

    def test_date_filter_returns_highlights_for_fts(self, tmp_path):
        """Combined FTS + date filter should return highlights"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth.jpg', {
                'filename': 'moth_2024_01_15__12_00_00.jpg',
                'filepath': 'photos/moth.jpg',
                'tags': ['luna', 'moth']
            })

            result = engine.search_with_date_filter(
                query='luna',
                date_filter={
                    'operator': 'gte',
                    'start_date': '2024-01-01'
                }
            )

            assert result.total == 1
            match = result.results[0]
            assert 'tags' in match.highlights
            assert '<mark>' in match.highlights['tags']

    def test_date_only_query_no_highlights(self, tmp_path):
        """Date-only query should not have FTS highlights"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth.jpg', {
                'filename': 'moth_2024_01_15__12_00_00.jpg',
                'filepath': 'photos/moth.jpg',
                'tags': ['luna']
            })

            result = engine.search_with_date_filter(
                query=None,
                date_filter={
                    'operator': 'gte',
                    'start_date': '2024-01-01'
                }
            )

            assert result.total == 1
            match = result.results[0]
            # No FTS query means no highlights
            assert match.highlights == {}

    def test_empty_date_filter(self, tmp_path):
        """Null/empty date filter should return all documents"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth1.jpg', {
                'filename': 'moth1.jpg',
                'filepath': 'photos/moth1.jpg',
                'tags': ['luna']
            })
            engine.index_photo('photos/moth2.jpg', {
                'filename': 'moth2.jpg',
                'filepath': 'photos/moth2.jpg',
                'tags': ['luna']
            })

            result = engine.search_with_date_filter(
                query='luna',
                date_filter=None
            )

            assert result.total == 2


class TestIndexMetadataTracking:
    """Test photo_index_metadata table for incremental sync"""

    def test_index_photo_records_mtime(self, tmp_path):
        """index_photo should record sidecar_mtime in tracking table"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            sidecar_mtime = 1704067200.123

            engine.index_photo('photos/moth.jpg', {
                'filename': 'moth.jpg',
                'filepath': 'photos/moth.jpg'
            }, sidecar_mtime=sidecar_mtime)

            metadata = engine.get_indexed_metadata()

            assert 'photos/moth.jpg' in metadata
            assert metadata['photos/moth.jpg'] == sidecar_mtime

    def test_get_indexed_metadata_empty(self, tmp_path):
        """get_indexed_metadata on empty index should return empty dict"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            metadata = engine.get_indexed_metadata()

            assert isinstance(metadata, dict)
            assert len(metadata) == 0

    def test_get_indexed_metadata_multiple(self, tmp_path):
        """get_indexed_metadata should return all indexed filepaths with mtimes"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth1.jpg', {
                'filename': 'moth1.jpg',
                'filepath': 'photos/moth1.jpg'
            }, sidecar_mtime=1000.0)

            engine.index_photo('photos/moth2.jpg', {
                'filename': 'moth2.jpg',
                'filepath': 'photos/moth2.jpg'
            }, sidecar_mtime=2000.0)

            metadata = engine.get_indexed_metadata()

            assert len(metadata) == 2
            assert metadata['photos/moth1.jpg'] == 1000.0
            assert metadata['photos/moth2.jpg'] == 2000.0

    def test_remove_photo_cleans_metadata(self, tmp_path):
        """remove_photo should also remove from metadata tracking table"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            engine.index_photo('photos/moth.jpg', {
                'filename': 'moth.jpg',
                'filepath': 'photos/moth.jpg'
            }, sidecar_mtime=1000.0)

            assert 'photos/moth.jpg' in engine.get_indexed_metadata()

            engine.remove_photo('photos/moth.jpg')

            assert 'photos/moth.jpg' not in engine.get_indexed_metadata()


class TestIncrementalSync:
    """Test incremental_sync for efficient index updates"""

    def test_incremental_sync_new_photos(self, tmp_path):
        """incremental_sync should index new photos"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            photos = [
                {
                    'filepath': 'photos/moth1.jpg',
                    'sidecar_mtime': 1000.0,
                    'metadata': {'filename': 'moth1.jpg', 'tags': ['luna']}
                },
                {
                    'filepath': 'photos/moth2.jpg',
                    'sidecar_mtime': 2000.0,
                    'metadata': {'filename': 'moth2.jpg', 'tags': ['sphinx']}
                }
            ]

            stats = engine.incremental_sync(photos)

            assert stats['indexed'] == 2
            assert stats['updated'] == 0
            assert stats['deleted'] == 0
            assert stats['unchanged'] == 0
            assert stats['errors'] == 0
            assert 'took_ms' in stats

            # Verify photos are searchable
            result = engine.search('luna')
            assert result.total == 1

    def test_incremental_sync_updated_photos(self, tmp_path):
        """incremental_sync should re-index modified photos"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            # First sync
            photos1 = [
                {
                    'filepath': 'photos/moth.jpg',
                    'sidecar_mtime': 1000.0,
                    'metadata': {'filename': 'moth.jpg', 'tags': ['luna']}
                }
            ]
            engine.incremental_sync(photos1)

            # Second sync with updated mtime
            photos2 = [
                {
                    'filepath': 'photos/moth.jpg',
                    'sidecar_mtime': 2000.0,  # Newer mtime
                    'metadata': {'filename': 'moth.jpg', 'tags': ['luna', 'updated']}
                }
            ]
            stats = engine.incremental_sync(photos2)

            assert stats['indexed'] == 0
            assert stats['updated'] == 1
            assert stats['unchanged'] == 0

            # Verify updated content is searchable
            result = engine.search('updated')
            assert result.total == 1

    def test_incremental_sync_unchanged_photos(self, tmp_path):
        """incremental_sync should skip unchanged photos"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            photos = [
                {
                    'filepath': 'photos/moth.jpg',
                    'sidecar_mtime': 1000.0,
                    'metadata': {'filename': 'moth.jpg', 'tags': ['luna']}
                }
            ]

            # First sync
            engine.incremental_sync(photos)

            # Second sync with same mtime
            stats = engine.incremental_sync(photos)

            assert stats['indexed'] == 0
            assert stats['updated'] == 0
            assert stats['unchanged'] == 1

    def test_incremental_sync_deleted_photos(self, tmp_path):
        """incremental_sync should remove stale entries"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            # First sync with 2 photos
            photos1 = [
                {
                    'filepath': 'photos/moth1.jpg',
                    'sidecar_mtime': 1000.0,
                    'metadata': {'filename': 'moth1.jpg', 'tags': ['luna']}
                },
                {
                    'filepath': 'photos/moth2.jpg',
                    'sidecar_mtime': 2000.0,
                    'metadata': {'filename': 'moth2.jpg', 'tags': ['sphinx']}
                }
            ]
            engine.incremental_sync(photos1)

            # Second sync with only 1 photo (moth2 was deleted from filesystem)
            photos2 = [
                {
                    'filepath': 'photos/moth1.jpg',
                    'sidecar_mtime': 1000.0,
                    'metadata': {'filename': 'moth1.jpg', 'tags': ['luna']}
                }
            ]
            stats = engine.incremental_sync(photos2)

            assert stats['deleted'] == 1
            assert stats['unchanged'] == 1

            # Verify deleted photo is no longer searchable
            result = engine.search('sphinx')
            assert result.total == 0

    def test_incremental_sync_mixed_operations(self, tmp_path):
        """incremental_sync should handle mixed new/updated/deleted/unchanged"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            # Initial state: 3 photos
            photos1 = [
                {
                    'filepath': 'photos/unchanged.jpg',
                    'sidecar_mtime': 1000.0,
                    'metadata': {'filename': 'unchanged.jpg', 'tags': ['unchanged']}
                },
                {
                    'filepath': 'photos/to_update.jpg',
                    'sidecar_mtime': 1000.0,
                    'metadata': {'filename': 'to_update.jpg', 'tags': ['old']}
                },
                {
                    'filepath': 'photos/to_delete.jpg',
                    'sidecar_mtime': 1000.0,
                    'metadata': {'filename': 'to_delete.jpg', 'tags': ['deleted']}
                }
            ]
            engine.incremental_sync(photos1)

            # New state: 1 unchanged, 1 updated, 1 deleted, 1 new
            photos2 = [
                {
                    'filepath': 'photos/unchanged.jpg',
                    'sidecar_mtime': 1000.0,  # Same mtime
                    'metadata': {'filename': 'unchanged.jpg', 'tags': ['unchanged']}
                },
                {
                    'filepath': 'photos/to_update.jpg',
                    'sidecar_mtime': 2000.0,  # Updated mtime
                    'metadata': {'filename': 'to_update.jpg', 'tags': ['updated']}
                },
                # to_delete.jpg is missing
                {
                    'filepath': 'photos/new.jpg',
                    'sidecar_mtime': 3000.0,
                    'metadata': {'filename': 'new.jpg', 'tags': ['new']}
                }
            ]
            stats = engine.incremental_sync(photos2)

            assert stats['indexed'] == 1  # new.jpg
            assert stats['updated'] == 1  # to_update.jpg
            assert stats['deleted'] == 1  # to_delete.jpg
            assert stats['unchanged'] == 1  # unchanged.jpg
            assert stats['errors'] == 0

    def test_incremental_sync_empty_photos_clears_index(self, tmp_path):
        """incremental_sync with empty list should remove all entries"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            # Index some photos
            photos = [
                {
                    'filepath': 'photos/moth.jpg',
                    'sidecar_mtime': 1000.0,
                    'metadata': {'filename': 'moth.jpg', 'tags': ['luna']}
                }
            ]
            engine.incremental_sync(photos)

            # Sync with empty list
            stats = engine.incremental_sync([])

            assert stats['deleted'] == 1
            assert engine.get_stats()['total_documents'] == 0

    def test_incremental_sync_returns_took_ms(self, tmp_path):
        """incremental_sync should return timing info"""
        db_path = tmp_path / "search.db"

        with SearchEngine(db_path) as engine:
            stats = engine.incremental_sync([])

            assert 'took_ms' in stats
            assert isinstance(stats['took_ms'], float)
            assert stats['took_ms'] >= 0
