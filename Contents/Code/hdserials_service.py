# -*- coding: utf-8 -*-

import urllib
import re
import json
from lxml.etree import tostring

from mw_service import MwService

class HDSerialsService(MwService):
    URL = 'http://www.hdserials.tv'

    def available(self):
        document = self.fetch_document(self.URL)

        return document.xpath('//div[@id="gkDropMain"]//a[contains(@href, ".html")]')

    def get_menu(self):
        list = []

        document = self.fetch_document(self.URL)

        links = document.xpath('//div[@id="gkDropMain"]/ul/li/a')

        for link in links:
            path = link.xpath('@href')[0]

            if path != '/' and path != self.URL + '/':
                title = link.text_content()

                list.append({'path': path, 'title': title})

        return list

    def get_new_series(self):
        list = []

        document = self.fetch_document(self.URL)

        links = document.xpath('//div[@id="gkHeaderheader1"]//div[@class="custom"]/div/a')

        for link in links:
            path = link.xpath('@href')[0]
            title = link.text_content()

            list.append({'path': path, 'title': title})

        return list

    def get_popular(self):
        list = []

        document = self.fetch_document(self.URL + '/popular.html')

        items = document.xpath('//div[contains(@class, "nspArts")]//div[contains(@class, "nspArt")]/div')

        for item in items:
            title = item.find('h4').text_content()
            link = item.find('a')

            path = link.xpath('@href')[0]
            thumb = link.find('img').get('src')

            list.append({'path': path, 'title': title, 'thumb': thumb})

        return list

    def get_categories(self, path):
        list = []

        document = self.fetch_document(self.URL + path)

        links = document.xpath('//div[@class="itemListSubCategories"]//div[contains(@class, "subCategory")]/h2/a')

        for link in links:
            path = link.xpath('@href')[0]
            title = link.text_content()

            list.append({'path': path, 'title': title})

        return list

    def get_category_items(self, path):
        list = []

        document = self.fetch_document(self.URL + path)

        links = document.xpath('//div[@class="itemList"]//div[@class="catItemBody"]//span[@class="catItemImage"]/a')

        for link in links:
            path = link.xpath('@href')[0]
            title = link.get('title')
            thumb = link.find('img').get('src')

            list.append({'path': path, 'title': title, 'thumb': thumb})

        return list

    def get_pagination(self, path):
        list = []

        document = self.fetch_document(self.URL + path)

        links = document.xpath('//div[@class="k2Pagination"]/ul/li[@class="pagination-next"]/a')

        for link in links:
            path = link.xpath('@href')[0]
            title = link.text_content()

            list.append({'path': path, 'title': title})

        return list

    def get_media_data(self, path):
        data = {}

        document = self.fetch_document(path)

        frame_block = document.xpath('//div[@id="k2Container"]')[0]

        urls = frame_block.xpath('//div[@class="itemFullText"]//iframe[@src]')

        data['urls'] =  urls

        thumb = frame_block.xpath('//div[@class="itemImageBlock"]//a')[0].get('href')

        data['thumb'] = self.URL + thumb

        title_block = frame_block.xpath('//h2[@class="itemTitle"]')[0].text_content().split('/')

        data['title'] = [l.strip() for l in title_block]

        data['rating'] = float(re.compile('width\s?:\s?([\d\.]+)').search(
            frame_block.xpath('//div[@class="itemRatingBlock"]//li[@class="itemCurrentRating"]')[0].get('style')
        ).group(1)) / 10

        data['meta'] = frame_block.xpath(
            '//div[@class="itemFullText"]//text() ' +
            '| //div[@class="itemFullText"]//span ' +
            '| //div[@class="itemFullText"]//strong ' +
            '| //div[@class="itemFullText"]//p[@style="text-align: center;"]'
        )

        return data

    def retrieve_urls(self, url, season=None, episode=None):
        document = self.get_movie_document(url, season=season, episode=episode)
        content = tostring(document.xpath('body')[0])

        data = self.get_session_data(content)

        headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': url,
            'Content-Data': self.get_content_data(content)
        }

        return self.get_urls(headers, data)

    def get_movie_document(self, url, season=None, episode=None):
        gateway_url = self.get_gateway_url(self.fetch_document(url))

        if season:
            movie_url = '%s?season=%d&episode=%d' % (gateway_url, int(season), int(episode))
        else:
            movie_url = gateway_url

        return self.fetch_document(movie_url)

    def get_serial_info(self, document):
        ret = {}

        ret['seasons'] = {}
        ret['episodes'] = {}

        for item in document.xpath('//select[@id="season"]/option'):
            value = item.get('value')
            ret['seasons'][value] = unicode(item.text_content())
            if item.get('selected'):
                ret['current_season'] = value

        for item in document.xpath('//select[@id="episode"]/option'):
            value = item.get('value')
            ret['episodes'][value] = unicode(item.text_content())
            if item.get('selected'):
                ret['current_episode'] = value

        return ret

    def search(self, query):
        params = {
            'option': 'com_k2',
            'view': 'itemlist',
            'task': 'search',
            'searchword': query,
            'categories': '',
            'format': 'json',
            'tpl': 'search',
        }

        url = self.build_url(self.URL + "/index.php?", **params)

        content = self.fetch_content(url)

        return self.get_movies(content)

    def get_movies(self, content):
        result = {'movies': []}

        data = json.loads(content)

        if 'items' in data:
            for item in data['items']:
                if item['title'] in item['category']['name']:
                    title = u'%s' % item['category']['name']

                    key = '%s?%s' % (
                        '/video/hdserials/info',
                        urllib.urlencode({'path': item['link']}))
                else:
                    title = u'%s / %s' % (item['category']['name'], item['title'])
                    key = '%s%s' % (self.URL, item['link'])


                rating_key = item['link']

                thumb = '%s%s' % (
                    self.URL,
                    item['image']
                )

                summary = self.to_document(item['introtext']).text_content()

                result['movies'].append({"key": key, "rating_key": rating_key, "name": title, "thumb": thumb, "summary": summary})

        return result

    def parse_page(self, path):
        if self.URL not in path:
            path = self.URL + path

        http_headers = {'Referer': path}

        # ret = service.load_cache(path)
        #
        # if ret:
        #     return ret

        document = self.fetch_document(path)
        #page = document.xpath('//div[@id="k2Container"]')[0]

        media_data = self.get_media_data(path)

        data = {'variants': {}}

        try:
            for url in media_data['urls']:
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

        # service.save_cache(ret)

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

        response = self.http_request(url)
        content = response.read()

        session_data = {
            'data': self.get_session_data(content),
            'headers': {
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': url,
                'Content-Data': self.get_content_data(content),
                'Cookie': None
                # 'Cookie': self.get_cookies(response)
            },
        }

        ret = {}
        ret['url'] = parent if parent else url

        # if ret['session']['values']['content_type'] == 'serial':
        if session_data['data']['content_type'] == 'serial':
            # response = self.http_request(url)
            # document = self.to_document(response.read())
            document = self.fetch_document(url)

            ret = dict(self.get_serial_info(document), **ret)

        ret['session'] = session_data

        return ret

    def get_gateway_url(self, document):
        gateway_url = None

        frame_block = document.xpath('//div[@id="k2Container"]')[0]

        urls = frame_block.xpath('//div[@class="itemFullText"]//iframe[@src]')

        if len(urls) > 0:
            gateway_url = urls[0].get('src')

        return gateway_url

    def get_cookie_info(self, url):
        response = self.http_request(url)
        document = self.to_document(response.read())

        cookie = response.headers['Set-Cookie']

        index = cookie.index(';')

        cookie = cookie[0: index + 1]

        csrf_token = document.xpath('//meta[@name="csrf-token"]/@content')[0]

        return {'cookie': str(cookie), 'csrf-token': str(csrf_token)}

    def get_episode_url(url, season, episode):
        if season:
            return '%s?season=%d&episode=%d' % (url, int(season), int(episode))

        return url

    def replace_keys(self, s, keys):
        s = s.replace('\'', '"')

        for key in keys:
            s = s.replace(key + ':', '"' + key + '":')

        return s
