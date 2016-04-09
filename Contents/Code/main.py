# -*- coding: utf-8 -*-

import constants
import util
import pagination
from lxml.etree import tostring
from flow_builder import FlowBuilder

builder = FlowBuilder()

@route(constants.PREFIX + '/new_series')
def HandleNewSeries():
    oc = ObjectContainer(title2=unicode(L("New Series")))

    new_series = service.get_new_series()

    for item in new_series:
        path = item['path']
        title = item['title']
        text = item['text']

        info = service.get_episode_info(text)

        season = info['season']
        episode = info['episode']

        oc.add(DirectoryObject(
            key=Callback(HandleContainer, path=path, title=title, name=title, season=season, episode=episode),
            title=title + ", " + str(episode) + " " + unicode(L("episode"))
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

        oc.add(DirectoryObject(
            key=Callback(HandleContainer, path=path, title=title, name=title, thumb=thumb),
            title=unicode(title),
            thumb=thumb
        ))

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
            key=Callback(HandleCategory, category_path=path, title=title),
            title=unicode(title)
        ))

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
            title=unicode(all_title)
        ))

    cats = service.get_subcategories(category_path)

    for item in cats:
        title = item['title']
        path = item['path']

        oc.add(DirectoryObject(
            key=Callback(HandleCategoryItems, category_path=path, title=title),
            title=unicode(title)
        ))

    return oc

@route(constants.PREFIX + '/category_items')
def HandleCategoryItems(category_path, title, page=1):
    oc = ObjectContainer(title2=unicode(title))

    response = service.get_category_items(category_path, page)

    if response['movies']:
        for item in response['movies']:
            title = item['title']
            path = item['path']
            thumb = service.get_thumb(item['thumb'])

            oc.add(DirectoryObject(
                key=Callback(HandleContainer, path=path, title=title, name=title, thumb=thumb),
                title=unicode(title),
                thumb=thumb
            ))

        pagination.append_controls(oc, response, page=page, callback=HandleCategoryItems, title=title, category_path=category_path)

    return oc

@route(constants.PREFIX + '/container')
def HandleContainer(path, title, name, thumb=None, season=None, episode=None, **kwargs):
    if path.find(service.URL) < 0:
        path = service.URL + path

    document = service.get_movie_document(path)

    content = tostring(document.xpath('body')[0])

    data = service.get_session_data(content)

    if data and data['content_type'] == 'serial':
        oc = ObjectContainer(title2=unicode(title))

        if season:
            serial_info = service.get_serial_info(document)

            if episode:
                episode_name = serial_info['episodes'][episode]

                oc.add(DirectoryObject(
                    key=Callback(HandleMovie, path=path, title=episode_name, name=episode_name, thumb=thumb),
                    title=unicode(episode_name)
                ))

            season_name = serial_info['seasons'][season]

            oc.add(DirectoryObject(
                key=Callback(HandleEpisodes, path=path, title=season_name, name=season_name,
                             thumb=thumb, season=season),
                title=unicode(season_name)
            ))

        serial_info = service.get_serial_info(document)

        for s in sorted(serial_info['seasons'].keys()):
            if s != season:
                season_name = serial_info['seasons'][s]

                oc.add(DirectoryObject(
                    key=Callback(HandleEpisodes, path=path, title=name, name=season_name, thumb=thumb, season=s),
                    title=unicode(season_name)
                ))


        # service.queue.append_queue_controls(oc,
        #                                     {
        #                                         "path": path,
        #                                         "title": title,
        #                                         "name": title,
        #                                         "thumb": thumb
        #                                     },
        #                                     add_bookmark_handler=HandleAddBookmark,
        #                                     remove_bookmark_handler=HandleRemoveBookmark
        #                                     )

        return oc

    else:
        return HandleMovie(path=path, title=title, name=name, thumb=thumb)

# @route(constants.PREFIX + '/seasons')
# def HandleSeasons(path):
#     data = service.parse_page(path)
#
#     if not data:
#         return util.no_contents()
#
#     if len(data['seasons']) == 1:
#         return HandleEpisodes(path, data['current_season'])
#
#     oc = ObjectContainer(
#         title2=data['title'],
#         content=ContainerContent.Seasons,
#     )
#
#     seasons = data['seasons'].keys()
#
#     seasons.sort(key=lambda k: int(k))
#
#     for season in seasons:
#         title = data['seasons'][season]
#         source_title = unicode(L('Title'))
#         rating_key = service.get_episode_url(data['url'], season, 0)
#         thumb = service.get_thumb(data['thumb'])
#
#         oc.add(SeasonObject(
#             key=Callback(HandleEpisodes, path=path, season=season),
#             rating_key=rating_key,
#             index=int(season),
#             title=unicode(title),
#             source_title=source_title,
#             thumb=thumb,
#             # summary=data['summary']
#         ))
#
#     return oc

