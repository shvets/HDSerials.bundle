# -*- coding: utf-8 -*-

import constants
import urllib

from urllib import urlencode

@route(constants.PREFIX + '/search')
def HandleSearch(query):
    oc = ObjectContainer(title2=u'%s' % L('Поиск'))

    try:
        HTTP.Headers['Referer'] = '%s/' % service.URL
        res = JSON.ObjectFromURL(
            '%s/index.php?%s' % (service.URL, urlencode({
                'option': 'com_k2',
                'view': 'itemlist',
                'task': 'search',
                'searchword': query,
                'categories': '',
                'format': 'json',
                'tpl': 'search',
            }))
        )
    except:
        return oc

    if 'items' in res:
        for item in res['items']:
            rating_key = item['link']

            if item['title'] in item['category']['name']:
                title = u'%s' % item['category']['name']
                key = '%s?%s' % (constants.PREFIX + '/info', urlencode({'path': item['link']}))

                oc.add(TVShowObject(title=title, key=key, rating_key=rating_key,
                                       thumb='%s%s' % (service.URL, item['image']),
                                       summary=HTML.ElementFromString(item['introtext']).text_content()))
            else:
                title = u'%s / %s' % (item['category']['name'], item['title'])
                # key = URLService.LookupURLForMediaURL(service.URL + item['link'])

                key = Callback(HandleMovie, title=title, url=service.URL + item['link'])
                    # ,
                    #            rating_key=rating_key,
                    #            thumb='%s%s' % (service.URL, item['image']),
                    #            summary=HTML.ElementFromString(item['introtext']).text_content())

                # oc.add(MovieObject(title=title, key=key, rating_key=rating_key,
                #                        thumb='%s%s' % (service.URL, item['image']),
                #                        summary=HTML.ElementFromString(item['introtext']).text_content()))

                oc.add(DirectoryObject(key=key, title=title))
    return oc

@route(constants.PREFIX + '/movie')
def HandleMovie(title, url, **params):
    oc = ObjectContainer(title2=unicode(title))

    oc.add(MetadataObjectForURL(url))

    return oc

def MetadataObjectForURL(url):
    url = InitMetaUrl(url)

    item = url.item
    episode = url.episode

    kwargs = {
        'source_title': L('Title'),
    }

    for k in ['summary', 'thumb', 'directors', 'rating', 'duration', 'originally_available_at']:
        if k in item and item[k]:
            kwargs[k] = item[k]

    if episode:
        if 'roles' in item:
            kwargs['guest_stars'] = item['roles']

        title = item['episodes'][str(episode)]

        video = EpisodeObject(
            rating_key=GetEpisodeURL(
                item['url'],
                item['current_season'],
                episode
            ),
            title=title,
            season=int(item['current_season']),
            index=int(episode),
            show=item['title'],
            **kwargs
        )
    else:
        for k in ['year', 'original_title', 'countries']:
            if k in item and item[k]:
                kwargs[k] = item[k]

        title = item['title']
        video = MovieObject(
            title=title,
            rating_key=item['url'],
            **kwargs
        )

    rating_key = 'rating_key'
    # video.rating = 5.0
    thumb = item['thumb']
    # video.year = data['year']
    # video.tags = data['tags']
    # video.duration = data['duration'] * 60 * 1000
    summary = 'summary'

    video.key = Callback(HandleMovie, title=title, url=url)
        # , rating_key=rating_key, thumb=thumb, summary=summary,
        #                  container=True)

    video.items = MediaObjectsForURL(url)

    return video

def MediaObjectsForURL(url):
    items = []

    url = InitMetaUrl(url)
    item = url.item

    for variant in item['variants'].values():
        if url.episode and (str(item['current_season']) not in variant['seasons'] or str(url.episode) not in variant['episodes']):
            continue

        session = None
        url_update = None
        episode = None
        season = None

        if item['url'] == variant['url'] and not url.episode:
            session = JSON.StringFromObject(variant['session'])
        else:
            url_update = variant['url']
            if url.episode:
                season = item['current_season']
                episode = url.episode

        media_object = MediaObject(
            parts=[PartObject(
                key=Callback(Play, url=url_update, season=season, episode=episode, session=session),
            )],
            video_resolution=720,
            container='mpegts',
            video_codec=VideoCodec.H264,
            audio_codec=AudioCodec.AAC,
            optimized_for_streaming=True,
            audio_channels=2
        )

        items.append(media_object)

    return items

def InitMetaUrl(url):
    Log.Debug('Normalize URL: %s' % url)

    try:
        # has attribute crutch
        if url.item:
            return url
    except:

        # Fetch there. Replace - Samsung-TV crutch
        res = url.replace('%7C%7C', '||').split('||')
        res.reverse()

        path = res.pop()
        episode = res.pop() if len(res) else 0

        url = MetaUrl(url)

        try:
            res = JSON.ObjectFromString(urllib.urlopen(
                'http://127.0.0.1:32400%s?%s' % (
                    '/video/hdserials/getmeta',
                    urllib.urlencode({
                        'path': path,
                        'episode': episode
                    })
                )
            ).read())

            if res:
                return url.update(res, episode)

        except Exception as e:
            Log.Error(u'%s' % e)
            pass

    raise Ex.MediaNotAvailable

class MetaUrl(str):
    item = None
    episode = None

    def update(self, item, episode):
        self.item = item
        self.episode = int(episode)
        return self

