from hdserials_service import HDSerialsService
from plex_storage import PlexStorage

class HDSerialsPlexService(HDSerialsService):
    def __init__(self):
        storage_name = Core.storage.abs_path(Core.storage.join_path(Core.bundle_path, 'Contents', 'hdserials.storage'))

        self.queue = PlexStorage(storage_name)

        self.queue.register_simple_type('movie')
        self.queue.register_simple_type('episode')
        self.queue.register_simple_type('season')
        self.queue.register_simple_type('serie')

    def handle_bookmark_operation(self, operation, media_info):
        if operation == 'add':
            self.queue.add(media_info)
        elif operation == 'remove':
            self.queue.remove(media_info)

    def append_bookmark_controls(self, oc, handler, media_info):
        bookmark = self.queue.find(media_info)

        if bookmark:
            oc.add(DirectoryObject(
                key=Callback(handler, operation='remove', **media_info),
                title=unicode(L('Remove Bookmark')),
                thumb=R(constants.REMOVE_ICON)
            ))
        else:
            oc.add(DirectoryObject(
                key=Callback(handler, operation='add', **media_info),
                title=unicode(L('Add Bookmark')),
                thumb=R(constants.ADD_ICON)
            ))

    # def load_cache(self, path):
    #     if Data.Exists(self.KEY_CACHE):
    #         ret = Data.LoadObject(self.KEY_CACHE)
    #
    #         if ret and 'path' in ret and ret['path'] == path:
    #             Log.Debug('Return from cache %s' % path)
    #
    #             return ret
    #
    # def save_cache(self, data):
    #     Data.SaveObject(self.KEY_CACHE, data)