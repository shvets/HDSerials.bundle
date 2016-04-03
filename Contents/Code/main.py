import common

# import common as Common
from urllib import urlencode

@route(common.PREFIX + '/search')
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
                key = '%s?%s' % (common.PREFIX + '/info', urlencode({'path': item['link']}))

                oc.add(TVShowObject(title=title, key=key, rating_key=rating_key,
                                       thumb='%s%s' % (service.URL, item['image']),
                                       summary=HTML.ElementFromString(item['introtext']).text_content()))
            else:
                title = u'%s / %s' % (item['category']['name'], item['title'])
                # key = URLService.LookupURLForMediaURL(service.URL + item['link'])

                key = HandleMovies(service.URL + item['link'])

                oc.add(MovieObject(title=title, key=key, rating_key=rating_key,
                                       thumb='%s%s' % (service.URL, item['image']),
                                       summary=HTML.ElementFromString(item['introtext']).text_content()))
    return oc

@route(common.PREFIX + '/movies')
def HandleMovies(url):
    return URLService.LookupURLForMediaURL(url)


@route(common.PREFIX + '/queue')
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