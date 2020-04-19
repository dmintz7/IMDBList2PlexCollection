import os
import sys
import json
import requests
import time
import platform
from lxml import html
from plexapi.server import PlexServer
from tmdbv3api import TMDb
from tmdbv3api import Movie

# Hacky solution for Python 2.x & 3.x compatibility
if hasattr(__builtins__, 'raw_input'):
	input=raw_input


### ConfigParser Python2/3 Support ###

try:
	# >3.2
	from configparser import ConfigParser
except ImportError:
	# python27
	# Refer to the older SafeConfigParser as ConfigParser
	from ConfigParser import SafeConfigParser as ConfigParser

parser = ConfigParser()

# Get config.ini path and check it exists!
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.ini')
didreadreadme = os.path.isfile(config_path)
if not didreadreadme:
	print("You need to read the README. Please create a config.ini in the same folder as this program.")
	print("\n")
	input("Press Enter to exit, and then go and read the README.")
	sys.exit()

# Process config.ini
parser.read(config_path)

PLEX_URL = parser.get('plex', 'url')
# Strip trailing slashes from URL
slash = '/'
if (PLEX_URL[-1] == slash):
	PLEX_URL = PLEX_URL.rstrip('//')
PLEX_TOKEN = parser.get('plex', 'token')
MOVIE_LIBRARIES = parser.get('plex', 'library').split(',')

def script(IMDB_COLLECTION_NAME, IMDB_URL, PAGE_NUMBERS=1):
	if not (IMDB_URL[-1] == slash):
		IMDB_URL = IMDB_URL + '/'

	def add_collection(library_key, rating_key):
		headers = {"X-Plex-Token": PLEX_TOKEN}
		params = {"type": 1,
				  "id": rating_key,
				  "collection[0].tag.tag": IMDB_COLLECTION_NAME,
				  "collection.locked": 0
				  }

		url = "{base_url}/library/sections/{library}/all".format(base_url=PLEX_URL, library=library_key)
		r = requests.put(url, headers=headers, params=params)

	def run_imdb_sync():
		try:
			plex = PlexServer(PLEX_URL, PLEX_TOKEN)
		except:
			print("No Plex server found at: {base_url}".format(base_url=PLEX_URL))
			print("Please check that config.ini exists, and is correct.")
			print("If the URL displayed is correct, your token may be incorrect.")
			input("Press Enter to exit")
			sys.exit()

# Get list of movies from the Plex server
		all_movies = []
		for movie_lib in MOVIE_LIBRARIES:
			try:
				print("Retrieving a list of movies from the '{library}' library in Plex.".format(library=movie_lib))
				movie_library = plex.library.section(movie_lib)
				library_language = movie_library.language  # IMDB will use language from last library in list
				all_movies.extend(movie_library.all())
			except:
				print("The '{library}' library does not exist in Plex.".format(library=movie_lib))
				print("Please check that config.ini exists, and is correct.")
				input("Press Enter to exit")
				sys.exit()

# Get the requested imdb list
		print("Retrieving movies from selected IMDB list. Depending on the amount of pages selected this might take a few minutes.")
		maxpages = int(PAGE_NUMBERS) + 1
		title_name = []
		title_years = []
		title_ids = []
		for i in range(1,maxpages):
			url = IMDB_URL + '?page={}'.format(i)
			r = requests.get(url, headers={'Accept-Language': library_language})
			tree = html.fromstring(r.content)
			title_name.extend(tree.xpath("//div[contains(@class, 'lister-item-content')]//h3[contains(@class, 'lister-item-header')]//a/text()"))
			title_years.extend(tree.xpath("//div[contains(@class, 'lister-item-content')]//h3[contains(@class, 'lister-item-header')]//span[contains(@class, 'lister-item-year')]/text()"))
			title_ids.extend(tree.xpath("//div[contains(@class, 'lister-item-image')]//a/img//@data-tconst"))

# Convert TMDB to IMDB ID and create a dictionary of {imdb_id: movie} 
		print("Matching IMDB IDs to Library. For large Libraries using TMDB agent this step can take a long time.")
		reqcount = 0
		tmdb = TMDb()
		tmdb.api_key = parser.get('tmdb', 'apikey')
		movie = Movie()
		imdb_map = {}
		for m in all_movies:		 
			if 'themoviedb://' in m.guid:
				if reqcount >= 10:
					time.sleep(2.5)
					reqcount = 0
				if tmdb.api_key:
					try:
						tmdb_id = m.guid.split('themoviedb://')[1].split('?')[0]
						tmdbapi = movie.details(tmdb_id)
						imdb_id = tmdbapi.imdb_id
						reqcount += 1
					except AttributeError:
						imdb_id = None
						reqcount += 1
				else:
					imdb_id = None
			elif 'imdb://' in m.guid:
				imdb_id = m.guid.split('imdb://')[1].split('?')[0]
			else:
				imdb_id = None
			
			if imdb_id and imdb_id in title_ids:
				imdb_map[imdb_id] = m
			else:
				imdb_map[m.ratingKey] = m

