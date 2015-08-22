#!/usr/bin/env python
from __future__ import print_function

import praw
import os
import re
import time
import webbrowser
import __main__ as main
from threading import Thread
try:
	# Python 3.x
	import configparser
	from http.server import HTTPServer, BaseHTTPRequestHandler
	from urllib.parse import urlparse, parse_qs
except ImportError:
	# Python 2.x
	import ConfigParser as configparser
	from SimpleHTTPServer import SimpleHTTPRequestHandler as BaseHTTPRequestHandler
	from SocketServer import TCPServer as HTTPServer
	from urlparse import urlparse, parse_qs


# ### CONFIGURATION ### #
REFRESH_MARGIN = 60
TOKEN_VALID_DURATION = 3600
SERVER_URL = "127.0.0.1"
SERVER_PORT = 65010
SERVER_REDIRECT_PATH = "authorize_callback"
SERVER_LINK_PATH = "oauth"
try:
	DEFAULT_CONFIG = os.path.join(os.path.dirname(os.path.abspath(main.__file__)), "oauth.ini")
except AttributeError:
	# running interactive
	DEFAULT_CONFIG = os.path.join(os.path.dirname(os.path.abspath(".")), "oauth.ini")

CONFIGKEY_APP_KEY = ("app", "app_key")
CONFIGKEY_APP_SECRET = ("app", "app_secret")
CONFIGKEY_SCOPE = ("app", "scope")
CONFIGKEY_REFRESHABLE = ("app", "refreshable")
CONFIGKEY_TOKEN = ("token", "token")
CONFIGKEY_REFRESH_TOKEN = ("token", "refresh_token")
CONFIGKEY_VALID_UNTIL = ("token", "valid_until")

CONFIGKEY_SERVER_MODE = ("server", "server_mode")
CONFIGKEY_SERVER_URL = ("server", "url")
CONFIGKEY_SERVER_PORT = ("server", "port")
CONFIGKEY_SERVER_REDIRECT_PATH = ("server", "redirect_path")
CONFIGKEY_SERVER_LINK_PATH = ("server", "link_path")
# ### END CONFIGURATION ### #


class OAuth2UtilRequestHandler(BaseHTTPRequestHandler):

	def do_GET(self):
		"""
		Handle the retrieval of the code
		"""
		parsed_url = urlparse(self.path)

		if parsed_url[2] == "/" + SERVER_REDIRECT_PATH:  # 2 = Path
			parsed_query = parse_qs(parsed_url[4])  # 4 = Query

			if "code" not in parsed_query:
				self.send_response(200)
				self.send_header("Content-Type", "text/plain")
				self.end_headers()

				self.wfile.write("No code found, try again!".encode("utf-8"))
				return

			self.server.oauth2util.response_code = parsed_query["code"][0]

			self.send_response(200)
			self.send_header("Content-Type", "text/plain")
			self.end_headers()

			self.wfile.write(
				"Thank you for using OAuth2Util. The authorization was successful, "
				"you can now close this window.".encode("utf-8"))
		elif parsed_url[2] == "/" + SERVER_LINK_PATH: # 2 = Path
			self.send_response(200)
			self.send_header("Content-Type", "text/html")
			self.end_headers()

			self.wfile.write("<html><body>Hey there!<br/>Click <a href=\"{0}\">here</a> to claim your prize.</body></html>"
				.format(self.server.oauth2util.authorize_url).encode("utf-8"))
		else:
			self.send_response(404)
			self.send_header("Content-Type", "text/plain")
			self.end_headers()
			self.wfile.write("404 not found".encode("utf-8"))


