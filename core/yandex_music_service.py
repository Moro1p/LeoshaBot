import logging
import asyncio
import json
import random
import string
import yandex_music
import aiohttp
from aiohttp import ClientConnectorError, ClientTimeout
import os
from dotenv import load_dotenv, set_key

from utils.short_url import get_short_url

load_dotenv()
YANDEX_TOKEN = os.getenv("YA_AC_TOKEN")

class YandexMusicService:
    def __init__(self, ya_token):
        self.token = ya_token
        self.client = yandex_music.Client(token=ya_token).init()
        self.device_id = "".join([random.choice(string.ascii_lowercase) for _ in range(16)])
        self.logger = logging.getLogger(self.__class__.__name__)

    def extract_device_name(self, data: dict) -> str:
        try:
            devices = data.get("devices", [])
            active_device_id = data.get("active_device_id_optional")

            return next(
                (device["info"]["title"] for device in devices if device["info"]["device_id"] == active_device_id),
                "Desktop",
            )
        except KeyError as e:
            return f"error: {e}"

    async def get_current_track(self) -> dict:
        device_info = {"app_name": "Chrome", "type": 1}

        ws_proto = {
            "Ynison-Device-Id": self.device_id,
            "Ynison-Device-Info": json.dumps(device_info),
        }
        timeout = ClientTimeout(total=15, connect=10)
        session = None

        try:
            session = aiohttp.ClientSession(timeout=timeout)
            async with session.ws_connect(
                url="wss://ynison.music.yandex.ru/redirector.YnisonRedirectService/GetRedirectToYnison",
                headers={
                    "Sec-WebSocket-Protocol": f"Bearer, v2, {json.dumps(ws_proto)}",
                    "Origin": "https://music.yandex.ru",
                    "Authorization": f"OAuth {self.token}",
                },
                timeout=10,
            ) as ws:
                recv = await ws.receive()
                data = json.loads(recv.data)

            if "redirect_ticket" not in data or "host" not in data:
                self.logger.error(f"Invalid response structure: {data}")
                return {"success": False}

            new_ws_proto = ws_proto.copy()
            new_ws_proto["Ynison-Redirect-Ticket"] = data["redirect_ticket"]

            to_send = {
                "update_full_state": {
                    "player_state": {
                        "player_queue": {
                            "current_playable_index": -1,
                            "entity_id": "",
                            "entity_type": "VARIOUS",
                            "playable_list": [],
                            "options": {"repeat_mode": "NONE"},
                            "entity_context": "BASED_ON_ENTITY_BY_DEFAULT",
                            "version": {
                                "device_id": ws_proto["Ynison-Device-Id"],
                                "version": 9021243204784341000,
                                "timestamp_ms": 0,
                            },
                            "from_optional": "",
                        },
                        "status": {
                            "duration_ms": 0,
                            "paused": True,
                            "playback_speed": 1,
                            "progress_ms": 0,
                            "version": {
                                "device_id": ws_proto["Ynison-Device-Id"],
                                "version": 8321822175199937000,
                                "timestamp_ms": 0,
                            },
                        },
                    },
                    "device": {
                        "capabilities": {
                            "can_be_player": True,
                            "can_be_remote_controller": False,
                            "volume_granularity": 16,
                        },
                        "info": {
                            "device_id": ws_proto["Ynison-Device-Id"],
                            "type": "WEB",
                            "title": "Chrome Browser",
                            "app_name": "Chrome",
                        },
                        "volume_info": {"volume": 0},
                        "is_shadow": False,
                    },
                    "is_currently_active": False,
                },
                "rid": "ac281c26-a047-4419-ad00-e4fbfda1cba3",
                "player_action_timestamp_ms": 0,
                "activity_interception_type": "DO_NOT_INTERCEPT_BY_DEFAULT",
            }

            async with session.ws_connect(
                url=f"wss://{data['host']}/ynison_state.YnisonStateService/PutYnisonState",
                headers={
                    "Sec-WebSocket-Protocol": f"Bearer, v2, {json.dumps(new_ws_proto)}",
                    "Origin": "https://music.yandex.ru",
                    "Authorization": f"OAuth {self.token}",
                },
                timeout=10,
                method="GET",
            ) as ws:
                await ws.send_str(json.dumps(to_send))
                recv = await asyncio.wait_for(ws.receive(), timeout=10)
                ynison = json.loads(recv.data)
                #print(ynison) #======================================================================
                track_index = ynison["player_state"]["player_queue"]["current_playable_index"]
                if track_index == -1:
                    self.logger.warning("No track is currently playing.")
                    return {"success": False}
                track = ynison["player_state"]["player_queue"]["playable_list"][track_index]

            return {
                "paused": ynison["player_state"]["status"]["paused"],
                "duration_ms": ynison["player_state"]["status"]["duration_ms"],
                "progress_ms": ynison["player_state"]["status"]["progress_ms"],
                "track_id": track["playable_id"],
                "album_id": track["album_id_optional"],
                "success": True,
            }

        except ClientConnectorError as e:
            self.logger.error(f"Cannot connect to host: {e}. Please check your connection.")
            return {"success": False}
        except asyncio.TimeoutError:
            self.logger.error("Request timed out. Please check your connection.")
            return {"success": False}
        except Exception as e:
            self.logger.error(f"An unexpected error occurred: {str(e)}")
            return {"success": False}
        finally:
            if session is not None:
                await session.close()

    async def get_track_by_id(self, track_id: str):
        try:
            track = await asyncio.to_thread(self.client.tracks, track_id)
            if not track or not track[0]:
                self.logger.error(f"Track with ID {track_id} not found.")
                return {"success": False}

            return {
                "success": True,
                "title": track[0].title,
                "og_image": track[0].og_image,
                "artists": [artist.name for artist in track[0].artists],
                "album": track[0].albums[0].title if track[0].albums else None,
            }
        except Exception as e:
            self.logger.error(f"Failed to fetch track info for ID {track_id}: {str(e)}")
            return {"success": False}
    
    async def get_track(self):
        current_state = await self.get_current_track()

        if current_state['success'] is True:
            track = await self.get_track_by_id(current_state["track_id"])
            if track['success'] is True:
                link = f'music.yandex.ru/album/{current_state['album_id']}/track/{current_state['track_id']}'
                short_link = await get_short_url(link)
                self.logger.info(f"Successful fetch track {track["title"]}")
                if short_link:
                    link = short_link
                return {'success': True, 'title': track['title'], 'album': track['album'], 'artists': track['artists'], 'og_image': track['og_image'], 'link': link, 'duration_ms': current_state['duration_ms'], 'progress_ms': current_state['progress_ms'], 'paused': current_state['paused']}
            return {'success': False}
        return {'success': False}


if __name__ == "__main__":
    service = YandexMusicService(YANDEX_TOKEN)
    info = asyncio.run(service.get_track())
    print(info)