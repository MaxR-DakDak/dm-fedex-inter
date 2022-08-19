import re
import json
import os
import sys
import base64
import logging
import binascii
import requests
from unidecode import unidecode
import services
import datetime
from PyPDF2 import PdfFileMerger
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup as Soup
from config import CONFIG_KOD_DOSTEPU_PL, CONFIG_URL_PL, CONFIG_ID_PL, CONFIG_COURUER_ID, GENERATE_IMAGE_TYPE_PL

# logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
SEND_DATE = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
FILE_NAME, ORDER_NAME = sys.argv


try:
    checkerrors = False

    # GET ORDER DATA
    dm_data = services.get_companies_data()[0]
    order_data = services.get_order_data(ORDER_NAME)[0]
    json_packages = json.loads(order_data["shipment_packages_details"])
    total_package_insurance = 0
    total_package_content = []
    for package_insurance in json_packages:
        total_package_content.append(package_insurance['contents'])
        total_package_insurance = int(total_package_insurance) + int(package_insurance['insurance'])
    phone = order_data['delivery_phone']
    if order_data['delivery_phone'] == '':
        phone = order_data['phone']
    its_company = 0
    if order_data['company_name'] != '':
        its_company = 1
    ORDER_ID = order_data['id']
    name = re.findall(r'\w+', (unidecode(order_data['delivery_name'])))[0]
    surname = (str(order_data['delivery_name'].split(' ', 1)[1:])[2:-2])

    # CREATE XML REQUEST
    XML_TREE = f"""
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ws="http://ws.alfaprojekt.com/"><soapenv:Header/><soapenv:Body>
    <ws:zapiszListV2><accessCode>{CONFIG_KOD_DOSTEPU_PL}</accessCode><shipmentV2><nrExt></nrExt>
    <paymentForm>G</paymentForm><shipmentType>K</shipmentType><payerType>2</payerType>
    <sender><senderId>{CONFIG_ID_PL}</senderId></sender>
    
    <receiver>
    <receiverId></receiverId><addressDetails><isCompany>{its_company}</isCompany><companyName>{order_data['company_name']}</companyName><vatNo></vatNo>
    <name>{name}</name><surname>{surname}</surname><nrExt></nrExt>
    <city>{unidecode(order_data['delivery_city'])}</city><postalCode>{unidecode(order_data['delivery_postal_code'])}</postalCode><countryCode></countryCode>
    <street>{unidecode(order_data['delivery_street'])}</street><homeNo>{unidecode(order_data['delivery_housenr'])}</homeNo><localNo></localNo></addressDetails>
    <contactDetails><name>{unidecode(order_data['primary_contact'])}</name><surname></surname>
    <phoneNo>{phone}</phoneNo><email>{order_data['email']}</email></contactDetails>
    </receiver>
    
    <proofOfDispatch>
    <senderSignature>{dm_data['name']}</senderSignature>
    <courierId>{CONFIG_COURUER_ID}</courierId>
    <sendDate>{SEND_DATE}</sendDate>
    </proofOfDispatch>
    
    <insurance><insuranceValue>{total_package_insurance}</insuranceValue><contentDescription>Sprzęt komputerowy</contentDescription></insurance>
    
    <cod><codType></codType><codValue></codValue><bankAccountNumber></bankAccountNumber></cod>
    <additionalServices><!--Zero or more repetitions:--><service><serviceId></serviceId><!--Zero or more repetitions:-->
    <serviceArguments><!--Zero or more repetitions:--><serviceArgument><code></code><argValue></argValue></serviceArgument></serviceArguments></service>
    </additionalServices><parcels></parcels><remarks></remarks><mpk></mpk></shipmentV2></ws:zapiszListV2></soapenv:Body></soapenv:Envelope>"""

    xml = ET.fromstring(XML_TREE)

    # ADD PACKAGE
    for package in json_packages:
        xml.find('.//parcels').append(ET.fromstring(
            f"""<parcel><waybill></waybill><type>PC</type>
            <weight>{package['weight']}</weight>
            <dim1>{package['dimmensions']['width']}</dim1>
            <dim2>{package['dimmensions']['height']}</dim2>
            <dim3>{package['dimmensions']['length']}</dim3>
            <shape>0</shape><dimWeight></dimWeight><nrExtPp></nrExtPp></parcel>"""))

    # MASTER BOX
    response = requests.post(CONFIG_URL_PL, data=ET.tostring(xml), verify=False)
    box_id = []
    if response.status_code == 200:
        soup = Soup(response.content, 'xml')
        for waybill in soup.find_all('waybill'):
            box_id.append(waybill.get_text())
    else:
        soup = Soup(response.content, 'xml')
        err = soup.error.get_text()
        raise Exception(err)

    MASTER_BOX = box_id[0]
    OTHER_BOX = box_id[1:]

    # GET LABEL FOR MASTER AND OTHER BOXES
    for index, box in enumerate(OTHER_BOX, start=1):
        for label_format in GENERATE_IMAGE_TYPE_PL:
            GET_LABEL = f"""
            <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ws="http://ws.alfaprojekt.com/"><soapenv:Header/><soapenv:Body>
            <ws:wydrukujEtykietePaczki>
            <kodDostepu>{CONFIG_KOD_DOSTEPU_PL}</kodDostepu>
            <numerPaczki>{box}</numerPaczki>
            <format>{label_format}</format>
            </ws:wydrukujEtykietePaczki>
            </soapenv:Body></soapenv:Envelope>"""

            request_label = requests.post(CONFIG_URL_PL, data=GET_LABEL, verify=False)
            print(request_label.content)
            soup = Soup(request_label.content, 'xml')
            ascii_label_data = soup.etykietaBajty.get_text()

            if label_format == 'ZPL200':
                label_format = 'ZPLII'
            label_binary_data = binascii.a2b_base64(ascii_label_data)
            out_path = os.path.join(f'./labels_pl/{MASTER_BOX}', 'label_%s.%s' % (box, label_format.lower()))
            if not os.path.exists(f'./labels_pl/{MASTER_BOX}'):
                os.makedirs(f'./labels_pl/{MASTER_BOX}')

            print(f"Writing to file {out_path}")
            out_file = open(out_path, 'wb')
            out_file.write(label_binary_data)
            out_file.close()

    # MERGE PDF AND ZPL
    source_dir = f'./labels_pl/{MASTER_BOX}/'
    if not os.path.exists(f'./labels_pl/{MASTER_BOX}' + '/master/'):
        os.makedirs(f'./labels_pl/{MASTER_BOX}' + '/master/')
    with open(source_dir + f'/master/masterlabel_{MASTER_BOX}.zplii', "a") as master_file:
        for item in os.listdir(source_dir):
            if item.endswith('zplii'):
                with open(source_dir + item, "r") as file:
                    master_file.writelines(file)
    with open(source_dir + f'/master/masterlabel_{MASTER_BOX}.pdf', "wb") as master_file:
        merger = PdfFileMerger()
        for item in os.listdir(source_dir):
            if item.endswith('pdf'):
                merger.append(source_dir + item)
        merger.write(master_file)

    # POST PDF AND ZPL
    with open(source_dir + f'/master/masterlabel_{MASTER_BOX}.zplii', "rb") as master_file:
        encoded_string = base64.b64encode(master_file.read())
        data = {"file_name": f"fedex/{ORDER_NAME}.zplii", "file": str(encoded_string)[2:-1], "file_type": "shipment"}
        postdata = services.post_label_data(data)
    with open(source_dir + f'/master/masterlabel_{MASTER_BOX}.pdf', "rb") as master_file:
        encoded_string = base64.b64encode(master_file.read())
        data = {"file_name": f"fedex/{ORDER_NAME}.pdf", "file": str(encoded_string)[2:-1], "file_type": "shipment"}
        postdata = services.post_label_data(data)

except Exception as exception_err:
    checkerrors = True
    print(exception_err)

finally:
    print('DONE!')
    if checkerrors:
        data = {"id": ORDER_ID, "shipment_error": exception_err}
        posterr = services.post_shipments_data(data)
    else:
        data = {"id": ORDER_ID, "shipment_finished": 210}
        poststatus = services.post_shipments_data(data)
