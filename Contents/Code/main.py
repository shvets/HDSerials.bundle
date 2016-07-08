# -*- coding: utf-8 -*-

import copy
from media_info import MediaInfo
import plex_util
import pagination
import history
from flow_builder import FlowBuilder

@route(PREFIX + '/new_series')
def HandleNewSeries():
    oc = ObjectContainer(title2=unicode(L("New Series")))

    new_series = service.get_new_series()

    for item in new_series:
        path = item['path']
        name = item['title']
        text = item['text']

        info = service.get_episode_info(text)

        season = info['season']
        episode = info['episode']

        new_params = {
            'id': path,
            'title': name,
            'name': name,
            'thumb': None
        }
        oc.add(DirectoryObject(
            key=Callback(HandleMovieOrSerie, selected_season=season, selected_episode=episode, **new_params),
            title=name + ", " + str(episode) + " " + unicode(L("episode"))
        ))

    return oc

@route(PREFIX + '/popular')
def HandlePopular(page=1):
    page = int(page)

    oc = ObjectContainer(title2=unicode(L('Popular')))

    response = service.get_popular(page=page)

    for index, item in enumerate(response['items']):
        name = item['title']
        path = item['path']
        thumb = item['thumb']

        new_params = {
            'id': path,
            'title': name,
            'name': name,
            'thumb': thumb
        }
        key = Callback(HandleMovieOrSerie, **new_params)

        oc.add(DirectoryObject(key=key, title=unicode(name), thumb=thumb))

    pagination.append_controls(oc, response, page=int(page), callback=HandlePopular)

    return oc

@route(PREFIX + '/categories')
def HandleCategories():
    oc = ObjectContainer(title2=unicode(L('Categories')))

    items = service.get_categories()

    for item in items:
        name = item['title']
        path = item['path']

        if path == '/Serialy.html':
            oc.add(DirectoryObject(
                key=Callback(HandleSeries, category_path=path, title=name),
                title=plex_util.sanitize(name)
            ))
        else:
            oc.add(DirectoryObject(
                key=Callback(HandleCategory, category_path=path, title=name),
                title=plex_util.sanitize(name)
            ))

    return oc

@route(PREFIX + '/series')
def HandleSeries(category_path, title, page=1):
    oc = ObjectContainer(title2=unicode(title))

    response = service.get_subcategories(category_path, page)

    for item in response['data']:
        name = item['title']
        path = item['path']

        oc.add(DirectoryObject(
            key=Callback(HandleCategoryItems, category_path=path, title=name),
            title=unicode(name),
            thumb=R(ICON)
        ))

    pagination.append_controls(oc, response, page=page, callback=HandleSeries, category_path=category_path, title=title)

    return oc

@route(PREFIX + '/category')
def HandleCategory(category_path, title):
    oc = ObjectContainer(title2=unicode(title))

    # Add all items category
    items = service.get_category_items(category_path)

    if len(items) > 0:
        all_title = unicode(L('All')) + ' ' + unicode(title.lower())

        oc.add(DirectoryObject(
            key=Callback(HandleCategoryItems, category_path=category_path, title=all_title),
            title=plex_util.sanitize(all_title)
        ))

    cats = service.get_subcategories(category_path)

    for item in cats['data']:
        name = item['title']
        path = item['path']

        oc.add(DirectoryObject(
            key=Callback(HandleCategoryItems, category_path=path, title=name),
            title=plex_util.sanitize(name)
        ))

    return oc

@route(PREFIX + '/category_items')
def HandleCategoryItems(category_path, title, page=1):
    response = service.get_category_items(category_path, page)

    if len(response['items']) == 1:
        item = response['items'][0]

        name = item['title']
        path = item['path']
        thumb = service.get_thumb(item['thumb'])

        new_params = {
            'id': path,
            'title': name,
            'name': name,
            'thumb': thumb
        }
        return HandleMovieOrSerie(**new_params)
    else:
        oc = ObjectContainer(title2=unicode(title))

        if response['items']:
            for item in response['items']:
                name = item['title']
                path = item['path']
                thumb = service.get_thumb(item['thumb'])

                new_params = {
                    'id': path,
                    'title': name,
                    'name': name,
                    'thumb': thumb
                }

                oc.add(DirectoryObject(
                    key=Callback(HandleMovieOrSerie, **new_params),
                    title=plex_util.sanitize(name),
                    thumb=thumb
                ))

            pagination.append_controls(oc, response, page=page, callback=HandleCategoryItems, title=title,
                                       category_path=category_path)

        return oc

