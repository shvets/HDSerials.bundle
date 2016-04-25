# -*- coding: utf-8 -*-

import constants
import util
import pagination
import history
from flow_builder import FlowBuilder

builder = FlowBuilder()

@route(constants.PREFIX + '/new_series')
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

        oc.add(DirectoryObject(
            key=Callback(HandleContainer, path=path, title=name, name=name,
                         selected_season=season, selected_episode=episode),
            title=name + ", " + str(episode) + " " + unicode(L("episode"))
        ))

    return oc

@route(constants.PREFIX + '/popular')
def HandlePopular(page=1):
    page = int(page)

    oc = ObjectContainer(title2=unicode(L('Popular')))

    response = service.get_popular(page=page)

    for index, item in enumerate(response['movies']):
        name = item['title']
        path = item['path']
        thumb = item['thumb']

        key = Callback(HandleContainer, path=path, title=name, name=name, thumb=thumb)

        oc.add(DirectoryObject(key=key, title=unicode(name), thumb=thumb))

    pagination.append_controls(oc, response, page=int(page), callback=HandlePopular)

    return oc

@route(constants.PREFIX + '/categories')
def HandleCategories():
    oc = ObjectContainer(title2=unicode(L('Categories')))

    items = service.get_categories()

    for item in items:
        name = item['title']
        path = item['path']

        if path == '/Serialy.html':
            oc.add(DirectoryObject(
                key=Callback(HandleSerials, category_path=path, title=name),
                title=util.sanitize(name)
            ))
        else:
            oc.add(DirectoryObject(
                key=Callback(HandleCategory, category_path=path, title=name),
                title=util.sanitize(name)
            ))

    return oc

@route(constants.PREFIX + '/serials')
def HandleSerials(category_path, title, page=1):
    oc = ObjectContainer(title2=unicode(title))

    response = service.get_subcategories(category_path, page)

    for item in response['data']:
        name = item['title']
        path = item['path']

        #thumb = service.URL + service.fetch_document(service.URL + path).xpath('//div[@class="catItemImageBlock"]//span/a/img')[0].get('src')

        oc.add(DirectoryObject(
            key=Callback(HandleCategoryItems, category_path=path, title=name),
            title=unicode(name),
            thumb=R(constants.ICON)
        ))

    pagination.append_controls(oc, response, page=page, callback=HandleSerials, category_path=category_path, title=title)

    return oc

@route(constants.PREFIX + '/category')
def HandleCategory(category_path, title):
    oc = ObjectContainer(title2=unicode(title))

    # Add all items category
    items = service.get_category_items(category_path)

    if len(items) > 0:
        all_title = unicode(L('All')) + ' ' + unicode(title.lower())

        oc.add(DirectoryObject(
            key=Callback(HandleCategoryItems, category_path=category_path, title=all_title),
            title=util.sanitize(all_title)
        ))

    cats = service.get_subcategories(category_path)

    for item in cats['data']:
        name = item['title']
        path = item['path']

        oc.add(DirectoryObject(
            key=Callback(HandleCategoryItems, category_path=path, title=name),
            title=util.sanitize(name)
        ))

    return oc

@route(constants.PREFIX + '/category_items')
def HandleCategoryItems(category_path, title, page=1):
    response = service.get_category_items(category_path, page)

    if len(response['movies']) == 1:
        item = response['movies'][0]

        name = item['title']
        path = item['path']
        thumb = service.get_thumb(item['thumb'])

        return HandleContainer(path=path, title=name, name=name, thumb=thumb)
    else:
        oc = ObjectContainer(title2=unicode(title))

        if response['movies']:
            for item in response['movies']:
                name = item['title']
                path = item['path']
                thumb = service.get_thumb(item['thumb'])

                oc.add(DirectoryObject(
                    key=Callback(HandleContainer, path=path, title=name, name=name, thumb=thumb),
                    title=util.sanitize(name),
                    thumb=thumb
                ))

            pagination.append_controls(oc, response, page=page, callback=HandleCategoryItems, title=title,
                                       category_path=category_path)

        return oc

