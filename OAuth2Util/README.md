# OAuth2Util
Utility that allows for easier handling of OAuth2 with PRAW.

In your code you can use it like this:

	import praw
	import OAuth2Util

	r = praw.Reddit("Useragent")
	o = OAuth2Util.OAuth2Util(r)

That's it! To refresh the token (it is only valid for one hour), use `o.refresh()`. This checks first whether the token is still valid and doesn't request a new one if it is still valid. So you can call this method befor every block of PRAW usage. Example:

	import time
	while True:
		o.refresh()
		print(r.get_me().comment_karma)
		time.sleep(3600)

If you want to have different tokens (e.g if your script has to log in with different users), you have to specify a different config file (`o = OAuth2Util.OAuth2Util(r, configfile="otherconfigfile.txt")`).

## Reddit Config
In order to use OAuth2, you have to create an App on Reddit (https://www.reddit.com/prefs/apps/). For most use cases you will choose `script` as app type. You have to set the `redirect uri` to `http://127.0.0.1:65010/authorize_callback`, the other fields are up to you.

## Config
OAuth2Util uses one config file to store the information. Before you can use it, the first two sections must be filled out manually by you, the third one will automatically be filled out when you authorize the script. Your `oauth.txt` should contain these lines:
	
	# Config 
	scope=identity,account,edit,flair,history,livemanage,modconfig,modflair,modlog,modothers,modposts,modself,modwiki,mysubreddits,privatemessages,read,report,save,submit,subscribe,vote,wikiedit,wikiread # These grant the bot to every scope, only use those you want it to access.
	refreshable=True

	# Appinfo
	app_key=thisistheid
	app_secret=ThisIsTheSecretDoNotShare

	# Token
	token=None
	refresh_token=None

