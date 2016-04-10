# -*- coding: utf-8 -*-

import urllib
import re
import json
from lxml.etree import tostring

from mw_service import MwService

class HDSerialsService(MwService):
    URL = 'http://www.hdserials.tv'
    KEY_CACHE = 'parse_cache'

    cache = {}

    def load_cache(self, path):
        result = None

        if self.KEY_CACHE in self.cache:
            result = self.cache[self.KEY_CACHE]

            if result and 'path' in result and result['path'] == path:
                return result

        return result

    def save_cache(self, data):
        self.cache[self.KEY_CACHE] = data

    def available(self):
        document = self.fetch_document(self.URL)

        return document.xpath('//div[@id="gkDropMain"]//a[contains(@href, ".html")]')

    def get_categories(self):
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

        items = document.xpath('//div[@id="gkHeaderheader1"]//div[@class="custom"]/div')

        for item in items:
            link = item.find('a')

            path = link.xpath('@href')[0]
            title = link.text_content()
            text = item.xpath('span')[0].text_content() + ' ' + title

            list.append({'path': path, 'title': title, 'text': text})

        return list

    def get_popular(self, page=1, per_page=20):
        list = []

        document = self.fetch_document(self.URL + '/popular.html')

        items = document.xpath('//div[contains(@class, "nspArts")]//div[contains(@class, "nspArt")]/div')

        for index, item in enumerate(items):
            if index >= (page - 1) * per_page and index < page * per_page:
                link = item.find('a')

                path = self.URL + link.xpath('@href')[0]

                if path:
                    title = item.find('h4').text_content()
                    thumb = link.find('img').get('src')

                    list.append({'path': path, 'title': title, 'thumb': thumb})

        pagination = self.extract__pagination_data_from_array(items, page, per_page)

        return {"movies": list, "pagination": pagination["pagination"]}

    def get_subcategories(self, path, page=1, per_page=20):
        page = int(page)
        per_page = int(per_page)

        list = []

        document = self.fetch_document(self.URL + path)

        items = document.xpath('//div[@class="itemListSubCategories"]//div[contains(@class, "subCategory")]/h2/a')

        for index, item in enumerate(items):
            if index >= (page - 1) * per_page and index < page * per_page:
                path = item.xpath('@href')[0]
                title = item.text_content()

                list.append({'path': path, 'title': title})

        pagination = self.extract__pagination_data_from_array(items, page, per_page)

        return {"data": list, "pagination": pagination["pagination"]}

    def get_category_items(self, path, page=1):
        list = []

        page_path = self.get_page_path(path, page)

        document = self.fetch_document(self.URL + page_path)

        links = document.xpath('//div[@class="itemList"]//div[@class="catItemBody"]//span[@class="catItemImage"]/a')

        for link in links:
            href = self.URL + link.xpath('@href')[0]
            title = link.get('title')
            thumb = link.find('img').get('src')

            list.append({'path': href, 'title': title, 'thumb': thumb})

        pagination = self.extract_pagination_data(page_path)

        return {"movies": list, "pagination": pagination["pagination"]}

    def extract_pagination_data(self, path):
        document = self.fetch_document(self.URL + path)

        page = 1
        pages = 1

        response = {}

        pagination_root = document.xpath('//div[@class="k2Pagination"]')

        if pagination_root:
            pagination_block = pagination_root[0]

            counter_block = pagination_block.xpath('p[@class="counter"]/span')

            if counter_block:
                counter = counter_block[0].text_content()

                phrase = counter.split(' ')

                page = int(phrase[1])
                pages = int(phrase[3])

        response["pagination"] = {
            "page": page,
            "pages": pages,
            "has_previous": page > 1,
            "has_next": page < pages,
        }

        return response

    def extract__pagination_data_from_array(self, items, page, per_page):
        pages = len(items) / per_page

        if len(items) % per_page > 0:
            pages = pages + 1

        response = {}

        response["pagination"] = {
            "page": page,
            "pages": pages,
            "has_previous": page > 1,
            "has_next": page < pages,
        }

        return response

    def get_media_data(self, document):
        data = {}

        block = document.xpath('//div[@id="k2Container"]')[0]

        thumb = block.xpath('//div/span[@class="itemImage"]/a/img')[0].get("src")

        data['thumb'] = self.URL + thumb

        title_block = block.xpath('//h2[@class="itemTitle"]')[0].text_content().split('/')

        data['title'] = [l.strip() for l in title_block][0]

        data['rating'] = float(re.compile('width\s?:\s?([\d\.]+)').search(
            block.xpath('//div[@class="itemRatingBlock"]//li[@class="itemCurrentRating"]')[0].get('style')
        ).group(1)) / 10

        description_block = block.xpath('//div[@class="itemFullText"]/p')

        description = {}

        for elem in description_block[0]:
            key = unicode(elem.text_content())

            if key == u'Продолжительность':
                value = elem.tail.strip()[2:]
            elif elem.tail:
                value = elem.tail.replace(':', '')
            else:
                value = ''

            description[key] = value

        summary = description[u'Описание'] + '\n' + \
                  u'Страна'  + ': ' + description[u'Страна'] + '\n' + \
                  u'Жанр' + ': ' + description[u'Жанр'] + '\n' + \
                  u'Перевод' + ': ' + description[u'Перевод'] + '\n' + \
                  u'Режиссер' + ': ' + description[u'Режиссер'] + '\n' + \
                  u'В ролях' + ': ' + description[u'В ролях'] + '\n'

        data['duration'] = self.convert_duration(description[u'Продолжительность'])
        data['year'] = int(description[u'Год выпуска'])
        data['tags'] = description[u'Жанр'].replace(',', ', ').split(',')
        data['summary'] = summary

        return data

    def retrieve_urls(self, url, season=None, episode=None):
        if url.find(self.URL) < 0:
            url = self.URL + url

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
            value = int(item.get('value'))
            ret['seasons'][value] = unicode(item.text_content())
            if item.get('selected'):
                ret['current_season'] = int(value)

        for item in document.xpath('//select[@id="episode"]/option'):
            value = int(item.get('value'))
            ret['episodes'][value] = unicode(item.text_content())
            if item.get('selected'):
                ret['current_episode'] = int(value)

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

        result = {'movies': []}

        data = json.loads(content)

        if 'items' in data:
            for item in data['items']:
                title = item['category']['name'] + ' / ' + item['title']
                key = self.URL + item['link']
                rating_key = item['link']
                thumb = self.URL + item['image']
                summary = self.to_document(item['introtext']).text_content()
                path = self.URL + item['link']

                movie = {
                    "key": key,
                    "rating_key": rating_key,
                    "name": title,
                    "thumb": thumb,
                    "summary": summary,
                    "path": path
                 }

                result['movies'].append(movie)

        return result

    def parse_page(self, path, cache=False):
        if cache:
            result = self.load_cache(path)
        else:
            result = self.parse_page_body(path)

        if cache:
            self.save_cache(result)

        return result

    def parse_page_body(self, path):
        if self.URL not in path:
            path = self.URL + path

        http_headers = {'Referer': path}

        document = self.fetch_document(path)

        media_data = self.get_media_data(document)

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

        result = {
            'path': path,
            'rating': 0.00,
            'thumb': media_data['thumb']
        }

        title = media_data['title']

        result['original_title'] = title.pop() if len(title) > 1 else None
        result['title'] = ' / '.join(title)

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
                data['seasons'] = {'1': result['title']}
                data['current_season'] = 1
                data['episodes'] = data['variants']

        result.update(data)

        return result

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

    def get_page_path(self, path, page=1):
        if page == 1:
            new_path = path
        else:
            new_path = path[:len(path) - 5] + '/Page-' + str(page) + '.html'

        return new_path

    def is_serial(self, path):
        document = self.get_movie_document(path)

        content = tostring(document.xpath('body')[0])

        data = self.get_session_data(content)

        return data and data['content_type'] == 'serial'

    def get_thumb(self, path):
        if path.find(self.URL) < 0:
            thumb = self.URL + path
        else:
            thumb = path

        return thumb

    def get_episode_url(self, url, season, episode):
        if season:
            return '%s?season=%d&episode=%d' % (url, int(season), int(episode))

        return url

    def get_episode_info(self, title):
        try:
            info = self.parse_news_title(title)
            title = u'%s - S%dE%d (%s)' % (
                info['title'],
                int(info['season']),
                int(info['episode']),
                info['date']
            )

            season = info['season']
            episode = info['episode']
        except:
            season = None
            episode = None

        return {"season": season, "episode": episode, "title": title}

    def parse_news_title(self, title):
        return re.compile(
            u'(?P<date>\d{2}\.\d{2}\.\d{4})\sДобавлена'
            u'\s(?P<episode>\d+)\sсерия\sсериала\s(?P<title>.+)'
            u'\s(?P<season>\d+)\sсезон'
        ).match(title).groupdict()

    def replace_keys(self, s, keys):
        s = s.replace('\'', '"')

        for key in keys:
            s = s.replace(key + ':', '"' + key + '":')

        return s

    def convert_duration(self, s):
        tokens = s.split(':')

        result = []

        for token in tokens:
            data = re.search('(\d+)', token)

            if data:
                result.append(data.group(0))

        if len(result) == 3:
            hours = int(result[0])
            minutes = int(result[1])
            seconds = int(result[2])
        elif len(result) == 2:
            hours = int(result[0])
            minutes = int(result[1])
            seconds = 0
        else:
            hours = 0
            minutes = int(result[0])
            seconds = 0

        return hours * 60 * 60 + minutes * 60 + seconds
