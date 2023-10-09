from flask import Flask, request
from nacl.signing import SigningKey
from nacl.signing import VerifyKey
from nacl.encoding import Base64Encoder, HexEncoder
from nacl.hash import sha512
from datetime import datetime
from pysteamsignin import SteamSignIn
import psycopg
import os
printerr = lambda x: print(x, file=sys.stderr)
# sid_64 unsigned to signed and vice versa
u2s = lambda uint: uint - 2**63
s2u = lambda sint: sint + 2**63
# To give to client
encode_key = lambda signing_key: signing_key.encode(Base64Encoder).decode('utf-8')
# To store in DB
fingerprint = lambda verify_key: sha512(verify_key.encode(), encoder=HexEncoder).decode('utf-8')

app = Flask(__name__)

conn = None

# The following environment variables are used:
'''
FLASK_ENV
KD_HOST : Hostname of webapp, suggest it to be getakey.megascatterbomb.com
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
    # Connect to database
    try:
        conn = psycopg.connect(host=os.getenv('PG_HOST'), port=os.getenv('PG_PORT'), user=os.getenv('PG_USER'), password=os.getenv('PG_PASS'), database=os.getenv('PG_DB'))
    except psycopg.OperationalError as e:
        printerr("Failed to connect to database: " + str(e))
        exit(1)
    if os.getenv('FLASK_ENV') == 'development':
        app.run(host="127.0.0.1", port=4434, debug=True, load_dotenv=True)
    else:
        # Use gunicorn (same port)
        from subprocess import call
        call(["gunicorn", "app:app", "-b", "0.0.0.0:4434"])
        # TODO: Implement a proxy Apache/nginx server to forward requests from 443/tcp

# Returns: {"pub_key_fingerprint": bytes(64), "created": datetime}
def fetch_sid_64(sid_64: int) -> dict:
    with conn.cursor() as cur:
        cur.execute("SELECT pub_key_fingerprint, created FROM pki WHERE sid_64 = %s", (u2s(sid_64),))
        row = cur.fetchone()
        if row == None:
            return None, None
        else:
            return row[0], row[1]

@app.route('/login/<int:sid_64>')
def login(sid_64):
    steamLogin = SteamSignIn()
    # SECURITY: Figure out local https testing, or change to https in prod.
    steamLogin.RedirectUser(steamLogin.ConstructURL('http://%s:%s/verify/%s' % (os.getenv('KD_HOST'), os.getenv('KD_PORT'), sid_64)))
    return "Redirecting to Steam login..."

@app.route('/verify')
def verifier():
    steamLogin = SteamSignIn()
    # Get args from GET
    response = request.args
    sid_64 = steamLogin.ValidateResults(response)
    if sid_64 == None:
        return "Error: Invalid response from Steam Login.", 401
    else:
        fingerprint, created = fetch_sid_64(sid_64)
        if created == None:
            # New user, generate keys
            signing_key = SigningKey.generate()
            verify_key = signing_key.verify_key
            # Insert into database
            with conn.cursor() as cur:
                cur.execute("INSERT INTO pki (sid_64, pub_key_fingerprint, created) VALUES (%s, %s, %s)", (u2s(sid_64), fingerprint(verify_key), datetime.now()))
            # Return signing key to client
            return encode_key(signing_key)
        # Rate limit: 1 hour
        elif datetime.now()-created < timedelta(hours=1):
            return "Error: Rate limit exceeded. Wait 1 hour before creating a new key.", 429
        else:
            # Generate new keys
            signing_key = SigningKey.generate()
            verify_key = signing_key.verify_key
            # Update database
            with conn.cursor() as cur:
                cur.execute("UPDATE pki SET pub_key_fingerprint = %s, created = %s WHERE sid_64 = %s", (fingerprint(verify_key), datetime.now(), u2s(sid_64)))
            # Return signing key to client
            return encode_key(signing_key)

if __name__ == '__main__':
    main()