"""Generate Google Calendar auth URL. Run once, then paste redirect URL."""
import json, os, pickle, sys
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPE = ['https://www.googleapis.com/auth/calendar']
BASE = os.path.dirname(os.path.realpath(__file__))
CREDENTIALS = os.path.join(BASE, '..', 'credentials.json')
TOKEN = os.path.join(BASE, '..', 'token.pickle')

def main():
    with open(CREDENTIALS) as f:
        raw = json.load(f)
    if 'web' in raw and 'installed' not in raw:
        raw['installed'] = raw.pop('web')
        with open(CREDENTIALS, 'w') as f:
            json.dump(raw, f, indent=2)

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS, scopes=SCOPE)
    auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline',
        include_granted_scopes='true')
    print("AUTH_URL:" + auth_url)
    sys.stdout.flush()

    if len(sys.argv) > 1:
        redirect = sys.argv[1]
        flow.fetch_token(authorization_response=redirect)
        creds = flow.credentials
        with open(TOKEN, 'wb') as f:
            pickle.dump(creds, f)
        print(f"Token saved to {TOKEN}")
        print(f"Expires: {creds.expiry}")
    else:
        print("\n1. Buka URL di atas di browser")
        print("2. Login & authorize")
        print("3. Copy full redirect URL (mulai http://localhost:8080/...)")
        print("4. Jalankan: python google_calendar_setup.py \"REDIRECT_URL\"")

if __name__ == '__main__':
    main()
