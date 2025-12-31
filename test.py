import os
from steam_web_api import Steam

KEY = os.environ.get("EFA2CD4576ADDB945C7BA590FFF90F0A")

terraria_app_id = 552520
steam = Steam()

# arguments: app_id
user = steam.apps.search_games("terr")
print(user)

