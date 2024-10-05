import json
import os
import time

class JSONCache:
    def __init__(self, cache_file, ttl=3600):
        self.cache_file = cache_file
        self.ttl = ttl  # Time to live in seconds

    def _is_cache_valid(self):
        """Check if the cache is still valid based on TTL."""
        if not os.path.exists(self.cache_file):
            return False
        file_mod_time = os.path.getmtime(self.cache_file)
        return (time.time() - file_mod_time) < self.ttl

    def _load_cache(self):
        """Load data from the cache file."""
        with open(self.cache_file, 'r') as file:
            return json.load(file)

    def _save_cache(self, data):
        """Save data to the cache file."""
        with open(self.cache_file, 'w') as file:
            json.dump(data, file)

    def get(self):
        """Get data from the cache if valid, otherwise return None."""
        if self._is_cache_valid():
            return self._load_cache()
        return None

    def set(self, data):
        """Set data to the cache."""
        self._save_cache(data)

    def clear(self):
        """Clear the cache by deleting the cache file."""
        if os.path.exists(self.cache_file):
            os.remove(self.cache_file)
