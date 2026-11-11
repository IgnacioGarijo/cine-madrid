import unittest
from datetime import date
from unittest.mock import patch
from src.tmdb import Client,TMDBError,identity_match,classify,title_variants,enrich
from src.core import Incidents

CONFIG={'repertory_min_days':365,'current_release_max_days':180,'request_budget':300}

def movie(id=149,title='Akira',director='Katsuhiro Ōtomo',year=1988,runtime=124,releases=None,aliases=None):
    return dict(id='tmdb:'+str(id),tmdb_id=id,title=title,original_title=title,year=year,runtime=runtime,
                directors=[director],director=director,aliases=aliases or [],
                releases=releases if releases is not None else [{'country':'JP','type':3,'date':'1988-07-16'}],
                source_url='https://www.themoviedb.org/movie/'+str(id))

class TMDBTests(unittest.TestCase):
    def test_akira_identity_uses_director_and_ignores_version(self):
        matched,evidence=identity_match({'title':'Akira (VOSE)','director':'Katsuhiro Otomo','duration_minutes':124},[movie()])
        self.assertEqual(matched['id'],'tmdb:149')
        self.assertEqual(evidence['title_match'],'exact_or_alias')
        self.assertEqual(classify(matched,date(2026,11,12),'unclassified',CONFIG)[0],'repertory')

    def test_homonymous_remake_is_not_accepted_by_title(self):
        wrong=movie(id=999,director='Otro director',year=2016)
        matched,_=identity_match({'title':'Akira','director':'Katsuhiro Otomo'},[wrong,movie()])
        self.assertEqual(matched['id'],'tmdb:149')
        self.assertIsNone(identity_match({'title':'Akira'},[movie()])[0])

    def test_same_director_remake_requires_additional_evidence(self):
        candidates=[movie(id=1,title='Una película',runtime=90),movie(id=2,title='Una película',runtime=125)]
        source={'title':'Una película','director':'Katsuhiro Otomo'}
        self.assertIsNone(identity_match(source,candidates)[0])
        self.assertEqual(identity_match(dict(source,duration_minutes=124),candidates)[0]['tmdb_id'],2)

    def test_combined_titles_are_identified_without_manual_permutations(self):
        m=movie(id=313369,title='La ciudad de las estrellas (La La Land)',director='Damien Chazelle',aliases=['La La Land','La ciudad de las estrellas'],runtime=128)
        for title in ['Lalaland','La La Land: La ciudad de las estrellas','La la land (La ciudad de las estrellas)']:
            with self.subTest(title=title):
                self.assertIsNotNone(identity_match({'title':title,'director':'Damien Chazelle','duration_minutes':128},[m])[0])

    def test_typo_needs_duration_evidence(self):
        m=movie(id=1,title='La ciudad de las estrellas',director='Damien Chazelle',runtime=128)
        source={'title':'La ciudad de las estrellad','director':'Damien Chazelle'}
        self.assertIsNone(identity_match(source,[m])[0])
        self.assertIsNotNone(identity_match(dict(source,duration_minutes=128),[m])[0])

    def test_prefix_and_format_are_removed_for_search(self):
        self.assertIn('DEPREDADOR 2',title_variants('AETERNA: DEPREDADOR 2 (VOSE)'))
        self.assertIn('Akira',title_variants('Akira (VOSE)'))

    def test_recent_theatrical_release_stays_current(self):
        m=movie(releases=[{'country':'ES','type':3,'date':'2026-10-30'}])
        self.assertEqual(classify(m,date(2026,11,12),'unclassified',CONFIG)[0],'premiere')

    def test_old_festival_premiere_is_insufficient(self):
        m=movie(releases=[{'country':'FR','type':1,'date':'2020-05-01'}])
        self.assertEqual(classify(m,date(2026,11,12),'unclassified',CONFIG)[0],'unclassified')

    def test_first_distribution_in_spain_can_still_be_repertory(self):
        m=movie(releases=[{'country':'JP','type':3,'date':'1988-07-16'},{'country':'ES','type':3,'date':'2026-11-12'}])
        self.assertEqual(classify(m,date(2026,11,12),'premiere',CONFIG)[0],'repertory')

    def test_recent_reissue_does_not_erase_original_release(self):
        m=movie(releases=[{'country':'JP','type':3,'date':'1988-07-16'},{'country':'ES','type':3,'date':'2026-11-01'}])
        self.assertEqual(classify(m,date(2026,11,12),'unclassified',CONFIG)[1]['first_theatrical_date'],'1988-07-16')

    def test_intermediate_window_is_left_for_context_review(self):
        m=movie(releases=[{'country':'ES','type':3,'date':'2026-03-01'}])
        self.assertEqual(classify(m,date(2026,11,12),'unclassified',CONFIG)[0],'unclassified')

    @patch('src.tmdb.Client.resolve',side_effect=TMDBError('authentication_failed'))
    def test_authentication_failure_keeps_previously_verified_identity(self,resolve):
        source=dict(id='paz:1',title='Akira',director='Katsuhiro Otomo',identity_status='verified',canonical_id='tmdb:149',source_url='https://cine.example')
        incidents=Incidents();result=enrich([source],[],{},CONFIG,incidents,token='test-token')
        self.assertEqual(source['canonical_id'],'tmdb:149')
        self.assertEqual(result['status'],'error')
        self.assertEqual(result['errors'],['authentication_failed'])
        self.assertNotIn('test-token',str(incidents.finish(set())))

    @patch('src.tmdb.Client.get')
    def test_cached_metadata_does_not_query_again(self,get):
        from src.core import now
        cached=movie();cached['fetched_at']=now()
        client=Client('test-token',{'movies':{'149':cached}})
        self.assertEqual(client.movie(149)['id'],'tmdb:149');get.assert_not_called()

if __name__=='__main__':unittest.main()
