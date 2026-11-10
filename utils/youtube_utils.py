# utils/youtube_utils.py
from youtubesearchpython import VideosSearch
import re
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import Config
import aiohttp
import asyncio
import html
import logging
import threading
from urllib.parse import parse_qs, urlsplit
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable

def clean_metadata_text(text: str) -> str:
    """
    Cleans up HTML-encoded characters in any metadata text, converting them to their intended form.
    
    Args:
        text (str): The text string potentially containing HTML entities.
    
    Returns:
        str: A cleaned-up version of the text.
    """
    return html.unescape(text)

# One client per worker thread: built once instead of on every call, and
# not shared across threads because its HTTP transport isn't thread-safe.
_youtube_clients = threading.local()


def get_youtube_client():
    """Return this thread's YouTube API client, building it on first use.
    Call it inside asyncio.to_thread so the build stays off the event loop."""
    if not hasattr(_youtube_clients, 'client'):
        _youtube_clients.client = build(
            'youtube', 'v3', developerKey=Config.YOUTUBE_API_KEY)
    return _youtube_clients.client


async def resolve_channel(channel_identifier: str) -> dict | None:
    """
    Resolves a channel handle (e.g., '@AmoebaSisters', '@crashcourse')
    or channel ID (starts with 'UC') to an ID YouTube confirms exists.
    Returns {'channel_id', 'name'}, or None if there's no such channel;
    raises if the lookup fails.
    """
    clean_id = channel_identifier.strip()

    # Look up UC... channel IDs too, so a made-up ID isn't accepted
    if clean_id.startswith('UC') and len(clean_id) == 24:
        lookup = {'id': clean_id}
    else:
        # Ensure handle format (e.g., '@AmoebaSisters')
        handle = clean_id if clean_id.startswith('@') else f"@{clean_id}"
        lookup = {'forHandle': handle}
    try:

        # Run the synchronous function in a thread pool to make it async-friendly

        def fetch_channel_id():
            return get_youtube_client().channels().list(
                part='id,snippet',
                **lookup
            ).execute()
        response = await asyncio.to_thread(fetch_channel_id)

        items = response.get('items', [])
        if items:
            return {'channel_id': items[0]['id'],
                    'name': items[0]['snippet']['title']}

        return None

    except HttpError as e:
        logging.error(f"HTTP Error resolving handle '{channel_identifier}': "
                      f"{e.resp.status} {e.reason} {e.error_details}")
        raise
    except Exception as e:
        logging.error(f"Error resolving channel handle '{channel_identifier}': {e}")
        raise


async def fetch_videos_for_topic_and_channel(topic: str, channel_id: str, limit: int = 3) -> list[dict]:
    """
    Fetch candidate videos for a given topic from a specific YouTube channel
    using the official YouTube Data API v3. `channel_id` is the saved,
    already-resolved channel ID (UC...).
    """
    try:
        logging.debug(f"Starting API search for topic: {topic} in channel: {channel_id} (limit={limit})")

        # Run the synchronous function in a thread pool to make it async-friendly
        def fetch_videos():
            search_response = get_youtube_client().search().list(
                q=topic,
                channelId=channel_id,  # Strictly restricts search to this channel
                type='video',          # Only retrieve videos
                part='id,snippet',
                maxResults=limit
            ).execute()
            results = search_response.get('items', [])
            return results

        results = await asyncio.to_thread(fetch_videos)

        if not results:
            logging.warning(f"No results found for topic '{topic}' in channel '{channel_id}'")
            return []

        videos = []
        for item in results:
            video_id = item['id']['videoId']
            snippet = item['snippet']

            videos.append({
                'title': clean_metadata_text(snippet.get('title', 'No Title Found')),
                'link': f"https://www.youtube.com/watch?v={video_id}",
                'channel': snippet.get('channelTitle', 'No Channel Found'),
                'thumbnail': (snippet.get('thumbnails', {})
                              .get('high', {}).get('url', ''))
            })

        logging.debug(f"Extracted {len(videos)} videos for topic '{topic}' in channel '{channel_id}'")
        return videos

    except HttpError as e:
        logging.error(f"YouTube API HttpError for topic '{topic}' in channel "
                      f"'{channel_id}': {e.resp.status} {e.reason} "
                      f"{e.error_details}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error fetching videos: {e}")
        return []

async def fetch_videos_for_topic(topic, limit=3):
    """
    Fetch multiple candidate videos for a given topic from YouTube.

    Parameters:
    - topic (str): The topic to search for.
    - limit (int): Maximum number of videos to return.

    Returns:
    - list[dict]: A list of video metadata dicts (title, link, channel, thumbnail),
                  or an empty list if no videos are found.
    """
    try:
        logging.debug(f"Starting search for topic: {topic} (limit={limit})")
        search = VideosSearch(topic, limit=limit)
        search_results = search.result()
        results = search_results.get('result', [])

        if not results:
            logging.warning(f"No results found for topic '{topic}'")
            return []

        videos = []
        for video in results[:limit]:
            videos.append({
                'title': clean_metadata_text(video.get('title', 'No Title Found')),
                'link': video.get('link', 'No Link Found'),
                'channel': video.get('channel', {}).get('name', 'No Channel Found'),
                'thumbnail': video.get('thumbnails', [{}])[0].get('url', 'No Thumbnail Found')
            })

        logging.debug(f"Extracted {len(videos)} videos for topic '{topic}'")
        return videos

    except Exception as e:
        logging.error(f"Error fetching videos for topic '{topic}': {e}")
        return []


def extract_video_id(youtube_url):
    """Extracts the video ID from a YouTube URL."""
    video_id = None
    regex = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    match = re.search(regex, youtube_url)
    if match:
        video_id = match.group(1)
    return video_id


