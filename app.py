#!/usr/bin/python3
import os
import gc
import json
import gzip
import argparse
from config import *
from io import BytesIO
from base64 import b64encode
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qsl, quote, unquote
from http.server import HTTPServer, BaseHTTPRequestHandler

import requests
from cachelib import FileSystemCache

os.makedirs(CACHE_DIR, exist_ok=True)
print(f"Cache dir: {CACHE_DIR}")
cache = FileSystemCache(CACHE_DIR, default_timeout=int(os.getenv("CACHE_TIME", 300)))


class Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self._params = {}
        super().__init__(*args, **kwargs)

    def _error(self, message):
        self.send_response(500)
        self.end_headers()
        self.wfile.write(f'Error: {message}'.encode('utf8'))
        raise

    def do_GET(self):
        # Serve the favicon.ico file
        if self.path == '/favicon.ico':
            self._serve_favicon()
            return

        routes = {
            PLAYLIST_PATH: self._playlist,
            EPG_PATH: self._epg,
            STATUS_PATH: self._status,
            CLEAR_CACHE_PATH: self._clear_cache,
        }

        parsed = urlparse(self.path)
        func = parsed.path.split('/')[1]
        self._params = dict(parse_qsl(parsed.query, keep_blank_values=True))

        if func not in routes:
            self.send_response(404)
            self.end_headers()
            return

        try:
            routes[func]()
        except Exception as e:
            self._error(e)

    def _clear_cache(self):
        cache.clear()
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b'Cache cleared')

    def _serve_favicon(self):
        # Serve the favicon file as an ICO file
        try:
            with open('favicon.ico', 'rb') as f:
                self.send_response(200)
                self.send_header('Content-Type', 'image/x-icon')
                self.end_headers()
                self.wfile.write(f.read())
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()

    def _app_data(self):
        gc.collect()
        cache_path = cache.get(APP_URL)
        if cache_path and os.path.exists(cache_path):
            self.log_message(f"Cache hit: {APP_URL}")
            with open(cache_path, 'r') as f:
                return json.load(f)

        cache_path = os.path.join(CACHE_DIR, b64encode(APP_URL.encode()).decode())
        self.log_message(f"Downloading {APP_URL}...")
        resp = requests.get(APP_URL, stream=True, timeout=TIMEOUT)
        resp.raise_for_status()
        json_text = gzip.GzipFile(fileobj=BytesIO(resp.content)).read()
        data = json.loads(json_text)['regions']
        with open(cache_path, 'w') as f:
            json.dump(data, f)
        cache.set(APP_URL, cache_path, timeout=CACHE_TIME)
        return data

    def _playlist(self):
        all_channels = self._app_data()

        # Retrieve filters from URL or fallback to environment variables
        regions = [region.strip().lower() for region in (self._params.get('regions') or os.getenv('REGIONS', REGION_ALL)).split(DELIMITER)]
        regions = [region for region in all_channels.keys() if region.lower() in regions or REGION_ALL in regions]
        groups = [unquote(group).lower() for group in (self._params.get('groups') or os.getenv('GROUPS', '')).split(DELIMITER)]
        groups = [group for group in groups if group]

        start_chno = int(self._params['start_chno']) if 'start_chno' in self._params else None
        sort = self._params.get('sort', 'chno')
        include = [x for x in self._params.get('include', '').split(DELIMITER) if x]
        exclude = [x for x in self._params.get('exclude', '').split(DELIMITER) if x]

        self.send_response(200)
        self.send_header('content-type', 'vnd.apple.mpegurl')
        self.end_headers()

        channels = {}
        self.log_message(f"Including channels from regions: {regions} in groups: {groups}")
        for region in regions:
            channels.update(all_channels[region].get('channels', {}))

        self.wfile.write(b'#EXTM3U\n')
        channel_count = 0
        for key in sorted(channels.keys(), key=lambda x: channels[x]['chno'] if sort == 'chno' else channels[x]['name'].strip().lower()):
            if MAX_CHANNELS > 0 and channel_count >= MAX_CHANNELS:
                break
            
            channel = channels[key]
            logo = channel['logo']
            group = channel['group']
            name = channel['name']
            url = PLAYBACK_URL.format(id=key)
            channel_id = f'samsung-{key}'

            # Skip channels that require a license
            if channel.get('license_url'):
                continue

            # Apply include/exclude filters
            if (include and channel_id not in include) or (exclude and channel_id in exclude):
                continue

            # Apply group filter
            if groups and group.lower() not in groups:
                continue

            chno = ''
            if start_chno is not None:
                if start_chno > 0:
                    chno = f' tvg-chno="{start_chno}"'
                    start_chno += 1
            elif channel.get('chno') is not None:
                chno = ' tvg-chno="{}"'.format(channel['chno'])

            # Write channel information
            self.wfile.write(f'#EXTINF:-1 channel-id="{channel_id}" tvg-id="{key}" tvg-logo="{logo}" group-title="{group}"{chno},{name}\n{url}\n'.encode('utf8'))
            channel_count += 1

    def _epg(self):
        gc.collect()
        regions = (self._params.get('regions') or os.getenv('REGIONS', REGION_ALL)).split(DELIMITER)
        region = regions[0] if len(regions) == 1 else REGION_ALL
        url = EPG_URL.format(region=region)

        cache_path = cache.get(url)
        if cache_path and os.path.exists(cache_path):
            self.log_message(f"Cache hit: {url}...")
            self.send_response(200)
            self.send_header('Content-Type', 'application/xml')
            self.end_headers()
            with open(cache_path, 'rb') as f:
                chunk = f.read(CHUNKSIZE)
                while chunk:
                    self.wfile.write(chunk)
                    chunk = f.read(CHUNKSIZE)
            return

        self.log_message(f"Downloading {url}...")
        cache_path = os.path.join(CACHE_DIR, b64encode(url.encode()).decode())
        try:
            # Download the .gz EPG file
            with open(cache_path, 'wb') as cache_f:
                with requests.get(url, stream=True, timeout=TIMEOUT) as resp:
                    resp.raise_for_status()

                    self.send_response(200)
                    self.send_header('Content-Type', 'application/xml')
                    self.end_headers()

                    # Decompress the .gz content
                    with gzip.GzipFile(fileobj=BytesIO(resp.content)) as gz:
                        chunk = gz.read(CHUNKSIZE)
                        while chunk:
                            cache_f.write(chunk)
                            self.wfile.write(chunk)
                            chunk = gz.read(CHUNKSIZE)
            cache.set(url, cache_path, timeout=CACHE_TIME)
        except MemoryError:
            self.send_response(503)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b"Insufficient memory to process EPG. Try a single region.")
            gc.collect()
        except Exception as e:
            self._error(f"EPG error: {str(e)}")

    def _status(self):
        """Generate a lightweight status page with links to playlists and EPG."""
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        
        host = self.headers.get('Host')
        
        # Start with minimal HTML header
        html_parts = [f'''
            <html>
            <head>
                <title>Samsung TV Plus for Channels</title>
                <link rel="icon" href="/favicon.ico" type="image/x-icon">
                <style>
                    body {{ font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
                    h1, h2, h3 {{ color: #333; }}
                    a {{ color: #0066cc; text-decoration: none; }}
                    a:hover {{ text-decoration: underline; }}
                    .region {{ margin-top: 15px; padding: 10px; border-top: 1px solid #eee; }}
                    .categories {{ margin-top: 25px; border-top: 2px solid #ddd; padding-top: 10px; }}
                    .category-group {{ display: inline-block; margin-right: 20px; margin-bottom: 10px; vertical-align: top; }}
                    .links {{ margin-bottom: 10px; }}
                    ul {{ padding-left: 20px; }}
                    .category-count {{ color: #666; font-size: 0.8em; }}
                </style>
            </head>
            <body>
                <h1>Samsung TV Plus for Channels</h1>
                <div class="links">
                    <h2>All Regions</h2>
                    <p>Playlist: <b><a href="http://{host}/{PLAYLIST_PATH}">http://{host}/{PLAYLIST_PATH}</a></b></p>
                    <p>EPG: <b><a href="http://{host}/{EPG_PATH}">http://{host}/{EPG_PATH}</a></b></p>
                    <p><a href="http://{host}/{CLEAR_CACHE_PATH}">Clear Cache</a></p>
                </div>
        ''']
        
        # Get app data only once and process in chunks to save memory
        app_data = self._app_data()
        
        # Collect all categories across regions with channel counts
        all_categories = {}
        
        # First pass: collect all categories and their channel counts
        for region, region_data in app_data.items():
            if not region_data.get('channels'):
                continue
                
            for channel in region_data.get('channels', {}).values():
                group = channel.get('group', '').strip()
                if not group:
                    continue
                    
                if group not in all_categories:
                    all_categories[group] = {'count': 0, 'regions': set()}
                    
                all_categories[group]['count'] += 1
                all_categories[group]['regions'].add(region)
        
        # Add categories section if we found any
        if all_categories:
            # Calculate optimal column layout
            categories_html = '''
                <div class="categories">
                    <h2>Categories</h2>
                    <p>Select a category to view channels:</p>
            '''
            
            # Sort categories by count (descending)
            sorted_categories = sorted(all_categories.items(), key=lambda x: x[1]['count'], reverse=True)
            
            # Create category groups - max 5 per row and up to 4 columns
            for i, (category, data) in enumerate(sorted_categories):
                if i % 5 == 0:
                    if i > 0:
                        categories_html += '</div>'
                    categories_html += '<div class="category-group">'
                    
                encoded_category = quote(category)
                region_param = "" if REGION_ALL in data['regions'] else f"&regions={quote('|'.join(data['regions']))}"
                categories_html += f'<div><a href="http://{host}/{PLAYLIST_PATH}?groups={encoded_category}{region_param}">{category}</a> <span class="category-count">({data["count"]})</span></div>'
            
            # Close the last category group
            categories_html += '</div></div>'
            html_parts.append(categories_html)
        
        # Process each region
        for region, region_data in app_data.items():
            # Skip if region has no channels
            if not region_data.get('channels'):
                continue
                
            encoded_region = quote(region)
            region_html = f'''
                <div class="region">
                    <h2>{region_data["name"]}</h2>
                    <p>Playlist: <b><a href="http://{host}/{PLAYLIST_PATH}?regions={encoded_region}">
                       http://{host}/{PLAYLIST_PATH}?regions={encoded_region}</a></b></p>
                    <p>EPG: <b><a href="http://{host}/{EPG_PATH}?regions={encoded_region}">
                       http://{host}/{EPG_PATH}?regions={encoded_region}</a></b></p>
            '''
            
            # Extract unique groups for this region
            group_names = {}  # {group_name: count}
            for channel in region_data.get('channels', {}).values():
                group = channel.get('group', '').strip()
                if group:
                    group_names[group] = group_names.get(group, 0) + 1
            
            # Only add groups section if there are groups
            if group_names:
                region_html += '<h3>Categories:</h3><ul>'
                for group, count in sorted(group_names.items(), key=lambda x: (-x[1], x[0])):  # Sort by count (desc) then name
                    encoded_group = quote(group)
                    region_html += f'<li><a href="http://{host}/{PLAYLIST_PATH}?regions={encoded_region}&groups={encoded_group}">{group}</a> ({count})</li>'
                region_html += '</ul>'
                    
            region_html += '</div>'
            html_parts.append(region_html)
        
        # Close HTML
        html_parts.append('</body></html>')
        
        # Send HTML in chunks to reduce memory usage
        for part in html_parts:
            self.wfile.write(part.encode('utf8'))
            
        # Force garbage collection after generating the page
        gc.collect()

class ThreadingSimpleServer(ThreadingMixIn, HTTPServer):
    pass


def run():
    if os.getenv('IS_DOCKER'):
        PORT = 80
    else:
        parser = argparse.ArgumentParser(description="Samsung TV Plus for Channels")
        parser.add_argument("-port", "--PORT", default=80, help="Port number for server to use (optional)")
        args = parser.parse_args()
        PORT = args.PORT

    print(f"Starting server on port {PORT}")
    server = ThreadingSimpleServer(('0.0.0.0', int(PORT)), Handler)
    server.serve_forever()


if __name__ == '__main__':
    run()
