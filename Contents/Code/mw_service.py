import re
import base64
import json

from http_service import HttpService

class MwService(HttpService):

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

    def get_session_data(self, response):
        session_data = re.compile(
            ('\$\.post\(\'/sessions\/create_session\', {((?:.|\n)+)}\)\.success')
        ).search(response, re.MULTILINE)

        if session_data:
            session_data = session_data.group(1).replace('condition_detected ? 1 : ', '')

            new_session_data = self.replace_keys('{%s}' % session_data,
                                                 ['partner', 'd_id', 'video_token', 'content_type', 'access_key', 'cd'])

            return json.loads(new_session_data)

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

    def get_url(self, headers, data, url=None, season=None, episode=None):
        response = self.http_request(method='POST', url='http://moonwalk.cc/sessions/create_session',
                                     headers=headers, data=data)

        data = json.loads(response.read())

        manifest_url = data['manifest_m3u8']

        response2 = self.http_request(manifest_url)

        data2 = response2.read()

        # print(data2)

        url2 = [line for line in data2.splitlines() if line].pop()

        return url2

    # def get_play_list(self, url):
    #     path = url.replace('tracks-2,4', 'tracks-1,4').split('/')
    #     path.pop()
    #     path = '/'.join(path)
    #
    #     response = self.http_request(url).read().splitlines()
    #
    #     for i in range(0, len(response)):
    #         if response[i] == '#EXT-X-ENDLIST':
    #             break
    #         if response[i][:1] != '#':
    #             response[i] = path + '/' + response[i]
    #
    #     return "\n".join(response)

    def replace_keys(self, s, keys):
        s = s.replace('\'', '"')

        for key in keys:
            s = s.replace(key + ':', '"' + key + '":')

        return s