@indirect
@route(constants.PREFIX + '/play')
def Play(session, url, season, episode):
    Log('Play')
    Log.Debug('Get playlist from %s' % url)

    if not session:
        url_info = GetInfoByURL(GetEpisodeURL(
            url, season, episode
        ), url)

        if not url_info:
            raise Ex.MediaNotAvailable

        session = url_info['session']
    else:
        session = JSON.ObjectFromString(session)

    res = JSON.ObjectFromURL(
        url='http://moonwalk.cc/sessions/create_session',
        values=session['values'],
        headers=session['headers'],
        method='POST',
        cacheTime=0
    )

    if not res:
        raise Ex.MediaNotAvailable

    try:
        res = HTTP.Request(res['manifest_m3u8']).content
        Log.Debug('Found streams: %s' % res)
    except:
        raise Ex.MediaNotAvailable

    res = [line for line in res.splitlines() if line].pop()

    Log.Debug('Try to play %s' % res)

    res = Callback(Playlist, res=res)

    return IndirectResponse(VideoClipObject, key=HTTPLiveStreamURL(res))

def GetEpisodeURL(url, season, episode):
    if season:
        return '%s?season=%d&episode=%d' % (url, int(season), int(episode))
    return url


def GetInfoByURL(url, parent=None):
    if not Regex('http://moonwalk\.cc/').match(url):
        return {
            'url': url.replace('vkontakte.ru', 'vk.com'),
            'session': 'external',
        }

    headers = {}
    if parent:
        headers['Referer'] = parent
        if 'Referer' in HTTP.Headers:
            url = '%s&%s' % (
                url,
                urllib.urlencode({'referer': HTTP.Headers['Referer']})
            )

    elif 'Referer' in HTTP.Headers:
        headers['Referer'] = HTTP.Headers['Referer']

    try:
        page = HTTP.Request(
            url,
            cacheTime=300,
            headers=headers
        ).content
    except Ex.HTTPError, e:
        Log.Debug(e.hdrs)
        Log(e.msg)
        return None

    data = Regex(
        ('\$\.post\(\'/sessions\/create_session\', {((?:.|\n)+)}\)\.success')
    ).search(page, Regex.MULTILINE)

    if not data:
        return None

    data = data.group(1).replace('condition_detected ? 1 : ', '')

    ret = {
        'url': parent if parent else url,
        'session': {
            'values': JSON.ObjectFromString('{%s}' % data),
            'headers': {
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': url,
                'Cookie': HTTP.CookiesForURL(url)
            },
        }
    }

    data = Regex(
        ('xhr.setRequestHeader\([\'"](.+)[\'"],[ ]*[\'"](.+)[\'"]\)')
    ).findall(page, Regex.MULTILINE)

    if data:
        for k, v in data:
            ret['session']['headers'][k] = v

    data = Regex(
        ('setRequestHeader\|([^|]+)')
    ).search(page, Regex.MULTILINE)

    if data:
        ret['session']['headers']['Content-Data'] = String.Base64Encode(
            data.group(1)
        )

    if ret['session']['values']['content_type'] == 'serial':
        res = HTML.ElementFromString(page)
        ret['seasons'] = {}
        ret['episodes'] = {}
        for item in res.xpath('//select[@id="season"]/option'):
            value = item.get('value')
            ret['seasons'][value] = unicode(item.text_content())
            if item.get('selected'):
                ret['current_season'] = value

        for item in res.xpath('//select[@id="episode"]/option'):
            value = item.get('value')
            ret['episodes'][value] = unicode(item.text_content())
            if item.get('selected'):
                ret['current_episode'] = value

    return ret

def GetPage(uri, cacheTime=CACHE_1HOUR):
    try:
        if service.URL not in uri:
            uri = service.URL+uri

        res = HTML.ElementFromString(Regex(
            '<style=[^>]+>([^:]+)',
            Regex.MULTILINE
        ).sub(
            r'<span>\1</span>',
            HTTP.Request(uri, cacheTime=cacheTime).content
        ))

        HTTP.Headers['Referer'] = uri
    except:
        res = HTML.Element('error')

    return res

@route(constants.PREFIX + '/play_list.m3u8')
def Playlist(res):
    # Some players does not support gziped response
    Log.Debug('Modify playlist %s' % res)

    path = res.replace('tracks-2,4', 'tracks-1,4').split('/')
    path.pop()
    path = '/'.join(path)
    try:
        res = HTTP.Request(res).content.splitlines()
    except:
        raise Ex.MediaNotAvailable

    for i in range(0, len(res)):
        if res[i] == '#EXT-X-ENDLIST':
            break
        if res[i][:1] != '#':
            res[i] = path + '/' + res[i]

    return "\n".join(res)

def ParseNewsTitle(title):
    return Regex(
        u'(?P<date>\d{2}\.\d{2}\.\d{4})\sДобавлена'
        u'\s(?P<episode>\d+)\sсерия\sсериала\s(?P<title>.+)'
        u'\s(?P<season>\d+)\sсезон'
    ).match(title).groupdict()

def GetVideoObject(item, episode=0):

    if item['session'] == 'external':
        url = item['url']
    else:
        url = MetaUrl('%s||%s' % (item['path'], episode))
        url.update(item, episode)

    return MetadataObjectForURL(url)

@route(constants.PREFIX + '/queue')
def HandleQueue(title):
    oc = ObjectContainer(title2=unicode(title))

    for item in service.queue.data:
        if 'episode' in item:
            oc.add(DirectoryObject(
                key=Callback(HandleMovie, **item),
                title=unicode(item['title']),
                thumb=item['thumb']
            ))
        elif 'season' in item:
            oc.add(DirectoryObject(
                key=Callback(HandleEpisodes, **item),
                title=unicode(item['name']),
                thumb=item['thumb']
            ))
        else:
            oc.add(DirectoryObject(
                key=Callback(HandleContainer, **item),
                title=unicode(item['title']),
                thumb=item['thumb']
            ))

    return oc