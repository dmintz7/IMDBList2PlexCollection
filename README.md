# IMDBList2PlexCollection
This is a fork of deva5610/IMDBList2PlexCollection which takes an IMDB list, match the movies in your Plex Library and turn them into a collection. 

This script extends upon this and will add the movies not in the Plex Library to Radarr

# Configuration
Rename config.ini.sample to config.ini and populate all values

With each additional list increase the first value by one.
After the equal sign, list are comma separted with by:
Name of the Collection in Plex
IMDB List URL
Number of Pages to Loop, Default is 1

[general]
add_missing=False

[lists]
1=AFI's 100 Years...100 Movies - 1998,https://www.imdb.com/list/ls003795336/

[plex]
url=http://PLEX-SERVER-URL:32400
token=REPLACEmeWITHyourTOKEN
library=Movies,Test Library,Kids

[radarr]
host=http://RADARR-SERVER-URL:7878
api=RADARR-API-TOKEN
quality_profile=1
monitored=True
path_root=BASE-PATH-OF-MOVIES
search=True
minimumAvailability=released

[tmdb]
apikey=a41366ab753e5388ffcf31a63a6bbea8


# Usage
Run pip install -r requirements.txt to install dependencies then run python imdb2collection.py

Running daily will ensure any newly added movies to the Plex Library are added to the collection
