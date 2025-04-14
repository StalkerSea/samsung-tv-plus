import os
from tempfile import gettempdir

# Core settings
REGION_ALL = 'all'
PLAYLIST_PATH = os.getenv('PLAYLIST_PATH', 'playlist.m3u8')
EPG_PATH = os.getenv('EPG_PATH', 'epg.xml')
CLEAR_CACHE_PATH = os.getenv('CLEAR_CACHE_PATH', 'clear_cache')
STATUS_PATH = os.getenv('STATUS_PATH', '')
CACHE_DIR = os.path.join(gettempdir(), 'samsung-tv-plus')

# API endpoints
APP_URL = os.getenv('APP_URL', 'https://i.mjh.nz/SamsungTVPlus/.channels.json.gz')
EPG_URL = os.getenv('EPG_URL', 'https://i.mjh.nz/SamsungTVPlus/{region}.xml.gz')
PLAYBACK_URL = os.getenv('PLAYBACK_URL', 'https://jmp2.uk/sam-{id}.m3u8')

# Performance settings
DELIMITER = os.getenv('DELIMITER', '|')
TIMEOUT = (
    int(os.getenv('CONNECT_TIMEOUT', 5)),
    int(os.getenv('READ_TIMEOUT', 20))
)
CACHE_TIME = int(os.getenv('CACHE_TIME', 300))  # default of 5mins
CHUNKSIZE = int(os.getenv('CHUNKSIZE', 1024))
MAX_CHANNELS = int(os.getenv('MAX_CHANNELS', 0))  # 0 means no limit
MAX_EPG_SIZE = int(os.getenv('MAX_EPG_SIZE', 0))  # 0 means no limit