@route(PREFIX + '/movie_or_serie')
def HandleMovieOrSerie(selected_season=None, selected_episode=None, **params):
    if service.is_serial(params['id']):
        params['type'] = 'serie'
        return HandleSerie(selected_season=selected_season, selected_episode=selected_episode, **params)
    else:
        params['type'] = 'movie'
        return HandleMovie(**params)

@route(PREFIX + '/serie')
def HandleSerie(operation=None, selected_season=None, selected_episode=None, **params):
    movie_documents = service.get_movie_documents(params['id'])

    if len(movie_documents) == 1:
        return HandleSerieVersion(version=1, operation=operation, selected_season=selected_season,
                                  selected_episode=selected_episode, **params)
    else:
        oc = ObjectContainer(title2=unicode(params['title']))

        if 'version' in params:
            version = int(params['version'])

            new_params = copy.copy(params)
            new_params['version'] = version

            return HandleSerieVersion(operation=operation, selected_season=selected_season,
                                      selected_episode=selected_episode, **new_params)
        else:
            for index in range(0, len(movie_documents)):
                version = index + 1

                new_params = copy.copy(params)
                new_params['version'] = version

                oc.add(DirectoryObject(
                    key=Callback(HandleSerieVersion, operation=operation, selected_season=selected_season,
                                      selected_episode=selected_episode, **new_params),
                    title=unicode(movie_documents[index]['release']),
                ))

        return oc

@route(PREFIX + '/serie_version', version=int)
def HandleSerieVersion(version, operation=None, selected_season=None, selected_episode=None, **params):
    oc = ObjectContainer(title2=unicode(params['title']))

    media_info = MediaInfo(**params)
    media_info['version'] = version

    service.queue.handle_bookmark_operation(operation, media_info)

    movie_documents = service.get_movie_documents(params['id'])

    movie_document = movie_documents[version-1]['movie_document']

    if selected_season:
        addSelectedSeason(oc, movie_document, selected_season, selected_episode, **params)

    serial_info = service.get_serial_info(movie_document)

    for season in sorted(serial_info['seasons'].keys()):
        if not selected_season or selected_season and selected_season != int(season):
            season_name = serial_info['seasons'][season]
            rating_key = service.get_episode_url(params['id'], season, 0)
            # source_title = unicode(L('Title'))

            new_params = {
                'type': 'season',
                'id': params['id'],
                'serieName': params['name'],
                'name': season_name,
                'thumb': params['thumb'],
                'season': season,
                'version': version
            }

            oc.add(SeasonObject(
                key=Callback(HandleSeason, **new_params),
                title=unicode(season_name),
                rating_key=rating_key,
                index=int(season),
                thumb=params['thumb'],
                # source_title=source_title,
                # summary=data['summary']
            ))

    service.queue.append_bookmark_controls(oc, HandleSerieVersion, media_info)

    return oc

def addSelectedSeason(oc, document, selected_season, selected_episode, **params):
    selected_season = int(selected_season)

    serial_info = service.get_serial_info(document)

    if selected_episode:
        selected_episode = int(selected_episode)

        if len(serial_info['episodes']) >= selected_episode:
            episode_name = serial_info['episodes'][selected_episode]

            new_params = {
                'type': 'episode',
                'id': params['id'],
                'serieName': params['name'],
                'name': episode_name,
                'thumb': params['thumb'],
                'episodeNumber': selected_episode

            }
            oc.add(DirectoryObject(
                key=Callback(HandleMovie, **new_params),
                title=plex_util.sanitize(episode_name)
            ))

    season_name = serial_info['seasons'][selected_season]
    rating_key = service.get_episode_url(params['id'], selected_season, 0)

    new_params = {
        'type': 'season',
        'id': params['id'],
        'title': season_name,
        'name': params['name'],
        'thumb': params['thumb'],
        'season': selected_season
    }

    oc.add(SeasonObject(
        key=Callback(HandleSeason, **new_params),
        title=unicode(season_name),
        rating_key=rating_key,
        index=selected_season,
        thumb=params['thumb'],
    ))

