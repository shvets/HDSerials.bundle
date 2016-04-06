# -*- coding: utf-8 -*-

import constants
import urllib

from urllib import urlencode

@route(constants.PREFIX + '/news')
def ShowNews():
    page = GetPage('/').xpath(
        '//div[@id="gkHeaderheader1"]//div[@class="custom"]/div'
    )

    if not page:
        return ContentNotFound()

    oc = ObjectContainer(title2=u'Новые серии')
    for item in page:
        title = u'%s' % item.text_content()
        try:
            info = ParseNewsTitle(title)
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
            pass
        oc.add(DirectoryObject(
            key=Callback(
                ShowInfo,
                path=item.find('a').get('href'),
                season=season
            ),
            title=title
        ))

    return oc


@route(constants.PREFIX + '/popular')
def ShowPopular():
    page = GetPage('/popular.html').xpath(
        '//div[contains(@class, "nspArts")]//div[contains(@class, "nspArt")]/div'
    )
    if not page:
        return ContentNotFound()

    oc = ObjectContainer(title2=u'Популярное')
    for item in page:
        link = item.find('a')
        if link:
            oc.add(DirectoryObject(
                key=Callback(ShowInfo, path=link.get('href')),
                title=item.find('h4').text_content(),
                thumb=link.find('img').get('src')
            ))

    return oc


@route(constants.PREFIX + '/category')
def ShowCategory(path, title, show_items=False):
    page = GetPage(path)

    if not page:
        return ContentNotFound()

    oc = ObjectContainer(title2=u'%s' % title)

    items = page.xpath(
        '//div[@class="itemList"]//div[@class="catItemBody"]//span[@class="catItemImage"]/a'
    )

    cats = None

    if not show_items:
        cats = page.xpath(
            '//div[@class="itemListSubCategories"]//div[contains(@class, "subCategory")]/h2/a'
        )

    if cats:
        # Add all items category
        if items:
            oc.add(DirectoryObject(
                title=u'Все %s' % title.lower(),
                key=Callback(ShowCategory, path=path, title=title, show_items=True)
            ))

        for item in cats:
            title = u'%s' % item.text_content()
            oc.add(DirectoryObject(
                title=title,
                key=Callback(ShowCategory, path=item.get('href'), title=title)
            ))
    elif items:
        # View subcategory with single item
        if not show_items and len(items) == 1:
            return ShowInfo(items[0].get('href'))

        for item in items:
            title = u'%s' % item.text_content()
            oc.add(DirectoryObject(
                title=u'%s' % item.get('title'),
                key=Callback(ShowInfo, path=item.get('href')),
                thumb='%s%s' % (
                    service.URL,
                    item.find('img').get('src')
                ),
            ))
        next_page = page.xpath(
            '//div[@class="k2Pagination"]/ul/li[@class="pagination-next"]/a'
        )
        if next_page:
            oc.add(NextPageObject(
                title=u'%s' % next_page[0].text_content(),
                key=Callback(
                    ShowCategory,
                    path=next_page[0].get('href'),
                    title=title,
                    show_items=True
                )
            ))
    else:
        return ContentNotFound()

    return oc


@route(constants.PREFIX + '/history')
def History():
    history_object = history.load_history()

    if not history_object or not len(history_object):
        return ContentNotFound()

    oc = ObjectContainer(title2=u'История')

    for item in sorted(
        history_object.values(),
        key=lambda k: k['time'],
        reverse=True
    ):
        oc.add(DirectoryObject(
            key=Callback(
                ShowInfo,
                path=item['path']
            ),
            title=u'%s' % item['title'],
            thumb=item['thumb']
        ))

    return oc

@route(constants.PREFIX + '/info')
def ShowInfo(path, **kwargs):
    info = ParsePage(path)

    if not info:
        return ContentNotFound()

    if 'season' in kwargs:
        info['season'] = kwargs['season']
    else:
        info['season'] = None

    if 'episode' in kwargs:
        info['episode'] = kwargs['episode']
    else:
        info['episode'] = None

    history.push_to_history(info)

    if 'seasons' in info:
        if 'season' in kwargs and kwargs['season'] in info['seasons']:
            return Episodes(info['path'], kwargs['season'])

        return Seasons(info['path'])

    try:
        vo = GetVideoObject(info)
    except:
        return ContentNotFound()

    return ObjectContainer(objects=[vo], content=ContainerContent.Movies)

