# -*- coding: utf-8 -*-

import re
import json
from lxml.etree import tostring
from operator import itemgetter

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

        pagination = self.extract_pagination_data_from_array(items, page, per_page)

        return {"movies": list, "pagination": pagination["pagination"]}

    def get_subcategories(self, path, page=1, per_page=20):
        page = int(page)
        per_page = int(per_page)

        list = []

        document = self.fetch_document(self.URL + path)

        items = document.xpath('//div[@class="itemListSubCategories"]//div[contains(@class, "subCategory")]/h2/a')

        for index, item in enumerate(items):
            if index >= (page - 1) * per_page and index < page * per_page:
                href = item.xpath('@href')[0]
                title = item.text_content()

                list.append({'path': href, 'title': title})

        pagination = self.extract_pagination_data_from_array(items, page, per_page)

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

    def extract_pagination_data_from_array(self, items, page, per_page):
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

        titles = [l.strip() for l in title_block]

        if len(titles) > 1:
          data['title'] = titles[0] + ' / ' + titles[1]
        else:
            data['title'] = titles[0]

        data['rating'] = float(re.compile('width\s?:\s?([\d\.]+)').search(
            block.xpath('//div[@class="itemRatingBlock"]//li[@class="itemCurrentRating"]')[0].get('style')
        ).group(1)) / 10

        description_block = block.xpath('//div[@class="itemFullText"]')[0]

        description = {}

        for elem in description_block.xpath('p')[0]:
            key = unicode(elem.text_content())

            if len(key.strip()) > 0:
                if key == u'Продолжительность':
                    value = elem.tail.strip()[2:]
                elif elem.tail:
                    value = elem.tail.replace(':', '')
                else:
                    value = ''

                description[key] = value

        if len(description) > 0:
            if u'В ролях' not in description:
                description[u'В ролях'] = ''
        else:
            text = description_block.text_content()

            text, roles = text.split(u'В ролях:')
            text, director = text.split(u'Режиссер:')
            text, translation = text.split(u'Перевод:')
            text, duration = text.split(u'Продолжительность:')
            text, genre = text.split(u'Жанр:')
            text, country = text.split(u'Страна:')
            text, year = text.split(u'Год выпуска:')
            _, text = text.split(u'Описание:')

            description[u'Описание'] = text
            description[u'Страна'] = country
            description[u'Жанр'] = genre
            description[u'Перевод'] = translation
            description[u'Режиссер'] = director
            description[u'В ролях'] = roles
            description[u'Продолжительность'] = duration
            description[u'Год выпуска'] = year

        summary = description[u'Описание'] + '\n' + \
            u'Страна'  + ': ' + description[u'Страна'] + '\n' + \
            u'Жанр' + ': ' + description[u'Жанр'] + '\n' + \
            u'Перевод' + ': ' + description[u'Перевод'] + '\n' + \
            u'Режиссер' + ': ' + description[u'Режиссер'] + '\n' + \
            u'В ролях' + ': ' + description[u'В ролях'] + '\n'

        data['duration'] = self.convert_duration(description[u'Продолжительность'])

        try:
            data['year'] = int(description[u'Год выпуска'])
        except:
            data['year'] = int(description[u'Год выпуска'][0:4])

        data['tags'] = description[u'Жанр'].replace(',', ', ').split(',')
        data['genres'] = description[u'Жанр'].replace(',', ', ').split(',')
        data['summary'] = summary
        data['countries'] = description[u'Страна'].split(',')
        data['directors'] = description[u'Режиссер'].split(' ')

        return data

    def retrieve_urls(self, url, season=None, episode=None):
        if url.find(self.URL) < 0:
            url = self.URL + url

        document = self.get_movie_documents(url, season=season, episode=episode)[0]['movie_document']
        content = tostring(document.xpath('body')[0])

        data = self.get_session_data(content)

        headers = {
            'X-Requested-With': 'XMLHttpRequest',
            'Referer': url,
            'Content-Data': self.get_content_data(content)
        }

        return sorted(self.get_urls(headers, data), key=itemgetter('bandwidth'), reverse=True)

    def get_movie_documents(self, url, season=None, episode=None):
        movie_documents = []

        document = self.fetch_document(url)

        release_names = self.get_release_names(document)
        gateway_urls = self.get_gateway_urls(document)

        for index, gateway_url in enumerate(gateway_urls):
            if season:
                movie_url = '%s?season=%d&episode=%d' % (gateway_url, int(season), int(episode))
            else:
                movie_url = gateway_url

            movie_document = self.fetch_document(movie_url, self.get_headers(url))

            if len(release_names) > 0:
                release = release_names[index]
            else:
                release = 'unknown'

            movie_documents.append({'movie_document': movie_document, 'release': release})

        return movie_documents

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

    def get_gateway_urls(self, document):
        gateway_urls = []

        frame_block = document.xpath('//div[@id="k2Container"]')[0]

        urls_node = frame_block.xpath('//div[@class="itemFullText"]//iframe[@src]')

        for url_node in urls_node:
            url = url_node.get('src')

            gateway_urls.append(url)

        return gateway_urls

    def get_release_names(self, document):
        release_names = []

        block = document.xpath('//div[@id="k2Container"]')[0]

        p_nodes = block.xpath('//div[@class="itemFullText"]/p')


        for p_node in p_nodes:
            text = p_node.text

            if text and len(text.strip()) > 0:
                release_names.append(text)

        return release_names

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

    def is_serial(self, url):
        document = self.get_movie_documents(url)[0]['movie_document']

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
        s = s.replace('~', '').strip()

        if s.find(u'мин'):
            s = "00:" + s.replace(u'мин', '').replace(' ', '') + ":00"

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

    @staticmethod
    def get_headers(referer):
        return {
            'User-Agent': 'Plex-User-Agent',
            "Referer": referer
        }