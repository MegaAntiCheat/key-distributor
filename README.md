# key-distributor
Stateless web app written in Flask to distribute account-tied private keys to MegaAntiCheat clients using Steam OAuth.  
_work in progress_

# Getting Started

This uses Python 3.11, but most previous versions past 3.6 should work fine.

Create venv and activate it:
`python -m venv venv-311/`  
`.\venv-311\Scripts\activate` (on Windows cmd.exe or PowerShell)  
`source venv-311/bin/activate` (on Bash)

Install dependencies:
`python -m pip install -r requirements.txt`

Run the app:
`flask run`