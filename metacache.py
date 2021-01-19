import logging
import os
import pickle

from appdirs import user_cache_dir
from meta import FileMeta

log = logging.getLogger(__name__)


class MetaCache:
    def __init__(self):
        self.meta_cache = {}

    def get(self, path, getter):
        if path in self.meta_cache:
            return self.meta_cache[path]
        else:
            value = getter(path)
            self.meta_cache[path] = value
            return value

    def _get_path(self, ensure_path_exists):
        cache_dir = user_cache_dir('catvid', 'bad-bit')
        cache_file = os.path.join(cache_dir, 'cache.p')
        if ensure_path_exists:
            os.makedirs(cache_dir, exist_ok=True)
        return cache_file

    def load(self):
        log.info("Loading cache file (use --no-cache to disable)")
        try:
            with open(self._get_path(ensure_path_exists=False), 'rb') as c:
                self._unpickledict(pickle.load(c))
                log.info('Loaded cache file')
        except FileNotFoundError:
            log.warning("Cache file does not exist, starting fresh")
        except Exception as e:
            log.error("Could not load cache", e)
            raise e

    def save(self):
        log.info("Saving cache file (use --no-cache to disable)")
        try:
            with open(self._get_path(ensure_path_exists=True), 'wb') as c:
                pickle.dump(self._pickledict(), c)
                log.info('Saved cache file')
        except Exception as e:
            log.error("Could not save cache", e)
            raise e

    def _unpickledict(self, pickled):
        self.meta_cache = {}
        for k, v in pickled["file_meta"].items():
            self.meta_cache[k] = FileMeta(v)

    def _pickledict(self):
        return {
            "file_meta": {k: v.to_dict() for k, v in self.meta_cache.items()}
        }
