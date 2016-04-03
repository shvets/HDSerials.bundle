from hdserials_service import HDSerialsService
from plex_storage import PlexStorage

class PlexService(HDSerialsService):
    def __init__(self):
        storage_name = Core.storage.abs_path(Core.storage.join_path(Core.bundle_path, 'Contents', 'hdserials.storage'))

        self.queue = PlexStorage(storage_name)
