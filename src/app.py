from flask import Flask
from nacl.signing import SigningKey
from nacl.encoding import Base64Encoder
from steamid import SteamID
encode_key = lambda signing_key: signing_key.encode(Base64Encoder).decode('utf-8')

app = Flask(__name__)

# TODO: Implement app