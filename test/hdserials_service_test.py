# coding=utf-8

import test_helper

import unittest
import json
import urllib

from hdserials_service import HDSerialsService

class HDSerialsServiceTest(unittest.TestCase):
    def setUp(self):
        self.service = HDSerialsService()

    def test_get_menu(self):
        menu_items = self.service.get_menu()

        for item in menu_items:
            #print item
            self.assertTrue(len(item['path']) > 0)
            self.assertTrue(len(item['title']) > 0)

    def test_get_new_series(self):
        new_series = self.service.get_new_series()

        for serie in new_series:
            # print item
            self.assertTrue(len(serie['path']) > 0)
            self.assertTrue(len(serie['title']) > 0)

    def test_search(self):
        query = 'castle'

        result = self.service.search(query)

        #print(json.dumps(result, indent=4))

        if 'items' in result:
            for item in result['items']:
                if item['title'] in item['category']['name']:
                    title = u'%s' % item['category']['name']

                    key = '%s?%s' % (
                        '/video/hdserials/info',
                        urllib.urlencode({'path': item['link']}))
                else:
                    title = u'%s / %s' % (item['category']['name'], item['title'])
                    key = '%s%s' % (self.service.URL, item['link'])

                print('title:' + title)
                print('key:' + key)
                print('rating_key:' + item['link'])

                thumb = '%s%s' % (
                    self.service.URL,
                    item['image']
                ),
                print('thumb:' + unicode(thumb))

                print('summary :' + self.service.to_document(item['introtext']).text_content())

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
        # path = 'http://moonwalk.cc/serial/f26e26e1c4b2f4dcbc4f5d81bf680ffe/iframe'
        new_series = self.service.get_new_series()

        path = new_series[0]['path']

        result = self.service.parse_page(path)

        print(json.dumps(result, indent=4))

    def test_retrieve_url(self):
        #path = '/Multfilmy/Pixar-Animation-Studios/Horoshiy-dinozavr-/-The-Good-Dinosaur.html'
        new_series = self.service.get_new_series()

        path = new_series[0]['path']

        url = self.service.retrieve_url(path)

        print(url)

    def test_get_play_list(self):
        #path = '/Multfilmy/Pixar-Animation-Studios/Horoshiy-dinozavr-/-The-Good-Dinosaur.html'

        new_series = self.service.get_new_series()

        path = new_series[0]['path']

        url = self.service.retrieve_url(path)

        play_list = self.service.get_play_list(url)

        print(play_list)

    def test_get_url(self):
        path = self.service.URL + '/Multfilmy/Pixar-Animation-Studios/Horoshiy-dinozavr-/-The-Good-Dinosaur.html'

        media_data = self.service.get_media_data(path)

        print media_data

        info = self.service.parse_page(path)

        print(json.dumps(info, indent=4))

        url = self.service.get_url(info['session']['headers'], info['session']['data'])

        print(url)

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

        print(json.loads(self.replace_keys(l, ['partner', 'd_id', 'video_token', 'content_type', 'access_key', 'cd'])))

    def replace_keys(self, s, keys):
        for key in keys:
           s = s.replace(key + ':', '"' + key + '":')

        return s

if __name__ == '__main__':
    unittest.main()
