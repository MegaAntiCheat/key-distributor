from flask import Flask
from nacl.signing import SigningKey
from nacl.signing import VerifyKey
from nacl.encoding import Base64Encoder, HexEncoder
from nacl.hash import sha512
from steamid import SteamID
# To give to client
encode_key = lambda signing_key: signing_key.encode(Base64Encoder).decode('utf-8')
# To store in DB
fingerprint = lambda verify_key: sha512(verify_key.encode(), encoder=HexEncoder).decode('utf-8')

app = Flask(__name__)

# TODO: Implement app