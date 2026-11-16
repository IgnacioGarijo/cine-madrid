import unittest
import base64
from datetime import datetime, timezone
from unittest.mock import Mock

from src.push_notifications import send_alerts, upcoming


class PushTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,17,10,tzinfo=timezone.utc)
        self.data={'generated_at':'2026-11-17T10:00:00+01:00','movies':[{'id':'m','canonical_title':'Akira'}],'sessions':[
            {'movie_id':'m','title':'Akira','canonical_id':'tmdb:149','identity_status':'verified','status':'confirmed','stale':False,'start':'2026-11-20T20:00:00+01:00'},
            {'movie_id':'m','title':'Akira','canonical_id':'tmdb:149','identity_status':'verified','status':'confirmed','stale':False,'start':'2026-11-21T20:00:00+01:00'},
            {'movie_id':'m','title':'Otra','canonical_id':'tmdb:555','identity_status':'needs_review','status':'confirmed','stale':False,'start':'2026-11-20T20:00:00+01:00'},
            {'movie_id':'m','title':'Pasada','canonical_id':'tmdb:777','identity_status':'verified','status':'confirmed','stale':False,'start':'2026-11-16T20:00:00+01:00'},
            {'movie_id':'m','title':'Antigua','canonical_id':'tmdb:999','identity_status':'verified','status':'confirmed','stale':True,'start':'2026-11-20T20:00:00+01:00'}]}

    def test_only_future_verified_and_current_sessions_are_eligible(self):
        self.assertEqual(list(upcoming(self.data,self.now)),['tmdb:149'])

    def test_new_favorite_sends_once_and_seen_favorite_does_not_repeat(self):
        entries=[{'id':'a'*64,'subscription':{'endpoint':'https://fcm.googleapis.com/fcm/send/test'},'favorites':['tmdb:149'],'seen':{}},
                 {'id':'b'*64,'subscription':{'endpoint':'https://fcm.googleapis.com/fcm/send/other'},'favorites':['tmdb:149'],'seen':{'tmdb:149':0}}]
        http=Mock();http.get.return_value=Mock(ok=True,json=lambda:{'subscriptions':entries,'next':None});http.post.return_value=Mock(ok=True)
        send=Mock();sent,failed=send_alerts(self.data,'secret','private',http=http,send=send,now=self.now)
        self.assertEqual((sent,failed),(1,0));send.assert_called_once()
        self.assertIn('Akira',send.call_args.kwargs['data']);self.assertEqual(http.post.call_count,2)
        for call in http.post.call_args_list:self.assertEqual(call.kwargs['json']['current'],['tmdb:149'])

    def test_send_failure_does_not_acknowledge_or_log_private_details(self):
        http=Mock();http.get.return_value=Mock(ok=True,json=lambda:{'subscriptions':[{'id':'a'*64,'subscription':{},'favorites':['tmdb:149'],'seen':{}}],'next':None})
        send=Mock(side_effect=RuntimeError('sensitive endpoint'))
        sent,failed=send_alerts(self.data,'secret','private',http=http,send=send,now=self.now)
        self.assertEqual((sent,failed),(0,1));http.post.assert_not_called()

    def test_expired_subscription_is_removed_only_after_paginating(self):
        from pywebpush import WebPushException
        entries=[{'id':'a'*64,'subscription':{},'favorites':['tmdb:149'],'seen':{}}]
        http=Mock();http.get.side_effect=[Mock(ok=True,json=lambda:{'subscriptions':entries,'next':1}),
                                       Mock(ok=True,json=lambda:{'subscriptions':[],'next':None})]
        http.post.return_value=Mock(ok=True)
        send=Mock(side_effect=WebPushException('expired',response=Mock(status_code=410)))
        sent,failed=send_alerts(self.data,'secret','private',http=http,send=send,now=self.now)
        self.assertEqual((sent,failed),(0,0));self.assertEqual(http.get.call_count,2)
        self.assertEqual(http.post.call_args.kwargs['json'],{'id':'a'*64,'remove':True})

    def test_real_vapid_key_and_encryption_without_sending_network_traffic(self):
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat
        from pywebpush import webpush
        encode=lambda value:base64.urlsafe_b64encode(value).rstrip(b'=').decode()
        server=ec.generate_private_key(ec.SECP256R1())
        private=encode(server.private_numbers().private_value.to_bytes(32,'big'))
        client=ec.generate_private_key(ec.SECP256R1())
        public=encode(client.public_key().public_bytes(Encoding.X962,PublicFormat.UncompressedPoint))
        sub={'endpoint':'https://fcm.googleapis.com/fcm/send/test','keys':{'p256dh':public,'auth':encode(bytes(range(16)))}}
        transport=Mock();transport.post.return_value=Mock(status_code=201,text='',headers={})
        webpush(sub,data='Una favorita',vapid_private_key=private,vapid_claims={'sub':'https://example.org'},requests_session=transport)
        self.assertNotIn(b'Una favorita',transport.post.call_args.kwargs['data'])
        self.assertIn('Authorization',transport.post.call_args.kwargs['headers'])


if __name__=='__main__':unittest.main()
