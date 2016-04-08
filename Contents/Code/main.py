# -*- coding: utf-8 -*-

import urllib
from urllib import urlencode

import constants
import util
from flow_builder import FlowBuilder

builder = FlowBuilder()

@route(constants.PREFIX + '/news')
def ShowNews():
    oc = ObjectContainer(title2=u'Новые серии')

    new_series = service.get_new_series()

    for item in new_series:
        path = item['path']

        info = get_episode_info(item['title'])

        oc.add(DirectoryObject(
            key=Callback(ShowInfo, path=path, season=info['season'], episode=info['episode']),
            title=item['title']
        ))

    return oc

@route(constants.PREFIX + '/popular')
def ShowPopular():
    oc = ObjectContainer(title2=unicode(L('Popular')))

    items = service.get_popular()

    for item in items:
        Log(item)
        title = item['title']
        path = item['path']
        thumb = item['thumb']

        if path:
            oc.add(DirectoryObject(key=Callback(ShowInfo, path=path), title=title, thumb=thumb))

    # todo: add pagination

    return oc

@route(constants.PREFIX + '/category')
def ShowCategory(path, title, show_items=False, page=1):
    oc = ObjectContainer(title2=u'%s' % title)

    items = service.get_category_items(path)

    cats = None

    if not show_items:
        cats = service.get_categories(path)

    if cats:
        # Add all items category
        if items:
            oc.add(DirectoryObject(
                title=u'Все %s' % title.lower(),
                key=Callback(ShowCategory, path=path, title=title, show_items=True)
            ))

        for item in cats:
            title = u'%s' % item['title']
            oc.add(DirectoryObject(
                title=title,
                key=Callback(ShowCategory, path=item['path'], title=title)
            ))
    elif items:
        # View subcategory with single item
        if not show_items and len(items) == 1:
            return ShowInfo(items[0]['path'])

        for item in items:
            title = u'%s' % item['title']
            oc.add(DirectoryObject(
                title=u'%s' % item['title'],
                key=Callback(ShowInfo, path=item['path']),
                thumb='%s%s' % (service.URL, item['thumb']),
            ))

        # document = service.fetch_document(path)
        # result["pagination"] = service.extract_pagination_data(document, path)
        #
        # pagination.append_controls(oc, response, page=page, callback=ShowCategory, title=title, path=path)

        # next_page = page.xpath(
        #     '//div[@class="k2Pagination"]/ul/li[@class="pagination-next"]/a'
        # )

        next_page = service.get_pagination(path)

        if next_page:
            oc.add(NextPageObject(
                title=u'%s' % next_page[0]['title'],
                key=Callback(ShowCategory, path=next_page[0]['path'], title=title, show_items=True)
            ))

    return oc

@route(constants.PREFIX + '/info')
def ShowInfo(path, **kwargs):
    #info = ParsePage(path)
    info = service.parse_page(path)

    if not info:
        return util.no_contents()

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
        return util.no_contents()

    return ObjectContainer(objects=[vo], content=ContainerContent.Movies)

@route(constants.PREFIX + '/seasons')
def Seasons(path):
    #data = ParsePage(path)
    data = service.parse_page(path)

    if not data:
        return util.no_contents()

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

    #data = ParsePage(path)
    data = service.parse_page(path)

    if not data:
        return util.no_contents()

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
        return oc if len(oc) else util.no_contents()

    if season != data['current_season']:
        data = UpdateItemInfo(data, season, 1)
        if not data:
            return util.no_contents()

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

    #item = ParsePage(path)
    item = service.parse_page(path)
    if episode and episode != item['current_episode']:
        item = UpdateItemInfo(item, item['current_season'], episode)

    return JSON.StringFromObject(item)


###############################################################################
# Common
###############################################################################