@route(constants.PREFIX + '/container')
def HandleContainer(path, title, name, thumb=None, selected_season=None, selected_episode=None, **params):
    if service.is_serial(path):
        return HandleSeasons(path=path, title=title, name=name, thumb=thumb,
                             selected_season=selected_season, selected_episode=selected_episode)
    else:
        return HandleMovie(path=path, title=title, name=name, thumb=thumb)

@route(constants.PREFIX + '/seasons')
def HandleSeasons(path, title, name, thumb, operation=None, selected_season=None, selected_episode=None):
    oc = ObjectContainer(title2=unicode(title))

    if operation == 'add':
        service.queue.add_bookmark(path=path, title=title, name=name, thumb=thumb)
    elif operation == 'remove':
        service.queue.remove_bookmark(path=path, title=title, name=name, thumb=thumb)

    document = service.get_movie_document(path)

    if selected_season:
        selected_season = int(selected_season)

        serial_info = service.get_serial_info(document)

        if selected_episode:
            selected_episode = int(selected_episode)

            if len(serial_info['episodes']) >= selected_episode:
                episode_name = serial_info['episodes'][selected_episode]

                oc.add(DirectoryObject(
                    key=Callback(HandleMovie, path=path, title=episode_name, name=name, thumb=thumb),
                    title=util.sanitize(episode_name)
                ))

        season_name = serial_info['seasons'][selected_season]
        rating_key = service.get_episode_url(path, selected_season, 0)

        oc.add(SeasonObject(
            key=Callback(HandleEpisodes, path=path, title=season_name, name=name, thumb=thumb, season=selected_season),
            title=unicode(season_name),
            rating_key=rating_key,
            index=selected_season,
            thumb=thumb,
        ))

    serial_info = service.get_serial_info(document)

    for season in sorted(serial_info['seasons'].keys()):
        if not selected_season or selected_season and selected_season != int(season):
            season_name = serial_info['seasons'][season]
            rating_key = service.get_episode_url(path, season, 0)
            # source_title = unicode(L('Title'))

            oc.add(SeasonObject(
                key=Callback(HandleEpisodes, path=path, title=season_name, name=name, thumb=thumb, season=season),
                title=unicode(season_name),
                rating_key=rating_key,
                index=int(season),
                thumb=thumb,
                # source_title=source_title,
                # summary=data['summary']
            ))

    service.queue.append_controls(oc, HandleSeasons, path=path, title=title, name=name, thumb=thumb)

    return oc

@route(constants.PREFIX + '/episodes', container=bool)
def HandleEpisodes(path, title, name, thumb, season, operation=None, container=False):
    oc = ObjectContainer(title2=unicode(title))

    if operation == 'add':
        service.queue.add_bookmark(path=path, title=title, name=name, thumb=thumb, season=season)
    elif operation == 'remove':
        service.queue.remove_bookmark(path=path, title=title, name=name, thumb=thumb, season=season)

    document = service.get_movie_document(path, season, 1)
    serial_info = service.get_serial_info(document)

    for episode in sorted(serial_info['episodes'].keys()):
        episode_name = serial_info['episodes'][episode]

        key = Callback(HandleMovie, path=path, title=episode_name, name=name,
                       thumb=thumb, season=season, episode=episode, container=container)

        oc.add(DirectoryObject(key=key, title=unicode(episode_name)))

    service.queue.append_controls(oc, HandleEpisodes, path=path, title=title, name=name, thumb=thumb, season=season)

    return oc

@route(constants.PREFIX + '/movie', container=bool)
def HandleMovie(path, title, name, thumb, season=None, episode=None, operation=None, container=False):
    # urls = service.load_cache(path)
    #
    # if not urls:
    #     urls = service.retrieve_urls(path, season=season, episode=episode)
    #
    # service.save_cache(urls)

    urls = service.retrieve_urls(path, season=season, episode=episode)

    if not urls:
        return util.no_contents()
    else:
        oc = ObjectContainer(title2=unicode(name))

        if operation == 'add':
            service.queue.add_bookmark(path=path, title=title, name=name, thumb=thumb, season=season, episode=episode)
        elif operation == 'remove':
            service.queue.remove_bookmark(path=path, title=title, name=name, thumb=thumb, season=season, episode=episode)

        oc.add(MetadataObjectForURL(path=path, title=title, name=name, thumb=thumb,
                                    season=season, episode=episode, urls=urls))

        if str(container) == 'False':
            history.push_to_history(path=path, title=title, name=name, thumb=thumb, season=season, episode=episode)
            service.queue.append_controls(oc, HandleMovie, path=path, title=title, name=name, thumb=thumb, season=season, episode=episode)

        return oc

