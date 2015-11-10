# OAuth2Util
Utility that allows for easier handling of OAuth2 with PRAW.

In your code you can use it like this:

	import praw
	import OAuth2Util

	r = praw.Reddit("Useragent")
	o = OAuth2Util.OAuth2Util(r)

That's it! To refresh the token (it is only valid for one hour), use `o.refresh()`. This checks first whether the token is still valid and doesn't request a new one if it is still valid. So you can call this method befor every block of PRAW usage. Example:

	while True:
		o.refresh()
		print(r.get_me().comment_karma)
		time.sleep(3600)

If you want to have different tokens (e.g if your script has to log in with different users), you have to specify a different config file (`o = OAuth2Util.OAuth2Util(r, configfile="otherconfigfile.ini")`).

Starting with version 3.2 praw will refresh the token automatically if it encounters an InvalidTokenException. If you want to use this new feature, you should call `o.refresh(force=True)` once at the start to make sure praw has a valid refresh token:

	import praw
	import OAuth2Util

	r = praw.Reddit("Useragent")
	o = OAuth2Util.OAuth2Util(r)
	o.refresh(force=True)

	while True:
		print(r.get_me().comment_karma)
		time.sleep(3600)

Both methods should work without a problem. If you use the first method (without force, calling `refresh()` often) several instances of the script can share a token and only the first script will refresh the token. The other instances will pick it up automatically.

## Reddit Config
In order to use OAuth2, you have to create an App on Reddit (https://www.reddit.com/prefs/apps/). For most use cases you will choose `script` as app type. You have to set the `redirect uri` to `http://127.0.0.1:65010/authorize_callback`, the other fields are up to you.

# Server Mode
Add a line `server_mode=True` to your config file or initialize with `o = OAuth2Util.OAuth2Util(r, server_mode=True)` to activate server mode. This mode is designed for use where the script doesn't run locally but runs on a remote server instead. In this scenario it's not really helpful to open a webbrowser on the server, is it? If server mode is activated you can open a page in your local browser where you can click a link for the authorization. By default this page is `127.0.0.1:65010/oauth` but you can change those values in the config file.

## Config
OAuth2Util uses one config file to store the information. Before you can use it, the first two sections must be filled out manually by you, the third one will automatically be filled out when you authorize the script. Your `oauth.ini` should contain these lines:

	[app]
	# These grant the bot to every scope, only use those you want it to access.
	scope=identity,account,edit,flair,history,livemanage,modconfig,modflair,modlog,modothers,modposts,modself,modwiki,mysubreddits,privatemessages,read,report,save,submit,subscribe,vote,wikiedit,wikiread
	refreshable=True
	app_key=thisistheid
	app_secret=ThisIsTheSecretDoNotShare

	[server]
	server_mode=False
	url=127.0.0.1
	port=65010
	redirect_path=authorize_callback
	link_path=oauth

	# Will be filled automatically
	[token]
	token=None
	refresh_token=None
	valid_until=0

## Known Inconveniences
There are two small inconveniences with OAuth2Util:

### Your default browser can't be Microsoft Edge
This is an issue with Python, not OAuth2Util. Sometimes a built in python function that OAuth2Util uses to print out the callback info will detect Microsoft Edge as Opera, but then fail later when a file named "opera.bat" is not found, or something within that bat file will go wrong since it was not meant for Microsoft Edge. To resolve this, change your default browser to anything but Edge. You can change it back after initial token retreival has taken place.

### Rarely, OAuth2Util.OAuth2Util(r) will fail due to left open sockets
This is a very rare occurence and you will probably never see this issue. Most of the time it is caused if you had called `OAuth2Util.OAuth2Util(r)` on an older version, updated, and then called it again sometime later on. Otherwise the socket was kept open by some other software and was never closed. However, if and when this occurs, the previously opened sockets will close themselves, and you can call `OAuth2Util.OAuth2Util(r)` again with no problem.
