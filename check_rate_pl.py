import requests

from config import CONFIG_KOD_DOSTEPU_PL, CONFIG_URL_PL, CONFIG_ID_PL

# logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
# FILE_NAME, POSTAL_CODE = sys.argv

POSTAL_CODE = '02798'

XML_TREE = f"""
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ws="http://ws.alfaprojekt.com/">
    <soapenv:Header/>
    <soapenv:Body>
    <ws:pobierzDostepneUslugi>
    <accessCode>{CONFIG_KOD_DOSTEPU_PL}</accessCode>
    <postalCode>{POSTAL_CODE}</postalCode>
    </ws:pobierzDostepneUslugi>
    </soapenv:Body>
    </soapenv:Envelope>"""

response = requests.post(CONFIG_URL_PL, data=XML_TREE, verify=False)
print(response.content)
