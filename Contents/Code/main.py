# -*- coding: utf-8 -*-

import urllib
import json

import constants
import util
import pagination
from flow_builder import FlowBuilder

builder = FlowBuilder()

@route(constants.PREFIX + '/new_series')
def HandleNewSeries():
    oc = ObjectContainer(title2=u'Новые серии')

    new_series = service.get_new_series()

    for item in new_series:
        path = item['path']

        info = get_episode_info(item['title'])

        oc.add(DirectoryObject(
            key=Callback(HandleMovies, path=path, season=info['season'], episode=info['episode']),
            title=item['title']
        ))

    return oc

@route(constants.PREFIX + '/popular')
def HandlePopular(page=1):
    page = int(page)

    oc = ObjectContainer(title2=unicode(L('Popular')))

    response = service.get_popular(page=page)

    for index, item in enumerate(response['movies']):
        title = item['title']
        path = item['path']
        thumb = item['thumb']

        if path:
            oc.add(DirectoryObject(key=Callback(HandleMovies, path=path), title=title, thumb=thumb))

    pagination.append_controls(oc, response, page=int(page), callback=HandlePopular)

    return oc

@route(constants.PREFIX + '/categories')
def HandleCategories():
    oc = ObjectContainer(title2=unicode(L('Categories')))

    items = service.get_categories()

    for item in items:
        title = item['title']
        path = item['path']

        oc.add(DirectoryObject(
            key=Callback(HandleCategory, path=path, title=title),
            title=title
        ))

    return oc

@route(constants.PREFIX + '/category')
def HandleCategory(path, title):
    oc = ObjectContainer(title2=u'%s' % title)

    cats = service.get_subcategories(path)

    if cats:
        # Add all items category
        items = service.get_category_items(path)

        if items:
            oc.add(DirectoryObject(
                title=u'Все %s' % title.lower(),
                key=Callback(HandleCategoryItems, path=path, title=title)
            ))

        for item in cats:
            title = u'%s' % item['title']
            oc.add(DirectoryObject(
                title=title,
                key=Callback(HandleCategoryItems, path=item['path'], title=title)
            ))

    return oc

@route(constants.PREFIX + '/category_items')
def HandleCategoryItems(path, title, page=1):
    oc = ObjectContainer(title2=u'%s' % title)

    response = service.get_category_items(path, page)

    if response['movies']:
        for item in response['movies']:
            title = u'%s' % item['title']
            oc.add(DirectoryObject(
                title=u'%s' % item['title'],
                key=Callback(HandleMovies, path=item['path']),
                thumb='%s%s' % (service.URL, item['thumb']),
            ))

        pagination.append_controls(oc, response, page=page, callback=HandleCategoryItems, title=title, path=path)

    return oc

@route(constants.PREFIX + '/movies')
def HandleMovies(path, **kwargs):
    info = service.parse_page(path)

    if not info:
        return util.no_contents()

    # if 'season' in kwargs:
    #     info['season'] = kwargs['season']
    # else:
    #     info['season'] = None
    #
    # if 'episode' in kwargs:
    #     info['episode'] = kwargs['episode']
    # else:
    #     info['episode'] = None

    history.push_to_history(info)

    if 'seasons' in info:
        if 'season' in kwargs and kwargs['season'] in info['seasons']:
            return HandleEpisodes(info['path'], kwargs['season'])
        else:
          return HandleSeasons(info['path'])
    else:
        try:
            vo = GetVideoObject(info)

            return ObjectContainer(objects=[vo], content=ContainerContent.Movies)
        except:
            return util.no_contents()

@route(constants.PREFIX + '/seasons')
def HandleSeasons(path):
    data = service.parse_page(path)

    # if not data:
    #     return util.no_contents()

    if len(data['seasons']) == 1:
        return HandleEpisodes(path, data['current_season'])

    oc = ObjectContainer(
        title2=data['title'],
        content=ContainerContent.Seasons,
    )

    seasons = data['seasons'].keys()

    seasons.sort(key=lambda k: int(k))

    for season in seasons:
        oc.add(SeasonObject(
            key=Callback(HandleEpisodes, path=path, season=season),
            rating_key=service.get_episode_url(data['url'], season, 0),
            index=int(season),
            title=data['seasons'][season],
            source_title=unicode(L('Title')),
            thumb=data['thumb'],
            # summary=data['summary']
        ))

    return oc

