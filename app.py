import datetime
import jwt
import os
import pathlib
import re
import requests
import urllib3
from dotenv import load_dotenv

# Hide insecure request warnings in the terminal
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Read environment variables from .env locally
env = pathlib.Path(".env")
if env.is_file():
    load_dotenv(dotenv_path=env)

# My API credentials
client_id = os.environ.get('client_id')
client_secret = os.environ.get('client_secret')
tech_acct_id = os.environ.get('tech_acct_id')
org_id = os.environ.get('org_id')
ims_exchange = os.environ.get("ims_exchange")
ims_host = os.environ.get("ims_host")
aa_scope = os.environ.get("aa_scope")
aa_api_base_url = os.environ.get("aa_api_base_url")
private_key = os.environ.get('private_key')
rsid = os.environ.get('rsid')
global_company_id = os.environ.get('global_company_id')


def get_jwt(scope):
    """Encodes AA API creds into a JWT token"""
    payload:dict = {
        "exp": datetime.datetime.utcnow() + datetime.timedelta(seconds=30), # expiration for JWT
        "iss": org_id,
        "sub": tech_acct_id,
        f"https://{ims_host}/s/{scope}": True,
        "aud": f"https://{ims_host}/c/{client_id}"
    }

    # Encode the payload & sign with private key
    return jwt.encode(payload, str.encode(private_key.replace("\\n","\n")), algorithm="RS256")

def get_access_token(jwt_token):
    """Requests and access token from Adobe for use in API calls"""
    access_payload:dict = {
        "client_id": client_id,
        "client_secret": client_secret,
        "jwt_token": jwt_token
    }

    # Send the JWT in exchange for an access token
    # I have disabled verification here due to firewall complications
    r = requests.post(
        ims_exchange, data=access_payload, verify=False
    )
    # this is the token I need to make AA API calls
    return r.json()["access_token"]


jwt_token = get_jwt(aa_scope)
access_token = get_access_token(jwt_token)

headers = {
    "accept": "application/json",
    "x-proxy-global-company-id": global_company_id,
    "x-api-key": client_id,
    "Authorization": f"Bearer {access_token}"
}

r = requests.get(f"https://analytics.adobe.io/api/{global_company_id}/dimensions?rsid={rsid}", headers=headers)
dimensions = r.json()
props = filter(lambda dimension: dimension.get('extraTitleInfo') is not None and "prop" in dimension.get('extraTitleInfo'), dimensions)
filtered_props = [prop for prop in props if "entry" not in prop['id'] and "exit" not in prop['id']]

# order props in numerical order
def order_nums(dimension):
    id = dimension.get('id')
    regex = r"\d+"
    return int(re.findall(regex,id).pop())

filtered_props.sort(key=order_nums)

# for prop in filtered_props:
    # print(prop)

    # returns:
    # {'id': 'variables/prop1', 'title': 'pagename', 'name': 'pagename', 'type': 'string', .....
    # {'id': 'variables/prop2', 'title': 'username', 'name': 'username', 'type': 'string', .....
    # {'id': 'variables/prop3', 'title': 'url', 'name': 'url', 'type': 'string', .....
    # etc etc
    # similar output for evars

evars = filter(lambda dimension: dimension.get('extraTitleInfo') is not None and "evar" in dimension.get('extraTitleInfo'), dimensions)
evars = list(evars)
evars.sort(key=order_nums)
m = requests.get(f"https://analytics.adobe.io/api/{global_company_id}/metrics?rsid={rsid}", headers=headers)
metrics = m.json()
events = list(filter(lambda event: event.get("extraTitleInfo") is not None and "event" in event.get("extraTitleInfo"), metrics))
events.sort(key=order_nums)


# for event in events:
    # print(event)

    # returns:
    # {'id': 'metrics/event1', 'title': 'Pageview', 'name': 'Pageview', 'type': 'int', 'extraTitleInfo': 'event1',....
    # {'id': 'metrics/event2', 'title': 'Login', 'name': 'Login', 'type': 'int', 'extraTitleInfo': 'event2', ....
    # {'id': 'metrics/event3', 'title': 'Click', 'name': 'Click', 'type': 'int', 'extraTitleInfo': 'event3', ....
    # etc etc


last_update = datetime.datetime.now() - datetime.timedelta(hours=4) # adjust for utc time of automation server

output = f"""
# Adobe Analytics Events and Dimensions
<br>
*Last Updated: {last_update.strftime("%x - %X")}*
<div id="variablesearch">
    <input name="search" placeholder="Search" value="">
</div>

## Report Suite: {rsid}
<hr>"""

output += """
### Props
| Number | Name | Description |
|----------|----------|----------|"""

for p in filtered_props:
    description = p.get('description')
    # descriptions come with weird formatting sometimes...
    if description:
        description = description.strip().replace("\r", " ").replace("\n", " ")
    id = p.get('id').replace("variables/", "")
    name = p.get('name')
    output += f"\n|{id} | {name} | {description}"

# remember to add spacing between elements in markdown
output += "\n"
output += """

### Evars

| Number | Name | Description |
|----------|----------|----------|"""

for e in evars:
    description = e.get('description')
    if description:        
        description = description.strip().replace("\r", " ").replace("\n", " ")
    id = e.get('id').replace("variables/", "")
    name = e.get('name')
    output += f"\n|{id}|{name}|{description}|"

output += "\n"
output += """

### Events

| Number | Name | Description |
|----------|----------|----------|"""

for e in list(events):
    description = e.get('description')
    if description:        
        description = description.strip().replace("\r", " ").replace("\n", " ")
    id = e.get('id').replace("metrics/", "")
    name = e.get('name')
    output += f"\n|{id}|{name}|{description}|"

with open('adobevargrid.md', 'w') as f:
    f.write(output)