class OAuth2Util:

	def __init__(self, reddit, app_key=None, app_secret=None, scope=None,
				 refreshable=None, configfile=DEFAULT_CONFIG, print_log=False,
				 server_mode=None):
		"""
		Create a new instance. The app info can also be read from a config file.
		"""

		self.r = reddit
		self.server = None

		self.configfile = configfile

		self.config = configparser.ConfigParser()
		needMigration = None
		try:
			self.config.read(configfile)
			if len(self.config.sections()) == 0:
				if os.path.isfile("oauth.txt"):
					needMigration = "oauth.txt"
				else:
					raise FileNotFoundError("File " + configfile + " not found")
		except configparser.MissingSectionHeaderError:
			needMigration = configfile

		if needMigration is not None:
			self._migrate_config(needMigration, configfile)
			self.config.read(configfile)

		if not self.config.has_section(CONFIGKEY_SERVER_MODE[0]):
			self.config.add_section(CONFIGKEY_SERVER_MODE[0])

		try:
			self._get_value(CONFIGKEY_SERVER_MODE)
		except KeyError:
			self.config.set(CONFIGKEY_SERVER_MODE[0], CONFIGKEY_SERVER_MODE[1], str(False))

		if app_key is not None:
			self.config.set(CONFIGKEY_APP_KEY[0], CONFIGKEY_APP_KEY[1], str(app_key))
		if app_secret is not None:
			self.config.set(CONFIGKEY_APP_SECRET[0], CONFIGKEY_APP_SECRET[1], str(app_secret))
		if scope is not None:
			self.config.set(CONFIGKEY_SCOPE[0], CONFIGKEY_SCOPE[1], str(scope))
		if refreshable is not None:
			self.config.set(CONFIGKEY_REFRESHABLE[0], CONFIGKEY_REFRESHABLE[1], str(refreshable))
		if server_mode is not None:
			self.config.set(CONFIGKEY_SERVER_MODE[0], CONFIGKEY_SERVER_MODE[1], str(server_mode))

		global SERVER_URL, SERVER_PORT, SERVER_REDIRECT_PATH, SERVER_LINK_PATH
		SERVER_URL = self._get_value(CONFIGKEY_SERVER_URL, exception_default=SERVER_URL)
		SERVER_PORT = self._get_value(CONFIGKEY_SERVER_PORT, int, exception_default=SERVER_PORT)
		SERVER_REDIRECT_PATH = self._get_value(CONFIGKEY_SERVER_REDIRECT_PATH, exception_default=SERVER_REDIRECT_PATH)
		SERVER_LINK_PATH = self._get_value(CONFIGKEY_SERVER_LINK_PATH, exception_default=SERVER_LINK_PATH)

		self._print = print_log

		self._set_app_info()
		self.refresh()
		self.set_access_credentials()

	# ### LOAD SETTINGS ### #

	def _set_app_info(self):
		"""
		Set the app info (id & secret) read from the config file on the Reddit object
		"""
		redirect_url = "http://{0}:{1}/{2}".format(SERVER_URL, SERVER_PORT,
												   SERVER_REDIRECT_PATH)
		self.r.set_oauth_app_info(self._get_value(CONFIGKEY_APP_KEY),
								  self._get_value(CONFIGKEY_APP_SECRET),
								  redirect_url)

	def _get_value(self, key, func=None, split_val=None, as_boolean=False,
		exception_default=None):
		"""
		Helper method to get a value from the config
		"""
		try:
			if as_boolean:
				return self.config.getboolean(key[0], key[1])
			value = self.config.get(key[0], key[1])
			if split_val is not None:
				value = value.split(split_val)
			if func is not None:
				return func(value)
			return value
		except (KeyError, configparser.NoSectionError, configparser.NoOptionError) as e:
			if exception_default is not None:
				return exception_default
			raise KeyError(e)

	def _change_value(self, key, value):
		"""
		Change the value of the given key in the given file to the given value
		"""
		if not self.config.has_section(key[0]):
			self.config.add_section(key[0])

		self.config.set(key[0], key[1], str(value))

		with open(self.configfile, "w") as f:
			self.config.write(f)

	def _migrate_config(self, oldname=DEFAULT_CONFIG, newname=DEFAULT_CONFIG):
		"""
		Migrates the old config file format to the new one
		"""
		print("Your OAuth2Util config file is in an old format and needs "
			"to be changed. I tried as best as I could to migrate it.")

		with open(oldname, "r") as old:
			with open(newname, "w") as new:
				new.write("[app]\n")
				new.write(old.read())

	# ### SAVE SETTINGS ### #

	# ### REQUEST FIRST TOKEN ### #

	def _start_webserver(self, authorize_url=None):
		"""
		Start the webserver that will receive the code
		"""
		server_address = (SERVER_URL, SERVER_PORT)
		self.server = HTTPServer(server_address, OAuth2UtilRequestHandler)
		self.server.oauth2util = self
		self.response_code = None
		self.authorize_url = authorize_url
		t = Thread(target=self.server.serve_forever)
		t.daemon = True
		t.start()

	def _wait_for_response(self):
		"""
		Wait until the user accepted or rejected the request
		"""
		while not self.response_code:
			time.sleep(2)
		time.sleep(5)
		self.server.shutdown()

	def _get_new_access_information(self):
		"""
		Request new access information from reddit using the built in webserver
		"""
		try:
			url = self.r.get_authorize_url(
				"SomeRandomState", self._get_value(CONFIGKEY_SCOPE, set, split_val=","),
				self._get_value(CONFIGKEY_REFRESHABLE, as_boolean=True))
		except praw.errors.OAuthAppRequired:
			print(
				"Cannot obtain authorize url from praw. Please check your "
				"configuration files.")
			raise

		self._start_webserver(url)
		if not self._get_value(CONFIGKEY_SERVER_MODE, as_boolean=True):
			webbrowser.open(url)
		else:
			print("Webserver is waiting for you :D. Please open {0}:{1}/{2} "
					"in your browser"
				.format(SERVER_URL, SERVER_PORT, SERVER_LINK_PATH))
		self._wait_for_response()

		try:
			access_information = self.r.get_access_information(
				self.response_code)
		except praw.errors.OAuthException:
			print("--------------------------------")
			print("Can not authenticate, maybe the app infos (e.g. secret) "
					"are wrong.")
			print("--------------------------------")
			raise

		self._change_value(CONFIGKEY_TOKEN, access_information["access_token"])
		self._change_value(CONFIGKEY_REFRESH_TOKEN, access_information["refresh_token"])
		self._change_value(CONFIGKEY_VALID_UNTIL, time.time() + TOKEN_VALID_DURATION)

	def _check_token_present(self):
		"""
		Check whether the tokens are set and request new ones if not
		"""
		try:
			self._get_value(CONFIGKEY_TOKEN)
			self._get_value(CONFIGKEY_REFRESH_TOKEN)
			self._get_value(CONFIGKEY_REFRESHABLE)
		except KeyError:
			if self._print:
				print("Request new Token (CTP)")
			self._get_new_access_information()

	# ### PUBLIC API ### #

	def toggle_print(self):
		"""
		Enable / Disable log output
		"""
		self._print = not self._print
		if self._print:
			print('OAuth2Util printing on')

	def set_access_credentials(self):
		"""
		Set the token on the Reddit Object again
		"""
		self._check_token_present()

		try:
			self.r.set_access_credentials(self._get_value(CONFIGKEY_SCOPE, set, split_val=","),
										  self._get_value(CONFIGKEY_TOKEN),
										  self._get_value(CONFIGKEY_REFRESH_TOKEN))
		except (praw.errors.OAuthInvalidToken, praw.errors.HTTPException):
			if self._print:
				print("Request new Token (SAC)")
			self._get_new_access_information()

	# ### REFRESH TOKEN ### #

	def refresh(self, force=False):
		"""
		Check if the token is still valid and requests a new if it is not
		valid anymore

		Call this method before a call to praw
		if there might have passed more than one hour

		force: if true, a new token will be retrieved no matter what
		"""
		self._check_token_present()

		# We check whether another instance already refreshed the token
		if time.time() > self._get_value(CONFIGKEY_VALID_UNTIL, float) - REFRESH_MARGIN:
			self.config.read(self.configfile)
			if time.time() < self._get_value(CONFIGKEY_VALID_UNTIL, float) - REFRESH_MARGIN:
				if self._print:
					print("Found new token")
				self.set_access_credentials()

		if force or time.time() > self._get_value(CONFIGKEY_VALID_UNTIL, float) - REFRESH_MARGIN:
			if self._print:
				print("Refresh Token")
			try:
				new_token = self.r.refresh_access_information(self._get_value(CONFIGKEY_REFRESH_TOKEN))
				self._change_value(CONFIGKEY_TOKEN, new_token["access_token"])
				self._change_value(CONFIGKEY_VALID_UNTIL, time.time() + TOKEN_VALID_DURATION)
				self.set_access_credentials()
			except (praw.errors.OAuthInvalidToken, praw.errors.HTTPException):
				if self._print:
					print("Request new Token (REF)")
				self._get_new_access_information()