@route(constants.PREFIX + '/episodes')
def HandleEpisodes(path, season):
    Log.Debug('Get episodes for %s' % path)

    data = service.parse_page(path)

    # if not data:
    #     return util.no_contents()

    if data['session'] == 'external':
        oc = ObjectContainer(
            title2=u'%s' % data['title'],
            content=ContainerContent.Episodes
        )

        for episode in data['episodes']:
            Log.Debug('Try to get metadata from external: %s' % episode)
            try:
                url = data['episodes'][episode]['url']

                oc.add(MetadataObjectForURL(url))
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

def GetVideoObject(item, episode=0):
    if item['session'] == 'external':
        url = item['url']
    else:
        url = MetaUrl('%s||%s' % (item['path'], episode))
        url.update(item, episode)

    info = InitMetaUrl(url)

    return MetadataObjectForURL(info.item, info.episode)

@route(constants.PREFIX + '/movie')
def HandleMovie(title, item, episode):
    oc = ObjectContainer(title2=unicode(title))

    oc.add(MetadataObjectForURL(json.loads(item), episode))

    return oc

def MetadataObjectForURL(item, episode=None):
    kwargs = {
        'source_title': unicode(L('Title')),
    }

    for k in ['summary', 'thumb', 'directors', 'rating', 'duration', 'originally_available_at']:
        if k in item and item[k]:
            kwargs[k] = item[k]

    if episode and 'episodes' in item:
        if 'roles' in item:
            kwargs['guest_stars'] = item['roles']

        title = item['episodes'][str(episode)]

        rating_key = service.get_episode_url(item['url'], item['current_season'], episode)

        video = builder.build_metadata_object(media_type='episode', rating_key=rating_key, title=title,
            season=int(item['current_season']), index=int(episode), show=item['title'], **kwargs)
    else:
        for k in ['year', 'original_title', 'countries']:
            if k in item and item[k]:
                kwargs[k] = item[k]

        title = item['title']

        video = builder.build_metadata_object(media_type='movie', title=title, rating_key=item['url'], **kwargs)

    video.key = Callback(HandleMovie, title=title, item=json.dumps(item), episode=episode)

    video.items = MediaObjectsForURL(item, episode)

    return video

def MediaObjectsForURL(item, episode=None):
    items = []

    for variant in item['variants'].values():
        if episode and 'episodes' in item and (str(item['current_season']) not in variant['seasons'] or str(episode) not in variant['episodes']):
            continue

        session = None
        url_update = None
        episode = None
        season = None

        if item['url'] == variant['url'] and not episode:
            session = JSON.StringFromObject(variant['session'])
        else:
            url_update = variant['url']

            if episode:
                season = item['current_season']

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

@route(constants.PREFIX + '/getmeta')
def GetMeta(path, episode):
    episode = int(episode)

    item = service.parse_page(path)
    if episode and episode != item['current_episode']:
        item = UpdateItemInfo(item, item['current_season'], episode)

    return JSON.StringFromObject(item)

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

    update = service.get_info_by_url(service.get_episode_url(url, season, episode), HTTP.Headers, url)

    if not update:
        return None

    item['variants'][url].update(update.copy())

    del update['seasons']
    item.update(update)

    service.save_cache(item)

    return item

@route(constants.PREFIX + '/search')
def HandleSearch(query=None, page=1):
    oc = ObjectContainer(title2=unicode(L('Search')))

    response = service.search(query=query)

    for movie in response['movies']:
        Log(movie)
        name = movie['name']
        thumb = movie['thumb']
        path = movie['path']

        key = Callback(HandleMovies, path=path, title=name, name=name, thumb=thumb)

        oc.add(DirectoryObject(key=key, title=unicode(name), thumb=thumb))

    #pagination.append_controls(oc, response, page=page, callback=HandleSearch, query=query)

    return oc

@indirect
@route(constants.PREFIX + '/play')
def Play(session, url, season, episode):
    if not session:
        url_info = service.get_info_by_url(service.get_episode_url(
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

@route(constants.PREFIX + '/play_list.m3u8')
def Playlist(res):
    # Some players does not support gziped response

    return service.get_play_list(res)

@route(constants.PREFIX + '/history')
def History():
    history_object = history.load_history()

    oc = ObjectContainer(title2=u'История')

    if history_object:
        for item in sorted(history_object.values(), key=lambda k: k['time'], reverse=True):
            path = item['path']
            title = item['title']
            thumb = item['thumb']

            oc.add(DirectoryObject(
                key=Callback(HandleMovies, path=path), title=unicode(title), thumb=thumb
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
                key=Callback(HandleMovies, **item),
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