@route(constants.PREFIX + '/seasons')
def Seasons(path):

    data = ParsePage(path)
    if not data:
        return ContentNotFound()

    if len(data['seasons']) == 1:
        return Episodes(path, data['current_season'])

    oc = ObjectContainer(
        title2=data['title'],
        content=ContainerContent.Seasons,
    )
    seasons = data['seasons'].keys()

    seasons.sort(key=lambda k: int(k))
    for season in seasons:
        oc.add(SeasonObject(
            key=Callback(
                Episodes,
                path=path,
                season=season
            ),
            rating_key=GetEpisodeURL(data['url'], season, 0),
            index=int(season),
            title=data['seasons'][season],
            source_title=unicode(L('Title')),
            thumb=data['thumb'],
            # summary=data['summary']
        ))

    return oc


@route(constants.PREFIX + '/episodes')
def Episodes(path, season):
    Log.Debug('Get episodes for %s' % path)

    data = ParsePage(path)
    if not data:
        return ContentNotFound()

    if data['session'] == 'external':
        oc = ObjectContainer(
            title2=u'%s' % data['title'],
            content=ContainerContent.Episodes
        )
        for episode in data['episodes']:
            Log.Debug('Try to get metadata from external: %s' % episode)
            try:
                oc.add(URLService.MetadataObjectForURL(
                    data['episodes'][episode]['url']
                ))
            except:
                continue
        return oc if len(oc) else ContentNotFound()

    if season != data['current_season']:
        data = UpdateItemInfo(data, season, 1)
        if not data:
            return ContentNotFound()

    oc = ObjectContainer(
        title2=u'%s / %s' % (data['title'], data['seasons'][season]),
        content=ContainerContent.Episodes
    )

    episodes = data['episodes'].keys()
    episodes.sort(key=lambda k: int(k))

    for episode in episodes:
        oc.add(GetVideoObject(data, episode))

    return oc

@route(constants.PREFIX + '/getmeta')
def GetMeta(path, episode):
    episode = int(episode)

    item = ParsePage(path)
    if episode and episode != item['current_episode']:
        item = UpdateItemInfo(item, item['current_season'], episode)

    return JSON.StringFromObject(item)


###############################################################################
# Common
###############################################################################

def ContentNotFound():
    return MessageContainer(
        L('Ошибка'),
        L('Контент не найден')
    )


def ParsePage(path):
    if service.URL not in path:
        path = service.URL+path

    ret = service.load_cache(path)

    if ret:
        return ret

    page = GetPage(path).xpath(
        '//div[@id="k2Container"]'
    )[0]

    data = {'variants': {}}
    try:
        for url in page.xpath(
            '//div[@class="itemFullText"]//iframe[@src]'
        ):
            Log.Debug('Found variant %s', url)
            variant = GetInfoByURL(url.get('src'))
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
    except:
        return None

    ret = {
        'path': path,
        'rating': 0.00,
        'thumb': '%s%s' % (
            service.URL,
            page.xpath(
                '//div[@class="itemImageBlock"]//a'
            )[0].get('href')
        ),
    }

    title = [
        l.strip() for l in page.xpath(
            '//h2[@class="itemTitle"]'
        )[0].text_content().split('/')
    ]

    ret['original_title'] = title.pop() if len(title) > 1 else None
    ret['title'] = ' / '.join(title)

    meta = page.xpath(
        '//div[@class="itemFullText"]//text() ' +
        '| //div[@class="itemFullText"]//span ' +
        '| //div[@class="itemFullText"]//strong ' +
        '| //div[@class="itemFullText"]//p[@style="text-align: center;"]'
    )

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
                data[tmap[current]] = data[tmap[current]]+' '+unicode(desc)
            else:
                data[tmap[current]] = unicode(desc)

    for current in ('countries', 'genres', 'directors', 'roles'):
        if current in data:
            data[current] = [l.strip() for l in data[current].split(',')]

    # TODO
    data['duration'] = None
    # data['duration'] = Datetime.MillisecondsFromString(data['duration'])

    data['rating'] = float(Regex('width\s?:\s?([\d\.]+)').search(
        page.xpath(
            '//div[@class="itemRatingBlock"]//li[@class="itemCurrentRating"]'
        )[0].get('style')
    ).group(1)) / 10

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

    service.save_cache(ret)

    return ret


def UpdateItemInfo(item, season, episode):
    url = item['url']
    season = str(season)

    if season not in item['variants'][url]['seasons']:
        # Try to search variant with season
        for variant in item['variants'].values():
            if season in variant['seasons']:
                url = variant['url']
                if int(season) == variant['current_season'] and int(episode) == variant['current_episode']:
                    update = variant.copy()
                    del update['seasons']
                    item.update(update)
                    return item
                break

    update = GetInfoByURL(GetEpisodeURL(
        url,
        season,
        episode
    ), url)
    if not update:
        return None

    item['variants'][url].update(update.copy())

    del update['seasons']
    item.update(update)

    service.save_cache(item)

    return item

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
        'source_title': unicode(L('Title')),
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