import unittest
from unittest.mock import Mock
from src.favorites import apply_request,request_url

def event(operation='Añadir',movie='tmdb:149',owner='owner'):
    return {'issue':{'user':{'login':owner},'title':'Favoritas: actualizar lista','body':f'### Operación\n\n{operation}\n\n### Película\n\n{movie}'}}

class FavoriteTests(unittest.TestCase):
    def test_only_owner_can_change_public_list(self):
        client=Mock();result,reply,success=apply_request(event(owner='visitor'),'owner',[],client)
        self.assertEqual(result,[]);self.assertIsNone(reply);client.movie.assert_not_called()

    def test_selected_identity_is_shared_and_duplicate_safe(self):
        client=Mock();client.movie.return_value={'id':'tmdb:149','tmdb_id':149,'title':'Akira','year':1988}
        result,_,success=apply_request(event(),'owner',[],client)
        self.assertTrue(success);self.assertEqual(result[0]['id'],'tmdb:149')
        again,_,_=apply_request(event(),'owner',result,client);self.assertEqual(len(again),1)
        removed,_,success=apply_request(event(operation='Quitar'),'owner',result,client)
        self.assertTrue(success);self.assertEqual(removed,[])

    def test_homonyms_are_presented_for_confirmation(self):
        client=Mock();client.search.return_value=[{'id':1},{'id':2}]
        client.movie.side_effect=[{'id':'tmdb:1','title':'Crash','year':1996},{'id':'tmdb:2','title':'Crash','year':2004}]
        result,reply,success=apply_request(event(movie='Crash'),'owner',[],client)
        self.assertEqual(result,[]);self.assertFalse(success);self.assertIn('1996',reply);self.assertIn('2004',reply)
        self.assertIn('movie=tmdb%3A1',reply)

if __name__=='__main__':unittest.main()
