from flask import Flask
from nacl.signing import SigningKey
from nacl.signing import VerifyKey
from nacl.encoding import Base64Encoder, HexEncoder
from nacl.hash import sha512
from steamid import SteamID
from datetime import datetime
from get_param import Param
printerr = lambda x: print(x, file=sys.stderr)
# To give to client
encode_key = lambda signing_key: signing_key.encode(Base64Encoder).decode('utf-8')
# To store in DB
fingerprint = lambda verify_key: sha512(verify_key.encode(), encoder=HexEncoder).decode('utf-8')

app = Flask(__name__)

# The following environment variables are used:
'''
FLASK_ENV
KD_PORT
KD_DEBUG
STEAM_CID : Steam client ID of administrator (NOT the same as a SteamID64)
STEAM_WEB_API_KEY : Used for Steam OAuth access
STEAM_API_DOMAIN : Used for Steam OAuth access
Database stuff:
PG_HOST
PG_PORT
PG_USER
PG_PASS
PG_DB : Database name (tenatively, "mac-kd")
'''

def main():
    # Check that all environment variables are set
    env_vars = ['FLASK_ENV', 'KD_PORT', 'KD_DEBUG', 'STEAM_CID', 'STEAM_WEB_API_KEY', 'STEAM_API_DOMAIN', 'PG_HOST', 'PG_PORT', 'PG_USER', 'PG_PASS', 'PG_DB']
    # Filter out unset environment variables
    unset_vars = list(filter(lambda x: os.getenv(x) == None, env_vars))
    if len(unset_vars) > 0:
        printerr("The following environment variables are unset: " + str(unset_vars))
        printerr("Please set them and try again.")
        exit(1)
    if os.getenv('FLASK_ENV') == 'development':
        app.run(host="127.0.0.1", port=4434, debug=True, load_dotenv=True)
    else:
        # Use gunicorn (same port)
        from subprocess import call
        call(["gunicorn", "app:app", "-b", "0.0.0.0:4434"])
        # TODO: Implement a proxy Apache/nginx server to forward requests from 443/tcp

#Set up a route at "/oauth" that takes a SteamID64 and directs the user to Steam OAuth
@app.route('/oauth/<steamid64>')
def oauth(steamid64):
    # Redirect user to Steam OAuth
    steam_cid = os.getenv('STEAM_CID')
    app.redirect("https://steamcommunity.com/oauth/login?response_type=token&client_id={steam_cid}&scope=openid&state={steamid64}")

# Callbacks at "/oauth/callback"
# Error callback redirects to "http://redirect/uri/here#error=access_denied&state=steamid64"
# Success callback redirects to "http://redirect/uri/here#access_token=token_here&token_type=steam&state=steamid64"
@app.route('/oauth/callback')
def oauth_callback():
    # Check for error
    if request.args.get('error') != None:
        # Show user error 401
        return "401: OAuth Failed", 401
    else:
        # Get access token
        access_token = request.args.get('access_token')
        # TODO: Check if token is valid



if __name__ == '__main__':
    main()