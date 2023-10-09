# key-distributor
Stateless web app written in Flask to distribute account-tied private keys to MegaAntiCheat clients using Steam OpenID.  
_work in progress_

# Getting Started

This uses Python 3.11, but most previous versions past 3.6 should work fine.

Create venv and activate it:  
`python -m venv venv-311/`  
`.\venv-311\Scripts\activate` (on Windows cmd.exe or PowerShell)  
`source venv-311/bin/activate` (on Bash)

Install dependencies:  
`python -m pip install -r requirements.txt`

Set environment variables (in .env in project root), set by default in prod workflow:  

`FLASK_ENV` : `production` or `development`
`KD_PORT`  
`KD_DEBUG`  
`STEAM_CID` : Steam client ID of administrator (NOT the same as a SteamID64)  
`STEAM_WEB_API_KEY` : Used for Steam OAuth access  
`STEAM_API_DOMAIN` : Used for Steam OAuth access  

Database stuff:  
`PG_HOST`  
`PG_PORT`  
`PG_USER`  
`PG_PASS`  
`PG_DB` : Database name (tenatively, `"mac-kd"`)

Run the app:  
`flask run`
