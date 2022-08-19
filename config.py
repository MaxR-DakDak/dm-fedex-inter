from fedex.config import FedexConfig
from requests.auth import HTTPBasicAuth

CONFIG_OBJ = FedexConfig(key='test',
                         password='test',
                         account_number='test',
                         meter_number='test',
                         use_test_server=True)

CONFIG_URL_PL = 'https://test.poland.fedex.com/fdsWs/IklServicePort?WSDL'
CONFIG_KOD_DOSTEPU_PL = 'test'
CONFIG_ID_PL = 'test'
CONFIG_COURUER_ID = 'test'
GENERATE_IMAGE_TYPE_PL = ['PDF', 'ZPL200']

DM_LOGIN = HTTPBasicAuth('test', 'test')