_YOUTUBE_VIDEO_ID = re.compile(r'[0-9A-Za-z_-]{11}')
_YOUTUBE_HOSTS = {'youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com',
                  'youtube-nocookie.com', 'www.youtube-nocookie.com'}
_YOUTUBE_ID_PATHS = {'shorts', 'embed', 'live', 'v'}
_YOUTUBE_START_TIME = re.compile(r'(?:(\d{1,3})h)?(?:(\d{1,5})m)?(?:(\d{1,6})s?)?')


def normalize_youtube_link(link):
    """Return https://www.youtube.com/watch?v=<id> (plus the start time, if
    one was given) for a link to a YouTube video, or None for anything else.

    The link is rebuilt from the video id instead of being stored as typed,
    so no other part of the input (a javascript: link, another site, or a URL
    a browser would read differently from Python) ever reaches the page."""
    if not isinstance(link, str):
        return None
    link = link.strip()
    if '://' not in link:
        link = 'https://' + link  # pasted without http(s)://
    try:
        parts = urlsplit(link)
        host = parts.hostname
    except ValueError:
        return None
    if parts.scheme not in ('http', 'https'):
        return None

    query = parse_qs(parts.query)
    segments = parts.path.strip('/').split('/')
    if host == 'youtu.be':
        video_id = segments[0]
    elif host in _YOUTUBE_HOSTS and parts.path.rstrip('/') == '/watch':
        video_id = query.get('v', [''])[0]
    elif host in _YOUTUBE_HOSTS and len(segments) >= 2 and segments[0] in _YOUTUBE_ID_PATHS:
        video_id = segments[1]
    else:
        return None
    if not _YOUTUBE_VIDEO_ID.fullmatch(video_id):
        return None

    normalized = f"https://www.youtube.com/watch?v={video_id}"
    # Keep a start time like t=90, t=90s or t=1m30s (start=90 on embed links).
    # Anything else, including absurdly long numbers, just drops the start time.
    start = (query.get('t') or query.get('start') or [''])[0]
    match = _YOUTUBE_START_TIME.fullmatch(start)
    if start and match:
        hours, minutes, seconds = (int(group or 0) for group in match.groups())
        total = hours * 3600 + minutes * 60 + seconds
        if total:
            normalized += f"&t={total}s"
    return normalized


async def get_video_metadata(youtube_url):
    """Retrieves metadata for a YouTube video by URL asynchronously."""
    video_id = extract_video_id(youtube_url)
    if not video_id:
        return {"error": "Invalid YouTube URL"}

    # YouTube API URL for getting video details
    api_url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}&key={Config.YOUTUBE_API_KEY}"

    async with aiohttp.ClientSession() as session:
        async with session.get(api_url) as response:
            if response.status == 200:
                response_data = await response.json()

                if "items" in response_data and len(response_data["items"]) > 0:
                    video = response_data["items"][0]["snippet"]
                    metadata = {
                        "title": clean_metadata_text(video["title"]),
                        "link" : youtube_url,
                        "channel": video["channelTitle"],
                        "thumbnail": video["thumbnails"]["high"]["url"],
                    }
                    return metadata
                else:
                    return {"error": "Video not found"}
            else:
                return {"error": f"Failed to fetch metadata, status code: {response.status}"}


async def fetch_video_transcript(video_id_or_url, languages=['en']):
    """
    Fetches transcript for a YouTube video.
    
    Parameters:
    - video_id_or_url (str): YouTube video ID or full URL
    - languages (list): List of language codes to try (default: ['en'])
    
    Returns:
    - dict: Dictionary with transcript data:
        {
            'transcript': [...],  # List of transcript segments with text, start, duration
            'transcript_text': '...',  # Full transcript as plain text
            'language': 'en',  # Language code of transcript
            'success': True
        }
        OR
        {
            'success': False,
            'error': 'Error message'
        }
    """
    try:
        # Extract video ID if URL is provided
        video_id = extract_video_id(video_id_or_url) if 'youtube.com' in video_id_or_url or 'youtu.be' in video_id_or_url else video_id_or_url
        
        if not video_id:
            return {
                'success': False,
                'error': 'Invalid video ID or URL'
            }
        
        # Run the synchronous transcript API in a thread pool to make it async-friendly
        # New API (v1.2.3+) requires instantiating the class
        def fetch_transcript():
            api = YouTubeTranscriptApi()
            fetched_transcript = api.fetch(video_id, languages=languages)
            # Convert FetchedTranscriptSnippet objects to list of dicts format
            return [
                {
                    'text': snippet.text,
                    'start': snippet.start,
                    'duration': snippet.duration
                }
                for snippet in fetched_transcript
            ]
        
        loop = asyncio.get_event_loop()
        transcript_list = await loop.run_in_executor(None, fetch_transcript)
        
        # Format transcript data
        # transcript_list is a list of dicts: [{'text': '...', 'start': 0.0, 'duration': 5.0}, ...]
        transcript_text = ' '.join([item['text'] for item in transcript_list])
        
        return {
            'success': True,
            'transcript': transcript_list,
            'transcript_text': transcript_text,
            'language': languages[0] if transcript_list else None,
            'video_id': video_id
        }
        
    except TranscriptsDisabled:
        return {
            'success': False,
            'error': 'Transcripts are disabled for this video'
        }
    except NoTranscriptFound:
        return {
            'success': False,
            'error': f'No transcript found for this video in languages: {languages}'
        }
    except VideoUnavailable:
        return {
            'success': False,
            'error': 'Video is unavailable or does not exist'
        }
    except Exception as e:
        logging.error(f"Error fetching transcript for video {video_id_or_url}: {e}")
        return {
            'success': False,
            'error': f'Failed to fetch transcript: {str(e)}'
        }