@route(PREFIX + '/season', container=bool)
def HandleSeason(operation=None, container=False, **params):
    movie_documents = service.get_movie_documents(params['id'], params['season'], 1)

    if len(movie_documents) == 1:
        return HandleSeasonVersion(version=1, operation=operation, container=container, **params)
    elif 'version' in params:
        new_params = copy.copy(params)
        del new_params['version']

        return HandleSeasonVersion(version=params['version'], operation=operation, container=container, **new_params)
    else:
        oc = ObjectContainer(title2=unicode(params['name']))

        for index in range(0, len(movie_documents)):
            version = index + 1

            oc.add(DirectoryObject(
                key=Callback(HandleSeasonVersion, version=version, operation=operation, container=container, **params),
                title=unicode(movie_documents[index]['release']),
            ))

        return oc

@route(PREFIX + '/season_version', container=bool)
def HandleSeasonVersion(version, operation=None, container=False, **params):
    version = int(version)

    if 'thumb' in params:
        thumb = params['thumb']
    else:
        thumb = None

    oc = ObjectContainer(title2=unicode(params['name']))

    media_info = MediaInfo(**params)

    service.queue.handle_bookmark_operation(operation, media_info)

    movie_documents = service.get_movie_documents(params['id'], params['season'], 1)
    movie_document = movie_documents[version-1]['movie_document']
    serial_info = service.get_serial_info(movie_document)

    for index, episode in enumerate(sorted(serial_info['episodes'].keys())):
        episode_name = serial_info['episodes'][episode]

        new_params = {
            'type': 'episode',
            'id': params['id'],
            'serieName': params['serieName'],
            'name': episode_name,
            'thumb': thumb,
            'season': params['season'],
            'episode':  episode,
            'episodeNumber': index + 1
        }
        key = Callback(HandleMovie, container=container, **new_params)

        oc.add(DirectoryObject(key=key, title=unicode(episode_name)))

    service.queue.append_bookmark_controls(oc, HandleSeasonVersion, media_info)

    return oc

@route(PREFIX + '/movie', container=bool)
def HandleMovie(operation=None, container=False, **params):
    # urls = service.load_cache(path)
    #
    # if not urls:
    #     urls = service.retrieve_urls(path, season=season, episode=episode)
    #
    # service.save_cache(urls)

    if 'season' in params:
        season = params['season']
    else:
        season = None

    if 'episode' in params:
        episode = params['episode']
    else:
        episode = None

    urls = service.retrieve_urls(params['id'], season=season, episode=episode)

    if not urls:
        return plex_util.no_contents()
    else:
        oc = ObjectContainer(title2=unicode(params['name']))

        media_info = MediaInfo(**params)

        service.queue.handle_bookmark_operation(operation, media_info)

        document = service.fetch_document(params['id'])
        data = service.get_media_data(document)

        if episode:
            media_info['type'] = 'episode'
            media_info['index'] = int(episode)
            media_info['season'] = int(season)
            media_info['content_rating'] = data['rating']
            # show=show,
        else:
            media_info['type'] = 'movie'
            media_info['year'] = data['year']
            media_info['genres'] = data['genres']
            media_info['countries'] = data['countries']
            media_info['genres'] = data['genres']
            # video.tagline = 'tagline'
            # video.original_title = 'original_title'

        url_items = []

        for url in urls:
            url_items.append(
                {
                    "url": url['url'],
                    "config": {
                        # "container": audio_container,
                        # "audio_codec": audio_codec,
                        "video_resolution": url['height'],
                        "width": url['width'],
                        "height": url['height'],
                        "bitrate": url['bandwidth'],
                        # "duration": duration
                    }
                })

        media_info['rating_key'] = service.get_episode_url(params['id'], season, 0)
        media_info['rating'] = data['rating']
        media_info['tags'] = data['tags']
        media_info['summary'] = data['summary']
        media_info['thumb'] = data['thumb']
        # media_info['art'] = data['thumb']
        # media_info['season'] = season
        # media_info['episode'] = episode

        oc.add(MetadataObjectForURL(media_info, url_items=url_items, player=PlayVideo))

        if str(container) == 'False':
            history.push_to_history(Data, media_info)
            service.queue.append_bookmark_controls(oc, HandleMovie, media_info)

        return oc