# Add movies to the selected collection
		print("Adding the collection '{}' to matched movies.".format(IMDB_COLLECTION_NAME))
		in_library_idx = []
		for i, imdb_id in enumerate(title_ids):
			movie = imdb_map.pop(imdb_id, None)
			if movie:
				add_collection(movie.librarySectionID, movie.ratingKey)
				in_library_idx.append(i)

# Get list of missing movies from selected list
		missing_imdb_movies = [(idx, imdb) for idx, imdb in enumerate(zip(title_ids, title_name, title_years))
							if idx not in in_library_idx]

		return missing_imdb_movies, len(title_ids)

	if __name__ == "__main__":

		missing_imdb_movies, list_count = run_imdb_sync()
	
		print("\n===================================================================\n")
		print("Number of IMDB movies from selected list in the library: {count}".format(count=list_count-len(missing_imdb_movies)))
		print("Number of missing selected list movies: {count}".format(count=len(missing_imdb_movies)))
		print("\nList of movies missing that are in selected IMDB list:\n")
		
		x = 0
		y = 0
		for idx, (imdb_id, title, year) in missing_imdb_movies:
			if platform.python_version().startswith('2'):
				print("{idx}\t{imdb_id}\t{title} {year}".format(idx=idx+1, imdb_id=imdb_id.encode('UTF-8'), title=title.encode('UTF-8'), year=year.encode('UTF-8')))
			else:
				print("{idx}\t{imdb_id}\t{title} {year}".format(idx=idx+1, imdb_id=imdb_id, title=title, year=year))
			if parser.get('general','add_missing') == True:
				if request_movie(imdb_id, title, year):
					x+=1
				else:
					y+=1
		
		return "List: %s - %s movies, Already in Library: %s, Added to Radarr: %s, Remaining: %s\n" % (IMDB_COLLECTION_NAME, list_count, list_count-len(missing_imdb_movies), x, y)

def request_movie(imdb_id, title, year):
	try:
		rdr = API(parser.get('radarr','host') + '/api', parser.get('radarr','api'))
		response = rdr.search_imdb(imdb_id)
		tmdbId = response.json()['tmdbId']
		payload = {"tmdbId": tmdbId,
			   "title": title,
			   "qualityProfileId": parser.get('radarr','quality_profile'),
			   "images": [],
			   "monitored": parser.get('radarr','monitored'),
			   "titleSlug": title,
			   "rootFolderPath": parser.get('radarr','path_root'),
			   "minimumAvailability": parser.get('radarr','minimumAvailability'),
			   "year": int(year[1:-1]),
			   "addOptions" : {
				  "searchForMovie" : parser.get('radarr','search')
				}
			 }
		response = rdr.add_movie(payload)
		rdr.command({'name':'MoviesSearch', 'movieIds': response['id']})
		print("sent to radarr successfully")
		return True
	except ValueError:
			print("Unable to find on TheMovieDB")
			return False
	except TypeError:
			print(response[0]['errorMessage'])
			return False
	except Exception as e:
		print("failed to send request to radarr")
		print('Error on line {}, {}, {}'.format(sys.exc_info()[-1].tb_lineno, type(e).__name__, e))
		print(response)
		return False
		

class API(object):

	def __init__(self, host_url, api_key):
		"""Constructor requires Host-URL and API-KEY"""
		self.host_url = host_url
		self.api_key = api_key

	# ENDPOINT COMMAND
	def command(self, command_json):
		res = self.request_post("{}/command".format(self.host_url), data=command_json)
		return res.json()

	def add_movie(self, movie_json):
		"""Add a new series to your collection"""
		res = self.request_post("{}/movie".format(self.host_url), data=movie_json)
		return res.json()
		
	def search_imdb(self, imdb):
		"""Searches for new shows on trakt"""
		res = self.request_get("{}/movie/lookup/imdb?imdbID={}".format(self.host_url, imdb))
		return res
		
	def request_get(self, url, data={}):
		"""Wrapper on the requests.get"""
		headers = {
			'X-Api-Key': self.api_key
		}
		res = requests.get(url, headers=headers, json=data)
		return res

	def request_post(self, url, data):
		"""Wrapper on the requests.post"""
		headers = {
			'X-Api-Key': self.api_key
		}
		res = requests.post(url, headers=headers, json=data)
		return res

print("Starting IMDB List to Collection Add")
lists = parser.items('lists')
review = ""
for key, value in lists:
	if value.count(",") == 1: value = value+",1"
	(IMDB_COLLECTION_NAME, IMDB_URL, PAGE_NUMBERS) = value.split(",")
	print("Selecting %s (%s)" % (IMDB_COLLECTION_NAME, IMDB_URL))
	try:
		review  = review + script(IMDB_COLLECTION_NAME, IMDB_URL, PAGE_NUMBERS)
	except:
		pass