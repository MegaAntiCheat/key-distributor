from flask import Flask, request, jsonify, redirect, jsonify, make_response
from nacl.signing import SigningKey
from nacl.signing import VerifyKey
from nacl.encoding import Base64Encoder, RawEncoder, HexEncoder
from nacl.hash import sha512
from datetime import datetime, timedelta
from pysteamsignin.steamsignin import SteamSignIn
from steamid import SteamID
import psycopg
import os
from sys import stderr
from dotenv import load_dotenv, find_dotenv
printerr = lambda x: print(x, file=stderr)
# sid_64 unsigned to signed and vice versa
u2s = lambda uint: uint - 2**63
s2u = lambda sint: sint + 2**63
# To give to client
encode_key = lambda signing_key: signing_key.encode(Base64Encoder).decode('utf-8')
# To store in DB
fingerprint = lambda verify_key: sha512(verify_key.encode(), encoder=RawEncoder)
# To query from whoami
fp_human_readable = lambda fingerprint: fingerprint.encode(HexEncoder).decode('utf-8')

app = Flask(__name__)

def main():
    # Check if .env exists in root directory
    if os.path.exists('.env'):
        load_dotenv(find_dotenv(), override=True)
    else:
        printerr("WARNING: No .env file found in root directory.")
    # Check that all environment variables are set
    env_vars = ['FLASK_ENV', 'KD_HOST', 'KD_PORT', 'KD_DEBUG', 'PG_HOST', 'PG_PORT', 'PG_USER', 'PG_PASS', 'PG_DB']
    # Filter out unset environment variables
    unset_vars = list(filter(lambda x: os.getenv(x) == None, env_vars))
    dbg = False
    if len(unset_vars) > 0:
        printerr("The following environment variables are unset: " + str(unset_vars))
        printerr("Please set them and try again.")
        exit(1)
    if os.getenv('KD_DEBUG') in ('True', 'true', '1', 't', 'y', 'yes', 'Y', 'Yes', 'YES'):
        dbg = True
    else:
        dbg = False
    # Connect to database
    try:
        global conn
        conn = psycopg.connect(host=os.getenv('PG_HOST'), port=os.getenv('PG_PORT'), user=os.getenv('PG_USER'), password=os.getenv('PG_PASS'), dbname=os.getenv('PG_DB'))
    except psycopg.OperationalError as e:
        printerr("Failed to connect to database: " + str(e))
        exit(1)
    if os.getenv('FLASK_ENV') == 'development':
        app.run(host="127.0.0.1", port=os.getenv("KD_PORT"), debug=dbg, load_dotenv=True)
    else:
        # Use gunicorn (same port)
        from subprocess import call
        call(["gunicorn", "app:app", "-b", "0.0.0.0:%s" % os.getenv("KD_PORT")])
        # TODO: Implement a proxy Apache/nginx server to forward requests from 443/tcp

# Returns: {"pub_key_fingerprint": bytes(64), "created": datetime}
def fetch_sid_64(sid_64: int) -> dict:
    with conn.cursor() as cur:
        cur.execute("SELECT pub_key_fingerprint, created FROM pki WHERE sid_64 = %s", (u2s(int(sid_64)),))
        row = cur.fetchone()
        if row == None:
            return None, None
        else:
            return row[0], row[1]

@app.route('/login')
def login():
    steamLogin = SteamSignIn()
    # SECURITY: Figure out local https testing, or change to https in prod.
    return steamLogin.RedirectUser(steamLogin.ConstructURL('http://%s:%s/verify' % (os.getenv('KD_HOST'), os.getenv('KD_PORT'))))

@app.route('/verify')
def verifier():
    crudded = False
    steamLogin = SteamSignIn()
    # Get args from GET
    steam_response = request.args
    sid_64 = steamLogin.ValidateResults(steam_response)
    printerr("Got sid_64: " + str(sid_64))
    response = None
    if sid_64 == False:
        response = app.response_class(
            response="Error: Invalid response from Steam Login.",
            status=401,
            mimetype='text/plain'
        )
    else:
        _, created = fetch_sid_64(sid_64)
        if created == None:
            printerr("New user, generating keys.")
            # New user, generate keys
            signing_key = SigningKey.generate()
            verify_key = signing_key.verify_key
            # Insert into database
            with conn.cursor() as cur:
                cur.execute("INSERT INTO pki (sid_64, pub_key_fingerprint, created) VALUES (%s, %s, %s)", (u2s(int(sid_64)), fingerprint(verify_key), datetime.now()))
                conn.commit()
            # Return signing key to client
            return encode_key(signing_key)
        # Rate limit: 1 hour
        elif datetime.now()-created < timedelta(hours=1):
            printerr("Rate Limit Exceeded.")
            response = app.response_class(
                response="Error: Rate limit exceeded. Wait 1 hour before creating a new key.",
                status=429,
                mimetype='text/plain'
            )
        else:
            # Generate new keys
            printerr("Updating keys.")
            signing_key = SigningKey.generate()
            verify_key = signing_key.verify_key
            # Update database
            with conn.cursor() as cur:
                cur.execute("UPDATE pki SET pub_key_fingerprint = %s, created = %s WHERE sid_64 = %s", (fingerprint(verify_key), datetime.now(), u2s(int(sid_64))))
                conn.commit()
            # Return signing key to client
            response = app.response_class(
                response=encode_key(signing_key),
                status=200,
                mimetype='text/plain'
            )
    return response

# Takes lower-case hex string
# Returns json
@app.route('/whoami/<pub_key_fingerprint>')
def whoami(pub_key_fingerprint):
    hash = None
    # Validate that pub_key_fingerprint is a possible SHA-512 hash
    try:
        hash = bytes.fromhex(pub_key_fingerprint)
        if len(hash) != 64:
            raise ValueError
    except ValueError:
        # Response should have json with one key, "error"
        response = make_response(
            jsonify({"error": "Invalid public key fingerprint."}),
            400,
        )
        return response
    sid_64 = None
    # Check if public key fingerprint exists in database, store sid_64 if it does
    with conn.cursor() as cur:
        cur.execute("SELECT sid_64 FROM pki WHERE pub_key_fingerprint = %s", (hash,))
        row = cur.fetchone()
        if row == None:
            # Response should have json with one key, "error"
            # Use jsonify
            response = make_response(
                jsonify({"error": "Fingerprint not found."}),
                404,
            )
            response.headers['Content-Type'] = 'application/json'
            return response
        else:
            sid_64 = s2u(row[0])
    printerr("sid_64 in whoami: " + str(sid_64))
    sid = SteamID(str(sid_64))
    payload = {
        "error": None,
        "steam3ID": sid.steam3(),
        "steamID64": str(sid_64),
        "steamID32": sid.steam2(newerFormat=False),
        "url": "https://steamcommunity.com/profiles/%s" % str(sid_64),
    }
    response = make_response(
        jsonify(payload),
        200,
    )
    response.headers['Content-Type'] = 'application/json'
    return response

if __name__ == '__main__':
    main()