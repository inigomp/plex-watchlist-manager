import requests
import xml.etree.ElementTree as ET

class PlexAPI:
    def __init__(self, token):
        self.token = token
        self.headers = {
            "Accept": "application/json",
            "X-Plex-Language": "es"
        }

    def get_watchlist(self):
        """Fetches all items from the Plex Universal Watchlist with pagination."""
        items = []
        start = 0
        size = 100
        while True:
            url = f"https://discover.provider.plex.tv/library/sections/watchlist/all?X-Plex-Token={self.token}&X-Plex-Container-Start={start}&X-Plex-Container-Size={size}"
            resp = requests.get(url, headers=self.headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json().get("MediaContainer", {})
                batch = data.get("Metadata", [])
                items.extend(batch)
                total = data.get("totalSize", 0)
                if len(items) >= total or not batch:
                    break
                start += size
            else:
                break
        return items

    def get_server_libraries(self, server_name="Navidad"):
        """Discovers servers and returns libraries for a specific server."""
        resources_url = f"https://plex.tv/api/resources?includeHttps=1&X-Plex-Token={self.token}"
        resp = requests.get(resources_url, timeout=10)
        if resp.status_code != 200: return []
        
        root = ET.fromstring(resp.content)
        devices = root.findall(".//Device[@provides='server']")
        
        for device in devices:
            if device.get("name") == server_name:
                access_token = device.get("accessToken")
                connections = device.findall("Connection")
                for conn in connections:
                    address = conn.get("uri")
                    try:
                        sections_url = f"{address}/library/sections?X-Plex-Token={access_token}"
                        sec_resp = requests.get(sections_url, timeout=5, verify=False)
                        if sec_resp.status_code == 200:
                            sec_root = ET.fromstring(sec_resp.content)
                            return [{
                                "title": s.get("title"),
                                "key": s.get("key"),
                                "address": address,
                                "token": access_token
                            } for s in sec_root.findall(".//Directory")]
                    except: continue
        return []

    def get_library_items(self, library):
        """Fetches all items from a specific library section."""
        url = f"{library['address']}/library/sections/{library['key']}/all?X-Plex-Token={library['token']}"
        resp = requests.get(url, timeout=20, verify=False)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            return root.findall(".//Video") or root.findall(".//Directory")
        return []
