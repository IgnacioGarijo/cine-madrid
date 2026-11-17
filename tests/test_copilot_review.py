import unittest
from unittest.mock import patch

from src.copilot_review import eligible, fingerprint, prepare, reviewed_identity, validate
from src.core import Incidents
from src.tmdb import enrich


class CopilotReviewTests(unittest.TestCase):
    def setUp(self):
        self.movie = {'id': 'cinema:1', 'title': 'Hope', 'director': 'Na Hong-Jin',
                      'duration_minutes': 160, 'identity_status': 'needs_review',
                      'identity_candidates': [{'id': 'tmdb:1'}]}
        self.candidate = {'id': 'tmdb:1', 'title': 'Hope', 'original_title': '호프',
                          'aliases': [], 'runtime': 157, 'year': 2026, 'director': '나홍진',
                          'source_url': 'https://www.themoviedb.org/movie/1'}
        self.cache = {'movies': {'1': self.candidate}}
        self.public = {'movies': [self.movie]}

    def test_accepts_only_a_real_candidate_with_corrobating_runtime_and_title(self):
        batch = prepare(self.public, self.cache)
        key = fingerprint(self.movie)
        result = validate({'decisions': [{'key': key, 'candidate_id': 'tmdb:1', 'match': True}]}, batch, self.public, self.cache, {})
        self.assertEqual(result[key]['candidate_id'], 'tmdb:1')
        identity, evidence = reviewed_identity(self.movie, self.movie['identity_candidates'], self.cache, result)
        self.assertEqual(identity['id'], 'tmdb:1')
        self.assertEqual(evidence['duration_difference_minutes'], 3)
        self.movie['duration_minutes'] = 140
        self.assertIsNone(reviewed_identity(self.movie, self.movie['identity_candidates'], self.cache, result)[0])

    def test_hallucinated_candidates_and_ambiguous_titles_are_not_accepted(self):
        batch = prepare(self.public, self.cache)
        key = fingerprint(self.movie)
        self.assertEqual(validate({'decisions': [{'key': key, 'candidate_id': 'tmdb:999', 'match': True}]}, batch, self.public, self.cache, {}), {})
        other = dict(self.candidate, id='tmdb:2')
        self.cache['movies']['2'] = other
        self.movie['identity_candidates'].append({'id': 'tmdb:2'})
        self.assertEqual(len(eligible(self.movie, self.movie['identity_candidates'], self.cache)), 2)
        self.assertEqual(validate({'decisions': [{'key': key, 'candidate_id': 'tmdb:1', 'match': True}]}, batch, self.public, self.cache, {}), {})

    def test_does_not_overwrite_previous_on_bad_or_negative_response(self):
        batch = prepare(self.public, self.cache)
        previous = {'old': {'candidate_id': 'tmdb:4'}}
        self.assertEqual(validate({'decisions': []}, batch, self.public, self.cache, previous), previous)
        with self.assertRaises(ValueError):
            validate({}, batch, self.public, self.cache, previous)

    def test_reviewed_identity_flows_into_classification(self):
        self.candidate.update(tmdb_id=1, directors=['나홍진'], releases=[{'country': 'ES', 'type': 3, 'date': '2026-11-01'}])
        session = {'movie_id': 'cinema:1', 'start': '2026-11-17T18:00:00+01:00', 'category': 'unclassified'}
        decision = {fingerprint(self.movie): {'candidate_id': 'tmdb:1', 'reviewed_at': '2026-11-17'}}
        with patch('src.tmdb.Client') as client:
            client.return_value.resolve.return_value = (None, 'metadata_mismatch', [{'id': 'tmdb:1'}])
            client.return_value.requests = 0
            enrich([self.movie], [session], self.cache, {'current_release_max_days': 180, 'repertory_min_days': 365}, Incidents(), token='test', review_decisions=decision)
        self.assertEqual(self.movie['identity_status'], 'verified')
        self.assertEqual(self.movie['canonical_id'], 'tmdb:1')
        self.assertEqual(session['category'], 'premiere')


if __name__ == '__main__':
    unittest.main()