@route(constants.PREFIX + '/episodes')
def HandleEpisodes(path, title, name, thumb, season, container=False):
    data = service.parse_page(path)

    if not data:
        return util.no_contents()

    oc = ObjectContainer(
        title2=unicode(data['title'] + " / " + data['seasons'][season]),
        content=ContainerContent.Episodes
    )

    episodes = data['episodes'].keys()
    episodes.sort(key=lambda k: int(k))

    thumb = service.get_thumb(data['thumb'])

    for episode in episodes:
        title = data['episodes'][episode]

        oc.add(DirectoryObject(
            key=Callback(HandleMovie, path=path, title=title, name=title, thumb=thumb, season=season, episode=episode),
            title=unicode(title),
            thumb=thumb
        ))

    return oc

@route(constants.PREFIX + '/movie', container=bool)
def HandleMovie(path, title, name, thumb=None, season=None, episode=None, container=False, **params):
    if path.find(service.URL) < 0:
        path = service.URL + path

    urls = service.retrieve_urls(path, season=season, episode=episode)


    if not urls:
        return util.no_contents()
    else:
        media_info = {
            "path": path,
            "title": title,
            "name": name,
            "thumb": thumb,
            "season": season,
            "episode": episode
        }

        oc = ObjectContainer(title2=unicode(name))

        oc.add(
            MetadataObjectForURL(path=path, title=title, name=name, thumb=thumb, season=season, episode=episode,
                                 urls=urls))

        # if str(container) == 'False':
        #     history.push_to_history(media_info)
        #     service.queue.append_queue_controls(oc, media_info,
        #                                         add_bookmark_handler=HandleAddBookmark,
        #                                         remove_bookmark_handler=HandleRemoveBookmark
        #                                          )

        return oc

def MetadataObjectForURL(path, title, name, thumb, season, episode, urls):
    video = MovieObject(title=title)

    if path.find(service.URL) < 0:
        path = service.URL + path

    document = service.fetch_document(path)

    data = service.get_media_data(document)

    # info = service.parse_page(path)
    # Log(info)

    video.rating_key = 'rating_key'
    video.rating = data['rating']
    video.thumb = service.get_thumb(data['thumb'])
    # video.year = data['year']
    # video.tags = data['tags']
    # video.duration = data['duration'] * 60 * 1000
    # video.summary = data['description']
    # video.originally_available_at = originally_available_at(on_air)

    video.key = Callback(HandleMovie, path=path, title=title, name=name, thumb=thumb,
                         season=season, episode=episode, container=True)

    video.items.extend(MediaObjectsForURL(urls))

    return video

def MediaObjectsForURL(urls):
    items = []

    for item in urls:
        url = item['url']

        play_callback = Callback(PlayVideo, url=url)

        media_object = builder.build_media_object(play_callback, video_resolution=item['width'])

        items.append(media_object)

    return items

@route(constants.PREFIX + '/search')
def HandleSearch(query=None, page=1):
    oc = ObjectContainer(title2=unicode(L('Search')))

    response = service.search(query=query)

    for movie in response['movies']:
        name = movie['name']
        thumb = service.get_thumb(movie['thumb'])
        path = movie['path']

        oc.add(DirectoryObject(
            key=Callback(HandleContainer, path=path, title=name, name=name, thumb=thumb),
            title=unicode(name),
            thumb=thumb
        ))

    pagination.append_controls(oc, response, page=page, callback=HandleSearch, query=query)

    return oc

@indirect
@route(constants.PREFIX + '/play_video')
def PlayVideo(url):
    if not url:
        return util.no_contents()
    else:
        play_list = Callback(PlayList, url=url)

        return IndirectResponse(MovieObject, key=HTTPLiveStreamURL(play_list))

@route(constants.PREFIX + '/play_list.m3u8')
def PlayList(url):
    return service.get_play_list(url)

@route(constants.PREFIX + '/history')
def History():
    history_object = history.load_history()

    oc = ObjectContainer(title2=u'История')

    if history_object:
        for item in sorted(history_object.values(), key=lambda k: k['time'], reverse=True):
            path = item['path']
            title = item['title']
            thumb = service.get_thumb(item['thumb'])

            oc.add(DirectoryObject(
                key=Callback(HandleContainer, path=path, title=title, name=title, thumb=thumb),
                title=unicode(title),
                thumb=thumb
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
