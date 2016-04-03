# coding=utf-8

import test_helper

import unittest
import json

from hdserials_service import HDSerialsService

class HDSerialsServiceTest(unittest.TestCase):
    def setUp(self):
        self.service = HDSerialsService()

    def test_get_menu(self):
        menu_items = self.service.get_menu()

        for item in menu_items:
            self.assertTrue(len(item['path']) > 0)
            self.assertTrue(len(item['title']) > 0)

    def test_get_new_series(self):
        new_series = self.service.get_new_series()

        for serie in new_series:
            self.assertTrue(len(serie['path']) > 0)
            self.assertTrue(len(serie['title']) > 0)

    def test_search(self):
        query = 'castle'

        result = self.service.search(query)

        print(json.dumps(result, indent=4))

    def test_get_media_data(self):
        new_series = self.service.get_new_series()

        path = new_series[0]['path']

        data = self.service.get_media_data(path)

        print data

        for key, value in data.iteritems():
            print key
            print value
            # self.assertTrue(len(item['path']) > 0)
            # self.assertTrue(len(item['title']) > 0)

    def test_parse_page(self):
        new_series = self.service.get_new_series()

        path = new_series[0]['path']

        result = self.service.parse_page(path)

        print(json.dumps(result, indent=4))

    def test_retrieve_url(self):
        new_series = self.service.get_new_series()

        path = new_series[0]['path']

        urls = self.service.retrieve_urls(path)

        print(json.dumps(urls, indent=4))

    def test_get_play_list(self):
        new_series = self.service.get_new_series()

        path = new_series[0]['path']

        urls = self.service.retrieve_urls(path)

        play_list = self.service.get_play_list(urls[0]['url'])

        print(play_list)

    def test_get_url(self):
        new_series = self.service.get_new_series()
        path = new_series[0]['path']

        media_data = self.service.get_media_data(path)

        print media_data

        info = self.service.parse_page(path)

        print(json.dumps(info, indent=4))

        urls = self.service.get_urls(info['session']['headers'], info['session']['data'])

        print(json.dumps(urls, indent=4))

    def test_get_info_by_url(self):
        new_series = self.service.get_new_series()

        path = new_series[0]['path']

        data = self.service.get_info_by_url(path, {})

        print(data)

        for key, value in data.iteritems():
            print key
            print value
            # self.assertTrue(len(item['path']) > 0)
            # self.assertTrue(len(item['title']) > 0)

    def json_test(self):
        l = '''
{
    partner: null,
    d_id: 21609,
    video_token: "b69eb1607ccbc9c0",
    content_type: "serial",
    access_key: "0fb74eb4b2c16d45fe",
    cd: 0
  }
        '''

        print(json.loads(self.service.replace_keys(l, ['partner', 'd_id', 'video_token', 'content_type', 'access_key', 'cd'])))

if __name__ == '__main__':
    unittest.main()
