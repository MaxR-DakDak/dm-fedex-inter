import requests
from config import DM_LOGIN


def get_order_data(value):
    url = f'https://192.168.0.100/json/shipments?name={value}'
    response = requests.get(url, auth=DM_LOGIN, verify=False)
    if response.status_code == 200:
        data = response.json()
        return data['collection']
    else:
        raise ValueError('Cant get order data!')


def get_companies_data():
    url = f'https://192.168.0.100/json/companies?nip=PL5252625009'
    response = requests.get(url, auth=DM_LOGIN, verify=False)
    if response.status_code == 200:
        data = response.json()
        return data['collection']
    else:
        raise ValueError('Cant get order data!')


def post_shipments_data(data):
    url = f'https://192.168.0.100/json/shipments'
    response = requests.post(url, data=data, auth=DM_LOGIN, verify=False)
    return response.status_code, response.text, response.url


def post_label_data(data):
    url = 'https://192.168.0.100/saveFile'
    response = requests.post(url, data=data, auth=DM_LOGIN, verify=False)
    return response.status_code, response.text, response.url


def get_label_data(file_name):
    url = f'https://192.168.0.100/loadFile?file_name={file_name}&file_type=shipment'
    response = requests.get(url, auth=DM_LOGIN, verify=False)
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        raise ValueError('Cant get data!')