# def ParsePage(path):
#     if service.URL not in path:
#         path = service.URL+path
#
#     # ret = service.load_cache(path)
#     #
#     # if ret:
#     #     return ret
#
#     # page = GetPage(path).xpath(
#     #     '//div[@id="k2Container"]'
#     # )[0]
#
#     document = service.fetch_document(path)
#     page = document.xpath('//div[@id="k2Container"]')[0]
#
#     data = {'variants': {}}
#     try:
#         for url in page.xpath(
#             '//div[@class="itemFullText"]//iframe[@src]'
#         ):
#             Log.Debug('Found variant %s', url)
#             variant = GetInfoByURL(url.get('src'))
#             if variant:
#                 data['variants'][variant['url']] = variant
#                 if 'session' not in data:
#                     data.update(variant)
#                     if 'seasons' in data:
#                         data['seasons'] = variant['seasons'].copy()
#                 else:
#                     if 'seasons' in variant:
#                         data['seasons'].update(variant['seasons'])
#
#
#         if len(data['variants']) == 0:
#             return None
#     except:
#         return None
#
#     ret = {
#         'path': path,
#         'rating': 0.00,
#         'thumb': '%s%s' % (
#             service.URL,
#             page.xpath(
#                 '//div[@class="itemImageBlock"]//a'
#             )[0].get('href')
#         ),
#     }
#
#     title = [
#         l.strip() for l in page.xpath(
#             '//h2[@class="itemTitle"]'
#         )[0].text_content().split('/')
#     ]
#
#     ret['original_title'] = title.pop() if len(title) > 1 else None
#     ret['title'] = ' / '.join(title)
#
#     meta = page.xpath(
#         '//div[@class="itemFullText"]//text() ' +
#         '| //div[@class="itemFullText"]//span ' +
#         '| //div[@class="itemFullText"]//strong ' +
#         '| //div[@class="itemFullText"]//p[@style="text-align: center;"]'
#     )
#
#     tmap = {
#         u'Описание': 'summary',
#         u'Год выпуска': 'year',
#         u'Страна': 'countries',
#         u'Жанр': 'genres',
#         u'Продолжительность': 'duration',
#         u'Режиссер': 'directors',
#         u'В ролях': 'roles',
#     }
#
#     current = None
#     variants_names = []
#     for desc in meta:
#         if not isinstance(desc, basestring):
#             if desc.tag == 'p' and u'Перевод' in desc.text_content():
#                 variants_names.append(desc.text_content())
#                 current = None
#             continue
#         if not desc:
#             continue
#
#         if desc in tmap:
#             current = desc
#         elif current:
#             if desc[:1] == ':':
#                 desc = desc[2:]
#
#             if tmap[current] in data:
#                 data[tmap[current]] = data[tmap[current]]+' '+unicode(desc)
#             else:
#                 data[tmap[current]] = unicode(desc)
#
#     for current in ('countries', 'genres', 'directors', 'roles'):
#         if current in data:
#             data[current] = [l.strip() for l in data[current].split(',')]
#
#     # TODO
#     data['duration'] = None
#     # data['duration'] = Datetime.MillisecondsFromString(data['duration'])
#
#     data['rating'] = float(Regex('width\s?:\s?([\d\.]+)').search(
#         page.xpath(
#             '//div[@class="itemRatingBlock"]//li[@class="itemCurrentRating"]'
#         )[0].get('style')
#     ).group(1)) / 10
#
#     if 'year' in data:
#         if '-' in data['year']:
#             data['year'] = data['year'].split('-')[0]
#
#         data['year'] = int(data['year'])
#
#     for k in data['variants']:
#         data['variants'][k]['variant_title'] = unicode(
#             variants_names.pop(0)
#         ) if variants_names else ''
#
#     if data['session'] == 'external':
#         if len(data['variants']) > 1:
#             data['seasons'] = {'1': ret['title']}
#             data['current_season'] = 1
#             data['episodes'] = data['variants']
#
#     ret.update(data)
#
#     # service.save_cache(ret)
#
#     return ret


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

    update = service.get_info_by_url(GetEpisodeURL(url, season, episode), HTTP.Headers, url)

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

        rating_key = GetEpisodeURL(
            item['url'],
            item['current_season'],
            episode
        )

        video = builder.build_metadata_object(media_type='episode', rating_key=rating_key, title=title,
            season=int(item['current_season']), index=int(episode), show=item['title'], **kwargs)
    else:
        for k in ['year', 'original_title', 'countries']:
            if k in item and item[k]:
                kwargs[k] = item[k]

        title = item['title']

        video = builder.build_metadata_object(media_type='movie', title=title, rating_key=item['url'], **kwargs)

    video.key = Callback(HandleMovie, title=title, url=url)

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

        play_callback = Callback(Play, url=url_update, season=season, episode=episode, session=session)

        media_object = builder.build_media_object(play_callback)

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
        url_info = service.get_info_by_url(GetEpisodeURL(
            url, season, episode
        ), HTTP.Headers, url)

        if not url_info:
            raise Ex.MediaNotAvailable

        session = url_info['session']
    else:
        session = JSON.ObjectFromString(session)

    res = JSON.ObjectFromURL(
        url='http://moonwalk.cc/sessions/create_session',
        values=session['data'],
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

def GetVideoObject(item, episode=0):
    if item['session'] == 'external':
        url = item['url']
    else:
        url = MetaUrl('%s||%s' % (item['path'], episode))
        url.update(item, episode)

    return MetadataObjectForURL(url)

@route(constants.PREFIX + '/history')
def History():
    history_object = history.load_history()

    oc = ObjectContainer(title2=u'История')

    if history_object:
        for item in sorted(history_object.values(), key=lambda k: k['time'], reverse=True):
            oc.add(DirectoryObject(
                key=Callback(
                    ShowInfo,
                    path=item['path']
                ),
                title=u'%s' % item['title'],
                thumb=item['thumb']
            ))

    return oc

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





def get_episode_info(title):
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

    return {"season": season, "episode": episode, "title": title}

def ParseNewsTitle(title):
    return Regex(
        u'(?P<date>\d{2}\.\d{2}\.\d{4})\sДобавлена'
        u'\s(?P<episode>\d+)\sсерия\sсериала\s(?P<title>.+)'
        u'\s(?P<season>\d+)\sсезон'
    ).match(title).groupdict()