@route(constants.PREFIX + '/search')
def HandleSearch(query=None, page=1):
    oc = ObjectContainer(title2=unicode(L('Search')))

    response = service.search(query=query)

    for movie in response['movies']:
        name = movie['name']
        thumb = movie['thumb']
        path = movie['path']

        oc.add(DirectoryObject(
            key=Callback(HandleContainer, path=path, title=name, name=name, thumb=thumb),
            title=unicode(name),
            thumb=thumb
        ))

    pagination.append_controls(oc, response, page=page, callback=HandleSearch, query=query)

    return oc

@route(constants.PREFIX + '/history')
def HandleHistory():
    history_object = history.load_history()

    oc = ObjectContainer(title2=unicode(L('History')))

    if history_object:
        for item in sorted(history_object.values(), key=lambda k: k['time'], reverse=True):
            path = item['path']
            name = item['title']

            if item['thumb']:
                thumb = service.get_thumb(item['thumb'])
            else:
                thumb = None

            oc.add(DirectoryObject(
                key=Callback(HandleContainer, path=path, title=name, name=name, thumb=thumb),
                title=unicode(name),
                thumb=thumb
            ))

    return oc

@route(constants.PREFIX + '/queue')
def HandleQueue():
    oc = ObjectContainer(title2=unicode(L('Queue')))

    for item in service.queue.data:
        if 'episode' in item:
            oc.add(DirectoryObject(
                key=Callback(HandleMovie, **item),
                title=util.sanitize(item['name']),
                thumb=item['thumb']
            ))
        elif 'season' in item:
            oc.add(DirectoryObject(
                key=Callback(HandleEpisodes, **item),
                title=util.sanitize(item['name']),
                thumb=item['thumb']
            ))
        else:
            oc.add(DirectoryObject(
                key=Callback(HandleContainer, **item),
                title=util.sanitize(item['name']),
                thumb=item['thumb']
            ))

    return oc

def MetadataObjectForURL(path, title, name, thumb, season, episode, urls):
    params = {}

    document = service.fetch_document(path)
    data = service.get_media_data(document)

    if episode:
        media_type = 'episode'
        params['index'] = int(episode)
        params['season'] = int(season)
        params['content_rating'] = data['rating']
        # show=show,
    else:
        media_type = 'movie'
        params['year'] = data['year']
        params['genres'] = data['genres']
        params['countries'] = data['countries']
        params['genres'] = data['genres']
        # video.tagline = 'tagline'
        # video.original_title = 'original_title'

    video = builder.build_metadata_object(media_type=media_type, **params)

    video.title = title
    video.rating_key = service.get_episode_url(path, season, 0)
    video.rating = data['rating']
    video.thumb = data['thumb']
    video.art = data['thumb']
    video.tags = data['tags']
    video.duration = data['duration'] * 1000
    video.summary = data['summary']
    video.directors = data['directors']

    video.key = Callback(HandleMovie, path=path, title=title, name=name, thumb=thumb,
                         season=season, episode=episode, container=True)

    video.items.extend(MediaObjectsForURL(urls))

    return video

def MediaObjectsForURL(urls):
    items = []

    for item in urls:
        url = item['url']

        play_callback = Callback(PlayVideo, url=url)

        media_object = builder.build_media_object(play_callback, video_resolution=item['height'],
                                                  width=item['width'], height=item['height'])

        items.append(media_object)

    return items

@indirect
@route(constants.PREFIX + '/play_video')
def PlayVideo(url, play_list=True):
    if not url:
        return util.no_contents()
    else:
        if str(play_list) == 'True':
            url = Callback(PlayList, url=url)

        return IndirectResponse(MovieObject, key=HTTPLiveStreamURL(url))

@route(constants.PREFIX + '/play_list.m3u8')
def PlayList(url):
    return service.get_play_list(url)
