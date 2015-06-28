import praw
import webbrowser
import time
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from threading import Thread

# ### CONFIGURATION ### #
REFRESH_MARGIN = 60
REDIRECT_URL = "127.0.0.1"
REDIRECT_PORT = 65010
REDIRECT_PATH = "authorize_callback"
# ### END CONFIGURATION ### #

class OAuth2UtilRequestHandler(BaseHTTPRequestHandler):
	def do_GET(self):
		parsed_url = urlparse(self.path)
		
		if parsed_url[2] != "/" + REDIRECT_PATH: # 2 = Path
			self.send_response(404)
			self.end_headers()
			return
		
		parsed_query = parse_qs(parsed_url[4]) # 4 = Query
		
		if not "code" in parsed_query:
			self.send_response(200)
			self.send_header("Content-Type", "text/plain")
			self.end_headers()
			
			self.wfile.write("No code found, try again!".encode("utf-8"))
			return
		
		self.server.oauth2util.response_code = parsed_query["code"][0]
		
		self.send_response(200)
		self.send_header("Content-Type", "text/plain")
		self.end_headers()
		
		self.wfile.write("Thank you for using OAuth2Util. The authorization was successful, you can now close this window.".encode("utf-8"))

class OAuth2Util:

	def __init__(self, reddit, config_file="oauth2.conf", print_log=False):
		self.r = reddit
		self.token = None
		self.refresh_token = None
		self.valid_until = time.time()
		self.server = None
		
		self._print = print_log
		
		self.OAUTHCONFIG = config_file
		self.config = self.read_config()
		
		self._set_app_info()
		self.set_access_credentials()
	
	# ### LOAD SETTINGS ### #
	
	def _set_app_info(self):
		self.r.set_oauth_app_info(self.config["client_id"], self.config["secret_id"], "http://{0}:{1}/{2}".format(REDIRECT_URL, REDIRECT_PORT, REDIRECT_PATH))
	
	# ### CONFIG ### #
	
	def read_config(self):
		try:
			with open(self.OAUTHCONFIG) as f:
				lines = [x.strip() for x in f.readlines()]
			pat = re.compile(r"^(\w+)[\t ]*=[\t ]*(.+)$")
			d = {}
			for l in lines:
				m = pat.match(l)
				try:
					key = m.group(1)
					val = m.group(2)
				except AttributeError:
					continue
				if val=="True":val=True
				if val=="False":val=False
				if val=="None":val=None
				if key=="scope":val=val.split(",")
				d[key] = val
			return d
		except OSError:
			print(self.OAUTHCONFIG, "not found.")
	
	def _change_value(self, key, value):
		try:
			with open(self.OAUTHCONFIG) as f:
				lines = [x.strip() for x in f.readlines()]
			for i in range(len(lines)):
				if lines[i].startswith(key):
					lines[i] = "%s=%s" % (key, str(value))
			with open(self.OAUTHCONFIG) as f:
				f.write("\n".join(lines))
		except OSError:
			print(self.OAUTHCONFIG, "not found.")
			
	# ### SAVE SETTINGS ### #
	
	def _save_token(self):
		self._change_value("token", self.config["token"])
		self._change_value("refresh_token", self.config["refresh_token"])
			
	# ### REQUEST FIRST TOKEN ### #

	def _start_webserver(self):
		server_address = (REDIRECT_URL, REDIRECT_PORT)
		self.server = HTTPServer(server_address, OAuth2UtilRequestHandler)
		self.server.oauth2util = self
		self.response_code = None
		t = Thread(target=self.server.serve_forever)
		t.daemon = True
		t.start()
	
	def _wait_for_response(self):
		while self.response_code == None:
			time.sleep(2)
		time.sleep(5)
		self.server.shutdown()

	def _get_new_access_information(self):
		try:
			url = self.r.get_authorize_url("SomeRandomState", self.config["scope"], self.config["refreshable"])
		except praw.errors.OAuthAppRequired:
			print("Cannot obtain authorize url from praw. Please check your configuration files.")
			raise

		self._start_webserver()
		webbrowser.open(url)
		self._wait_for_response()
		
		try:
			access_information = self.r.get_access_information(self.response_code)
		except praw.errors.OAuthException:
			print("--------------------------------")
			print("Can not authenticate, maybe the app infos (e.g. secret) are wrong.")
			print("--------------------------------")
			raise
		
		self.config["token"] = access_information["access_token"]
		self.config["refresh_token"] = access_information["refresh_token"]
		self.valid_until = time.time() + 3600
		self._save_token()
		
	# ### PUBLIC API ### #
	
	def toggle_print(self):
		self._print = not self._print
		if self._print:
			print("OAuth2Util printing on")
	
	def set_access_credentials(self):
		"""
		Set the token on the Reddit Object again
		"""
		try:
			self.r.set_access_credentials(set(self.config["scope"]), self.config["token"], self.config["refresh_token"])
		except praw.errors.OAuthInvalidToken:
			if self._print:
				print("Request new Token")
			self._get_new_access_information()
		
	# ### REFRESH TOKEN ### #
	
	def refresh(self):
		"""
		Check if the token is still valid and requests a new if it is not valid anymore
		
		Call this method before a call to praw
		if there might have passed more than one hour
		"""
		if time.time() > self.valid_until - REFRESH_MARGIN:
			if self._print:
				print("Refresh Token")
			new_token = self.r.refresh_access_information(self.config["refresh_token"])
			self.config["token"] = new_token["access_token"]
			self.valid_until = time.time() + 3600
			self._save_token()
			#self.set_access_credentials(self.scopes, self.refreshable)
