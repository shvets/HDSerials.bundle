import re
import base64
import json

from http_service import HttpService

class MwService(HttpService):

    def get_session_data(self, response):
        session_data = re.compile(
            ('\$\.post\(\'/sessions\/create_session\', {((?:.|\n)+)}\)\.success')
        ).search(response, re.MULTILINE)

        if session_data:
            session_data = session_data.group(1).replace('condition_detected ? 1 : ', '')

            new_session_data = self.replace_keys('{%s}' % session_data,
                                                 ['partner', 'd_id', 'video_token', 'content_type', 'access_key', 'cd'])

            return json.loads(new_session_data)

    # def get_session_data(self, document):
    #     body = tostring(document.xpath('body')[0])
    #
    #     session_data = re.compile(
    #         ('\$\.post\(\'/sessions\/create_session\', {((?:.|\n)+)}\)\.success')
    #     ).search(body, re.MULTILINE)
    #
    #     if session_data:
    #         session_data = session_data.group(1).replace('condition_detected ? 1 : ', '')
    #
    #         new_session_data = self.replace_keys('{%s}' % session_data,
    #                                              ['partner', 'd_id', 'video_token', 'content_type', 'access_key', 'cd'])
    #
    #         return json.loads(new_session_data)

    def collect_session_data(self, url):
        response = self.http_request(url).read()

        return {
            'data': self.get_session_data(response),
            'headers': {
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': url,
                'Content-Data': self.get_content_data(response),
                'Cookie': self.get_cookies(response)
            },
        }

    def get_content_data(self, response):
        data = re.compile(
            ('setRequestHeader\|([^|]+)')
        ).search(response, re.MULTILINE)

        if data:
            return base64.b64encode(data.group(1))

    def get_cookies(self, response):
        return None

    def get_serial_info(self, url):
        ret = {}

        response = self.http_request(url)
        document = self.to_document(response.read())

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

    # def get_url(self, headers, data, url=None, season=None, episode=None):
    #     response = self.http_request(method='POST', url='http://moonwalk.cc/sessions/create_session',
    #                                  headers=headers, data=data)
    #
    #     data = json.loads(response.read())
    #
    #     manifest_url = data['manifest_m3u8']
    #
    #     response2 = self.http_request(manifest_url)
    #
    #     data2 = response2.read()
    #
    #     # print(data2)
    #
    #     url2 = [line for line in data2.splitlines() if line].pop()
    #
    #     return url2

    def get_urls(self, headers, data):
        response = self.http_request(method='POST', url='http://moonwalk.cc/sessions/create_session',
                                     headers=headers, data=data)

        data = json.loads(response.read())

        manifest_url = data['manifest_m3u8']

        response2 = self.http_request(manifest_url)

        data2 = response2.read()

        # url2 = [line for line in data2.splitlines() if line].pop()

        lines = data2.splitlines()

        urls = []

        for index, line in enumerate(lines):
            if line.startswith('#EXTM3U'):
                continue
            elif not line.startswith('#EXT-X-STREAM-INF'):
                data = re.search("#EXT-X-STREAM-INF:RESOLUTION=(\d+)x(\d+),BANDWIDTH=(\d+)", lines[index - 1])

                urls.append({"url": line, "width": data.group(1), "height": data.group(2), "bandwith": data.group(3)})

        return urls

    def replace_keys(self, s, keys):
        s = s.replace('\'', '"')

        for key in keys:
            s = s.replace(key + ':', '"' + key + '":')

        return s