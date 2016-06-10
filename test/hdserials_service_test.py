# coding=utf-8

import test_helper

import unittest
import json

from hdserials_service import HDSerialsService

class HDSerialsServiceTest(unittest.TestCase):
    def setUp(self):
        self.service = HDSerialsService()

    def test_get_get_categories(self):
        menu_items = self.service.get_categories()

        for item in menu_items:
            self.assertTrue(len(item['path']) > 0)
            self.assertTrue(len(item['title']) > 0)

    def test_get_new_series(self):
        items = self.service.get_new_series()

        for item in items:
            self.assertTrue(len(item['path']) > 0)
            self.assertTrue(len(item['title']) > 0)

    def test_get_popular(self):
        response = self.service.get_popular()

        for item in response['movies']:
            self.assertTrue(len(item['path']) > 0)
            self.assertTrue(len(item['title']) > 0)
            self.assertTrue(len(item['thumb']) > 0)

        print(json.dumps(response, indent=4))

    def test_get_subcategories(self):
        items = self.service.get_subcategories('/Filmy.html')

        print(json.dumps(items, indent=4))

        for item in items['data']:
            self.assertTrue(len(item['path']) > 0)
            self.assertTrue(len(item['title']) > 0)

        print(json.dumps(items, indent=4))

    def test_get_category_items(self):
        items = self.service.get_category_items('/Filmy.html')

        for item in items:
            self.assertTrue(len(item['path']) > 0)
            self.assertTrue(len(item['title']) > 0)
            self.assertTrue(len(item['thumb']) > 0)

        print(json.dumps(items, indent=4))

    def test_pagination_in_category_items(self):
        result = self.service.get_category_items('/Filmy.html', page=1)

        #print(json.dumps(result, indent=4))

        pagination = result['pagination']

        self.assertEqual(pagination['has_next'], True)
        self.assertEqual(pagination['has_previous'], False)
        self.assertEqual(pagination['page'], 1)

        result = self.service.get_category_items('/Filmy.html', page=2)

        # print(json.dumps(result, indent=4))

        pagination = result['pagination']

        self.assertEqual(pagination['has_next'], True)
        self.assertEqual(pagination['has_previous'], True)
        self.assertEqual(pagination['page'], 2)

    def test_search(self):
        query = 'castle'

        result = self.service.search(query)

        print(json.dumps(result, indent=4))

    def test_pagination_in_popular(self):
        result = self.service.get_popular(page=1)

        # print(json.dumps(result, indent=4))

        pagination = result['pagination']

        self.assertEqual(pagination['has_next'], True)
        self.assertEqual(pagination['has_previous'], False)
        self.assertEqual(pagination['page'], 1)

        result = self.service.get_popular(page=2)

        # print(json.dumps(result, indent=4))

        pagination = result['pagination']

        self.assertEqual(pagination['has_next'], True)
        self.assertEqual(pagination['has_previous'], True)
        self.assertEqual(pagination['page'], 2)

    def test_pagination_in_subcategories(self):
        path = '/Serialy.html'

        result = self.service.get_subcategories(path=path, page=1)

        #print(json.dumps(result, indent=4))

        pagination = result['pagination']

        self.assertEqual(pagination['has_next'], True)
        self.assertEqual(pagination['has_previous'], False)
        self.assertEqual(pagination['page'], 1)

        result = self.service.get_subcategories(path=path, page=2)

        print(json.dumps(result, indent=4))

        pagination = result['pagination']

        self.assertEqual(pagination['has_next'], True)
        self.assertEqual(pagination['has_previous'], True)
        self.assertEqual(pagination['page'], 2)

    def test_get_media_data(self):
        new_series = self.service.get_new_series()

        path = new_series[0]['path']

        document = self.service.fetch_document(path)

        data = self.service.get_media_data(document)

        print(json.dumps(data, indent=4))

        for key, value in data.iteritems():
            self.assertTrue(data['rating'] > 0)
            self.assertTrue(data['thumb'] > 0)
            self.assertTrue(data['title'] > 0)

    def test_retrieve_urls(self):
        new_series = self.service.get_new_series()

        path = new_series[0]['path']

        urls = self.service.retrieve_urls(path)

        print(json.dumps(urls, indent=4))

    def test_retrieve_episode_urls(self):
        new_series = self.service.get_new_series()

        path = new_series[0]['path']

        urls = self.service.retrieve_urls(path, season=1, episode=2)

        print(json.dumps(urls, indent=4))

    def test_get_play_list(self):
        new_series = self.service.get_new_series()

        path = new_series[0]['path']

        urls = self.service.retrieve_urls(path)

        play_list = self.service.get_play_list(urls[0]['url'])

        print(play_list)

    def test_get_episode_info(self):
        new_series = self.service.get_new_series()

        text = new_series[0]['text']

        print text

        result = self.service.get_episode_info(text)

        print(json.dumps(result, indent=4))

    def test_is_serial(self):
        new_series = self.service.get_new_series()

        path = new_series[0]['path']

        result = self.service.is_serial(path)

        print(json.dumps(result, indent=4))

    def test_convert_duration(self):
        text = ' ~  22 мин'

        result = self.service.convert_duration(text)

        print result

    def test_json(self):
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
