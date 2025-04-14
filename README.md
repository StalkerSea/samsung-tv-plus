# Samsung TV Plus for Channels

A memory-efficient service that provides Samsung TV Plus channels as a standard IPTV playlist and EPG for use with Channels DVR or other IPTV players.

## Overview

This project creates a local web server that fetches Samsung TV Plus channel data and Electronic Program Guide (EPG) information, and serves it in standard formats compatible with IPTV players. It's designed to be lightweight and optimized for resource-constrained environments like Raspberry Pi.

## Features

- Serves Samsung TV Plus channels as an M3U8 playlist
- Provides EPG (Electronic Program Guide) data in XMLTV format
- Region filtering for different countries
- Channel group filtering
- Custom channel numbering
- Memory-efficient design for running on resource-constrained devices
- File-based caching system to reduce API calls
- Docker support with multi-architecture builds (arm/v7, arm64, amd64)

## Available Regions

- `at` (Austria)
- `ca` (Canada)
- `ch` (Switzerland)
- `de` (Germany)
- `es` (Spain)
- `fr` (France)
- `gb` (United Kingdom)
- `in` (India)
- `it` (Italy)
- `kr` (Korea)
- `us` (United States)

## Installation

### Prerequisites

- Python 3.8+
- pip (Python package manager)

### Local Installation

1. Clone this repository:

   ```bash
   git clone https://github.com/matthuisman/samsung-tvplus-for-channels.git
   cd samsung-tvplus-for-channels
   ```

2. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the server:

   ```bash
   python app.py --PORT 8182
   ```

   The server will start on port 8182 (or your specified port).

4. Access the web interface at: http://localhost:8182/

## Docker Installation

If you prefer using Docker:

 ```bash
 docker-compose up -d
 ```

This will start the service on port 8182 (configurable in the `docker-compose.yml` file).

## Usage

### Basic URLs

- **Web Interface**: http://localhost:8182/
- **Playlist URL**: http://localhost:8182/playlist.m3u8
- **EPG URL**: http://localhost:8182/epg.xml
- **Clear Cache**: http://localhost:8182/clear_cache

### Environment Variables

You can configure the service using these environment variables:

| Environment Variable | Description                                       | Default Value |
| -------------------- | ------------------------------------------------- | ------------- |
| `PORT`               | Port number for the web server                    | `8182`        |
| `REGION`             | Region code for TV channels (e.g., us, gb, de)    | `us`          |
| `GROUPS`             | Filter specific channel groups (comma-separated)  | All groups    |
| `NO_GROUPS`          | Exclude specific channel groups (comma-separated) | None          |
| `START_CHANNEL`      | Starting channel number                           | `1000`        |
| `CACHE_HOURS`        | Duration in hours before refreshing cache         | `12`          |
| `BASE_URL`           | Base URL for playlist and EPG generation          | Auto-detected |
| `LOG_LEVEL`          | Logging verbosity (DEBUG, INFO, WARNING, ERROR)   | `INFO`        |

### URL Parameters

The playlist and EPG endpoints can be customized using URL parameters:

#### Playlist Parameters

- **regions**: Filter channels by region codes (pipe-separated)
  ```
  http://localhost:8182/playlist.m3u8?regions=us|gb
  ```

- **groups**: Filter channels by groups (pipe-separated)
  ```
  http://localhost:8182/playlist.m3u8?groups=News|Sports
  ```

- **start_chno**: Starting channel number (integer)
  ```
  http://localhost:8182/playlist.m3u8?start_chno=1000
  ```

- **sort**: Sort method (`chno` or `name`)
  ```
  http://localhost:8182/playlist.m3u8?sort=name
  ```

- **include**: Only include specified channel IDs (pipe-separated)
  ```
  http://localhost:8182/playlist.m3u8?include=samsung-123|samsung-456
  ```

- **exclude**: Exclude specified channel IDs (pipe-separated)
  ```
  http://localhost:8182/playlist.m3u8?exclude=samsung-789
  ```

### EPG Parameters

- **regions**: Filter EPG by region code
  ```
  http://localhost:8182/epg.xml?regions=us
  ```

## Memory Optimization

This service is designed to run efficiently on resource-constrained devices:

- Uses file-based caching to reduce memory usage
- Processes large files in chunks to limit memory consumption
- Implements garbage collection for better memory management
- Configurable limits for channels and EPG size

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

Original project by Matt Huisman.
