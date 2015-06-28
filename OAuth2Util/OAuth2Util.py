#!/usr/bin/env python

import os
import time
import webbrowser
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

import praw


# ### CONFIGURATION ### #
REFRESH_MARGIN = 60
REDIRECT_URL = "127.0.0.1"
REDIRECT_PORT = 65010
REDIRECT_PATH = "authorize_callback"
DEFAULT_CONFIG_PATH = os.path.expanduser("~/.praw-oauth-config.txt")
# ### END CONFIGURATION ### #


class OAuth2UtilRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed_url = urlparse(self.path)

        if parsed_url[2] != "/" + REDIRECT_PATH:  # 2 = Path
            self.send_response(404)
            self.end_headers()
            return

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
            "Thank you for using OAuth2Util. The authorization was successful,\
             you can now close this window.".encode("utf-8"))


class OAuth2Util:

    def __init__(self, reddit, app_key, app_secret, scopes=['identity'],
                 refreshable=True, oauthtoken_configfile=DEFAULT_CONFIG_PATH,
                 print_log=False):
        self.r = reddit
        self.token = None
        self.refresh_token = None
        self.valid_until = time.time()
        self.scopes = set(scopes)
        self.refreshable = refreshable
        self.server = None

        self.app_key = app_key
        self.app_secret = app_secret

        self._print = print_log

        self.OAUTHTOKEN_CONFIGFILE = oauthtoken_configfile

        self._set_app_info()
        self._set_access_credentials()

    # ### LOAD SETTINGS ### #

    def _set_app_info(self):
        redirect_url = "http://{0}:{1}/{2}".format(REDIRECT_URL, REDIRECT_PORT,
                                                   REDIRECT_PATH)
        self.r.set_oauth_app_info(self.app_key, self.app_secret, redirect_url)

    def _set_access_credentials(self):
        try:
            self.r.set_access_credentials(self.scopes, self.token,
                                          self.refresh_token)
        except praw.errors.OAuthInvalidToken:
            if self._print:
                print("Request new Token")
            self._get_new_access_information()

    # ### SAVE SETTINGS ### #

    def _save_token(self):
        with open(self.OAUTHTOKEN_CONFIGFILE, "w") as f:
            f.write("{0}\n{1}\n".format(self.token, self.refresh_token))

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
        while not self.response_code:
            time.sleep(2)
        time.sleep(5)
        self.server.shutdown()

    def _get_new_access_information(self):
        try:
            url = self.r.get_authorize_url(
                "SomeRandomState", self.scopes, self.refreshable)
        except praw.errors.OAuthAppRequired:
            print(
                "Cannot obtain authorize url from praw. Please check your \
                configuration files.")
            raise

        self._start_webserver()
        webbrowser.open(url)
        self._wait_for_response()

        try:
            access_information = self.r.get_access_information(
                self.response_code)
        except praw.errors.OAuthException:
            print("--------------------------------")
            print(
                "Can not authenticate, maybe the app infos (e.g. secret) \
                are wrong.")
            print("--------------------------------")
            raise

        self.token = access_information["access_token"]
        self.refresh_token = access_information["refresh_token"]
        self.valid_until = time.time() + 3600
        self._save_token()

    # ### PUBLIC API ### #

    def toggle_print(self):
        self._print = not self._print
        if self._print:
            print('OAuth2Util printing on')

    def set_access_credentials(self):
        """
        Set the token on the Reddit Object again
        """
        self.r.set_access_credentials(set(self.scopes), self.token,
                                      self.refresh_token)

    # ### REFRESH TOKEN ### #

    def refresh(self):
        """
        Check if the token is still valid and requests a new if it is not
        valid anymore

        Call this method before a call to praw
        if there might have passed more than one hour
        """
        if time.time() > self.valid_until - REFRESH_MARGIN:
            if self._print:
                print("Refresh Token")
            new_token = self.r.refresh_access_information(self.refresh_token)
            self.token = new_token["access_token"]
            self.valid_until = time.time() + 3600
            self._save_token()
            # self.set_access_credentials(self.scopes, self.refreshable)
