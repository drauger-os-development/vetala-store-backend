# vetala-store-backend
Vetala Store Back-end API and database handlings, using Flask and SQLite.

## About
The Vetala Store API is a retrieval-only RESTful API, providing developers with the data needed to render relevant info on a client's screen, without the potential security risks of allowing arbitrary edits to the database.

## Interacting with the API
`GET` requests can be made with anything from wget to Firefox and everything in between. `POST` requests are all rejected.

When getting data, there are 3 top-level directories to consider

### `/tags`
There are no sub-directories from here. 

Requesting from this directory returns all possible tags. This can be useful for dynamically rendering possible tags to the user.

Here is an example of a possible return value (prettified to make it more human-readable):

```json
{
	"genres":[
			"open-world",
			"open-source",
			"mining",
			"survival",
			"sandbox",
			"multiplayer",
			"FPS",
			"quake",
			"RTS",
			"Historical",
			"Strategy",
			"demo",
			"puzzle",
			"turn-based strategy",
			"TBS",
			"Arcade",
			"Shoot_'em_up",
			"turn-based_strategy",
			"racing",
			"platformer",
			"MMO"
	],
	"platforms":[
			"linux"
	],
	"ratings":[
			"E",
			"T",
			"NONE",
			"E10+"
	]
}

```

Notice that spaces are not allowed in tag names. When rendering these names, replace underscores with spaces to have them look correctly.

### `/games`
Each game available has it's own sub-directory in this directory.

Requesting data from this directory currently lists data for every available game. Later, this directory will return data about some of the most popular games in the database.

#### `/games/<game>`
This directory returns detailed info about a given game. 

Here's the return from a request to `/games/OpenArena`:

```json
{
		"Name":"OpenArena",
		"description":"OpenArena is a community-produced deathmatch FPS based on GPL idTech3 technology. There are many game types supported including Free For All, Capture The Flag, Domination, Overload, Harvester, and more",
		"downloads":1,
		"genres":[
				"FPS",
				"open-source",
				"quake"
		],
		"joined":1623351659,
		"platform":"linux",
		"rating":"T",
		"screenshots_url":"http://www.openarena.ws/page.php?12"
}

```

Name, description, downloads, rating, and genres should all be fairly self-explanatory.

`joined` is the UNIX timestamp for when the game was added to the database. This can be useful for sorting for new games.

`platform` indicates how the game should be run, and what sort of performance can be expected. There are 4 possible values here:

 * `linux` - These are games that are compiled for x86 or AMD64 Linux. This can be either Debian/Ubuntu, or just Generic Linux
 * `native` - These are games compiled specifically for Vetala's CPU architecture and OS. Client developers are responsible for determining if the system the client is running on meets those requirements and, if not, parsing those games out.
 * `wine` - Windows games that are known to run well in Wine/Proton. These games, when downloaded, will include a script to configure their virtual drive and provide the best compatibility and performance possible.
 * `emulator` - These are games meant to run in emulators. These are often going to be home-brew, open-source games made to either run on the original console, or in the emulator itself. When downloaded, a configuration file will be included that details which emulator is required.
 
 
`screenshots_url` is the URL that points to screenshots for the game in question. HOWEVER, as this is rarely a simple, indexed, folder, this should often be provided as a link. It is advised developers check the returned from the URL provided to see if it is in fact those indexed files, or something else, and handle the link according to those findings.

#### `/games/<game>/download`
This directory should ONLY be queried when a user decides to download a game, in order to prevent affecting download statistics.

Here's the return from a request to `/games/OpenArena/download`:

```json
{
	"URL":"openarena",
	"in_pack_man":1
}
```

`URL` is either the download URL or the package name for the game. Which it is is indicated by `in_pack_man` (`true` (or `1`) if a package name, `false` (or `0`) if a URL). 

When a legitimate URL is provided, developers need to check the URL to see if it points to a TAR ball (or Sourceforge), or some page. If a TAR ball (or Sourceforge) is provided, you can download the game in the background and install the game however necessary. If it points to a web page, the webpage needs to be rendered in a web browser window, as a pay-wall is present. Once past the pay-wall, the download should be started.

### `/search`
`/search` does what it says on the tin: it searches for things. There are to ways to do this:

#### `/search/tags=<comma delimited list of tags>`
Here you can search games based on certain tags. There are 3 categories of tags, which you can search through simultaneously:

 * rating - The official or anticipated ESRB rating of a game
 * genre - The genre(s) the game fits into. `open-source` is included here as a genre, for those who only want to play open-source games
 * platform - How a game should be run. Retro-philes may want to explore the `emulator` tag, while gamers who come from Windows may want to try the `wine` tag. Those who want games that will just work and perform well out of the box will want to explore the `native` tag. And long-time Linux gamers may enjoy surfing games under the `linux` section.
 
#### `/search/free-text=<free text>`
Using the free-text function, you can search for random text in a game's name or description.


Please note you CANNOT search using both tags and free text simultaneously. Instead, try performing a search request using the free-text function, then searching the returned data for the relevant tags yourself.


