# -*- coding: utf-8 -*-

import urllib
import json
import re

from mw_service import MwService

class HDSerialsService(MwService):
    URL = 'http://www.hdserials.tv'

    def get_menu(self):
        list = []

        response = self.http_request(self.URL)
        document = self.to_document(response.read())

        links = document.xpath('//div[@id="gkDropMain"]/ul/li/a')

        for link in links:
            path = link.xpath('@href')[0]
            title = link.text_content()

            list.append({'path': path, 'title': title})

        return list

    def get_new_series(self):
        list = []

        response = self.http_request(self.URL)
        document = self.to_document(response.read())

        links = document.xpath('//div[@id="gkHeaderheader1"]//div[@class="custom"]/div/a')

        for link in links:
            path = link.xpath('@href')[0]
            title = link.text_content()

            list.append({'path': path, 'title': title})

        return list

    def get_media_data(self, path):
        data = {}

        response = self.http_request(path)
        document = self.to_document(response.read())

        frame_block = document.xpath('//div[@id="k2Container"]')[0]

        urls = frame_block.xpath('//div[@class="itemFullText"]//iframe[@src]')

        data['urls'] =  urls

        thumb = frame_block.xpath('//div[@class="itemImageBlock"]//a')[0].get('href')

        data['thumb'] = self.URL + thumb

        title_block = frame_block.xpath('//h2[@class="itemTitle"]')[0].text_content().split('/')

        data['title'] = [l.strip() for l in title_block]

        # Log(data['title'])

        data['rating'] = float(re.compile('width\s?:\s?([\d\.]+)').search(
            frame_block.xpath('//div[@class="itemRatingBlock"]//li[@class="itemCurrentRating"]')[0].get('style')
        ).group(1)) / 10

        # Log(data['rating'])

        data['meta'] = frame_block.xpath(
            '//div[@class="itemFullText"]//text() ' +
            '| //div[@class="itemFullText"]//span ' +
            '| //div[@class="itemFullText"]//strong ' +
            '| //div[@class="itemFullText"]//p[@style="text-align: center;"]'
        )

        return data

    def parse_page(self, path):
        http_headers = {'Referer': path}

        media_data = self.get_media_data(path)

        data = {'variants': {}}

        try:
            for url in media_data['urls']:
                # Log.Debug('Found variant %s', url)

                variant = self.get_info_by_url(url.get('src'), http_headers)
                if variant:
                    data['variants'][variant['url']] = variant
                    if 'session' not in data:
                        data.update(variant)
                        if 'seasons' in data:
                            data['seasons'] = variant['seasons'].copy()
                    else:
                        if 'seasons' in variant:
                            data['seasons'].update(variant['seasons'])

            if len(data['variants']) == 0:
                return None
        except Exception as e:
            print(e)
            return None

        ret = {
            'path': path,
            'rating': 0.00,
            'thumb': media_data['thumb']
        }

        title = media_data['title']

        ret['original_title'] = title.pop() if len(title) > 1 else None
        ret['title'] = ' / '.join(title)

        meta = media_data['meta']

        tmap = {
            u'Описание': 'summary',
            u'Год выпуска': 'year',
            u'Страна': 'countries',
            u'Жанр': 'genres',
            u'Продолжительность': 'duration',
            u'Режиссер': 'directors',
            u'В ролях': 'roles',
        }

        current = None
        variants_names = []
        for desc in meta:
            if not isinstance(desc, basestring):
                if desc.tag == 'p' and u'Перевод' in desc.text_content():
                    variants_names.append(desc.text_content())
                    current = None
                continue
            if not desc:
                continue

            if desc in tmap:
                current = desc
            elif current:
                if desc[:1] == ':':
                    desc = desc[2:]

                if tmap[current] in data:
                    data[tmap[current]] = data[tmap[current]] + ' ' + unicode(desc)
                else:
                    data[tmap[current]] = unicode(desc)

        for current in ('countries', 'genres', 'directors', 'roles'):
            if current in data:
                data[current] = [l.strip() for l in data[current].split(',')]

        # TODO
        data['duration'] = None
        # data['duration'] = Datetime.MillisecondsFromString(data['duration'])

        data['rating'] = media_data['rating']

        if 'year' in data:
            if '-' in data['year']:
                data['year'] = data['year'].split('-')[0]

            data['year'] = int(data['year'])

        for k in data['variants']:
            data['variants'][k]['variant_title'] = unicode(
                variants_names.pop(0)
            ) if variants_names else ''

        if data['session'] == 'external':
            if len(data['variants']) > 1:
                data['seasons'] = {'1': ret['title']}
                data['current_season'] = 1
                data['episodes'] = data['variants']

        ret.update(data)

        return ret

    def get_info_by_url(self, url, http_headers, parent=None):
        if not re.compile('http://moonwalk\.cc/').match(url):
            return {
                'url': url.replace('vkontakte.ru', 'vk.com'),
                'session': 'external',
            }

        headers = {}
        if parent:
            headers['Referer'] = parent
            if 'Referer' in http_headers:
                url = '%s&%s' % (
                    url,
                    urllib.urlencode({'referer': http_headers['Referer']})
                )

        elif 'Referer' in http_headers:
            headers['Referer'] = http_headers['Referer']

        session_data = self.collect_session_data(url)

        ret = {}
        ret['url'] = parent if parent else url

        #if ret['session']['values']['content_type'] == 'serial':
        if session_data['data']['content_type'] == 'serial':
            ret = dict(self.get_serial_info(url), **ret)

        ret['session'] = session_data

        return ret

    def retrieve_url(self, url):
        iframe_url = self.get_iframe_url(url)

        session_data = self.collect_session_data(iframe_url)

        #print(json.dumps(session_data, indent=4))

        # ret = {}
        #
        # if session_data['data']['content_type'] == 'serial':
        #     ret = self.get_serial_info(url)

        return self.get_url(session_data['headers'], session_data['data'])

    def get_iframe_url(self, url):
        response = self.http_request(url)
        document = self.to_document(response.read())

        frame_block = document.xpath('//div[@id="k2Container"]')[0]

        urls = frame_block.xpath('//div[@class="itemFullText"]//iframe[@src]')

        return urls[0].get('src')

    def search(self, query):
        params = urllib.urlencode({
            'option': 'com_k2',
            'view': 'itemlist',
            'task': 'search',
            'searchword': query,
            'categories': '',
            'format': 'json',
            'tpl': 'search',
        })

        response = self.http_request(self.URL + "/index.php?" + params)

        return json.loads(response.read())

    def replace_keys(self, s, keys):
        s = s.replace('\'', '"')

        for key in keys:
            s = s.replace(key + ':', '"' + key + '":')

        return s
