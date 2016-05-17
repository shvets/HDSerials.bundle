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