@route(PREFIX + '/search')
def HandleSearch(query=None, page=1):
    oc = ObjectContainer(title2=unicode(L('Search')))

    response = service.search(query=query)

    for movie in response['items']:
        name = movie['name']
        thumb = movie['thumb']

        new_params = {
            'id': movie['path'],
            'title': name,
            'name': name,
            'thumb': 'thumb'
        }
        oc.add(DirectoryObject(
            key=Callback(HandleMovieOrSerie, **new_params),
            title=unicode(name),
            thumb=thumb
        ))

    pagination.append_controls(oc, response, page=page, callback=HandleSearch, query=query)

    return oc

@route(PREFIX + '/container')
def HandleContainer(**params):
    type = params['type']

    if type == 'movie':
        return HandleMovie(**params)
    elif type == 'episode':
        return HandleMovie(**params)
    elif type == 'season':
        return HandleSeason(**params)
    elif type == 'serie':
        return HandleSerie(**params)

@route(PREFIX + '/queue')
def HandleQueue():
    oc = ObjectContainer(title2=unicode(L('Queue')))

    service.queue.handle_queue_items(oc, HandleContainer, service.queue.data)

    if len(service.queue.data) > 0:
        oc.add(DirectoryObject(
            key=Callback(ClearQueue),
            title=unicode(L("Clear Queue"))
        ))

    return oc

@route(PREFIX + '/clear_queue')
def ClearQueue():
    service.queue.clear()

    return HandleQueue()

@route(PREFIX + '/history')
def HandleHistory():
    history_object = history.load_history(Data)

    oc = ObjectContainer(title2=unicode(L('History')))

    if history_object:
        data = sorted(history_object.values(), key=lambda k: k['time'], reverse=True)

        service.queue.handle_queue_items(oc, HandleContainer, data)

    return oc

def MetadataObjectForURL(media_info, url_items, player):
    metadata_object = FlowBuilder.build_metadata_object(media_type=media_info['type'], title=media_info['name'])

    metadata_object.key = Callback(HandleMovie, container=True, **media_info)

    #metadata_object.title = title
    metadata_object.rating_key = media_info['rating_key']
    metadata_object.rating = media_info['rating']
    metadata_object.thumb = media_info['thumb']
    metadata_object.art = media_info['thumb']
    metadata_object.tags = media_info['tags']
    metadata_object.summary = media_info['summary']
    # metadata_object.directors = data['directors']

    if 'duration' in media_info:
        metadata_object.duration = int(media_info['duration']) * 1000

    if 'artist' in media_info:
        metadata_object.artist = media_info['artist']

    metadata_object.items.extend(MediaObjectsForURL(url_items, player))

    return metadata_object

def MediaObjectsForURL(url_items, player):
    media_objects = []

    for item in url_items:
        url = item['url']
        config = item['config']

        play_callback = Callback(player, url=url)

        media_object = FlowBuilder.build_media_object(play_callback, config)

        media_objects.append(media_object)

    return media_objects

@indirect
@route(PREFIX + '/play_video')
def PlayVideo(url, live=True, play_list=True):
    if not url:
        return plex_util.no_contents()
    else:
        if str(play_list) == 'True':
            url = Callback(PlayList, url=url)

        if live:
            key = HTTPLiveStreamURL(url)
        else:
            key = RTMPVideoURL(url)

        return IndirectResponse(MovieObject, key)

@route(PREFIX + '/play_list.m3u8')
def PlayList(url):
    return service.get_play_list(url)
