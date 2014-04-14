import unittest

import app


class PasteTestCase(unittest.TestCase):
    def setUp(self):
        app.redis.flushdb()
        self.app = app.app.test_client()

    def test_paste_form(self):
        resp = self.app.get('/')
        assert b'textarea' in resp.data

    def test_paste_create(self):
        post_resp = self.app.post('/', data={'content': 'my very own paste'})
        self.assertEqual(post_resp.status_code, 302)
        _, key = post_resp.location.rsplit('/', 1)
        get_resp = self.app.get('/{}'.format(key))
        self.assertEqual(get_resp.status_code, 200)
        self.assertIn(b"my very own paste", get_resp.data)

    def test_paste_delete(self):
        post_resp = self.app.post('/', data={'content': 'my very own paste'})
        _, key = post_resp.location.rsplit('/', 1)
        del_resp = self.app.delete('/{}'.format(key))
        self.assertEqual(del_resp.status_code, 204)
        get_resp = self.app.get('/{}'.format(key))
        self.assertEqual(get_resp.status_code, 404)

    def test_paste_get(self):
        raise NotImplementedError


if __name__ == "__main__":
    unittest.main()
