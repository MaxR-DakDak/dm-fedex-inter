import base64
import binascii
import json
import logging
import os
import shutil
import sys
import zpl
from PIL import Image
import services
import glob
import img2pdf as img2pdf
from config import CONFIG_OBJ
from fedex.services.ship_service import FedexProcessShipmentRequest
from unidecode import unidecode

# logging.basicConfig(stream=sys.stdout, level=logging.INFO)
FILE_NAME, ORDER_NAME = sys.argv

try:
    checkerrors = False

    # CREATE PACKAGE
    def create_package(sequence_number, package_weight_value, package_weight_units, physical_packaging="BOX"):
        package_weight = shipment.create_wsdl_object_of_type('Weight')
        package_weight.Value = package_weight_value
        package_weight.Units = package_weight_units

        package = shipment.create_wsdl_object_of_type('RequestedPackageLineItem')
        package.PhysicalPackaging = physical_packaging
        package.Weight = package_weight
        package.SequenceNumber = sequence_number
        return package

    # GET DREAMMACHINES DATA
    dm_data = services.get_companies_data()[0]

    # GET ORDER DATA
    data = services.get_order_data(ORDER_NAME)[0]
    ORDER_ID = data['id']
    json_packages = json.loads(data["shipment_packages_details"])
    length_packages = len(json_packages)
    total_package_weight = 0
    for package_weight in json_packages:
        total_package_weight = int(total_package_weight) + int(package_weight['weight'])
    total_package_insurance = 0
    for package_insurance in json_packages:
        total_package_insurance = int(total_package_insurance) + int(package_insurance['insurance'])
    json_order = json.loads(data["json"])

    # CREATE SHIPMENT
    shipment = FedexProcessShipmentRequest(CONFIG_OBJ)
    shipment.RequestedShipment.DropoffType = 'REGULAR_PICKUP'
    shipment.RequestedShipment.ServiceType = 'INTERNATIONAL_PRIORITY'
    shipment.RequestedShipment.PackagingType = 'YOUR_PACKAGING'

    # SENDER
    shipment.RequestedShipment.Shipper.Contact.CompanyName = unidecode(dm_data['name'])
    shipment.RequestedShipment.Shipper.Contact.PhoneNumber = dm_data['phone']
    shipment.RequestedShipment.Shipper.Address.StreetLines = f"{unidecode(dm_data['adres_street'])} {dm_data['adres_house']}"
    shipment.RequestedShipment.Shipper.Address.City = unidecode(dm_data['city'])
    shipment.RequestedShipment.Shipper.Address.PostalCode = dm_data['postal']
    shipment.RequestedShipment.Shipper.Address.CountryCode = 'PL'
    shipment.RequestedShipment.Recipient.Address.Residential = False

    # RECIPIENT
    shipment.RequestedShipment.Recipient.Contact.CompanyName = unidecode(data['company_name'])
    shipment.RequestedShipment.Recipient.Contact.PersonName = unidecode(data['delivery_name'])
    if data['delivery_phone'] == '':
        shipment.RequestedShipment.Recipient.Contact.PhoneNumber = data['phone']
    else:
        shipment.RequestedShipment.Recipient.Contact.PhoneNumber = data['delivery_phone']
    shipment.RequestedShipment.Recipient.Address.CountryCode = data['delivery_country']
    shipment.RequestedShipment.Recipient.Address.StateOrProvinceCode = data['delivery_state']
    shipment.RequestedShipment.Recipient.Address.City = unidecode(data['delivery_city'])
    shipment.RequestedShipment.Recipient.Address.StreetLines = unidecode(data['delivery_street'])
    shipment.RequestedShipment.Recipient.Address.PostalCode = data['delivery_postal_code']
    shipment.RequestedShipment.Recipient.Address.Residential = False
    shipment.RequestedShipment.EdtRequestType = 'NONE'

    # ACCOUNT?
    shipment.RequestedShipment.ShippingChargesPayment.PaymentType = 'SENDER'
    shipment.RequestedShipment.ShippingChargesPayment.Payor.ResponsibleParty.AccountNumber = CONFIG_OBJ.account_number

    # PACKAGE
    package1 = create_package(sequence_number=1, package_weight_value=json_packages[0]['weight'], package_weight_units="KG", physical_packaging="BOX")
    shipment.RequestedShipment.RequestedPackageLineItems = [package1]
    shipment.RequestedShipment.PackageCount = length_packages
    shipment.RequestedShipment.TotalWeight.Units = "KG"
    shipment.RequestedShipment.TotalWeight.Value = total_package_weight

    # INTERNATIONAL
    if data['delivery_country'] != 'PL':
        shipment.RequestedShipment.CustomsClearanceDetail.CustomsValue.Currency = 'PLN'
        shipment.RequestedShipment.CustomsClearanceDetail.CustomsValue.Amount = total_package_insurance
        shipment.RequestedShipment.CustomsClearanceDetail.DutiesPayment.PaymentType = 'RECIPIENT'

        for index, product in enumerate(json_order):
            if product['item_name'] == 'Transport':
                continue
            index = shipment.create_wsdl_object_of_type('Commodity')
            index.Name = product['item_name']
            index.NumberOfPieces = product['item_quantity']
            index.Description = product['item_name']
            index.CountryOfManufacture = 'CN'
            index.Quantity = product['item_quantity']
            index.QuantityUnits = 'EA'
            index.Weight.Units = "KG"
            index.Weight.Value = 0
            index.UnitPrice.Currency = 'PLN'
            index.UnitPrice.Amount = product['item_item_netto']
            shipment.RequestedShipment.CustomsClearanceDetail.Commodities.append(index)
    else:
        print('POLAND')

    # TOTAL INSURED
    shipment.RequestedShipment.TotalInsuredValue.Amount = total_package_insurance
    shipment.RequestedShipment.TotalInsuredValue.Currency = "PLN"

    # LABEL
    GENERATE_IMAGE_TYPE = 'PNG'
    shipment.RequestedShipment.LabelSpecification.LabelFormatType = 'COMMON2D'
    shipment.RequestedShipment.LabelSpecification.ImageType = GENERATE_IMAGE_TYPE
    # PAPER_4X6 FOR PNG
    # STOCK_4X6 FOR ZPL
    shipment.RequestedShipment.LabelSpecification.LabelStockType = 'PAPER_4X6'

    # REQUEST
    shipment.send_validation_request()
    shipment.send_request()

    # MASTER BOX TRACKING
    master_label = shipment.response.CompletedShipmentDetail.CompletedPackageDetails[0]
    master_tracking_number = master_label.TrackingIds[0].TrackingNumber
    master_tracking_id_type = master_label.TrackingIds[0].TrackingIdType
    master_tracking_form_id = master_label.TrackingIds[0].FormId
    print("\nMaster Tracking_number:", master_tracking_number)

    # PRINT
    print("HighestSeverity: {}".format(shipment.response.HighestSeverity))
    print("Tracking: {}""".format(shipment.response.CompletedShipmentDetail.CompletedPackageDetails[0].TrackingIds[0].TrackingNumber))
    CompletedPackageDetails = shipment.response.CompletedShipmentDetail.CompletedPackageDetails[0]

    # MASTER BOX
    ascii_label_data = shipment.response.CompletedShipmentDetail.CompletedPackageDetails[0].Label.Parts[0].Image
    label_binary_data = binascii.a2b_base64(ascii_label_data)
    out_path = os.path.join(f'./label/{master_tracking_number}', 'label_%s.%s' % (master_tracking_number, GENERATE_IMAGE_TYPE.lower()))
    out_path_zpl = os.path.join(f'./label/{master_tracking_number}', 'label_%s.zplii' % master_tracking_number)
    if not os.path.exists(f'./label/{master_tracking_number}'):
        os.makedirs(f'./label/{master_tracking_number}')

    print("Writing to file {}".format(out_path))
    out_file = open(out_path, 'wb')
    out_file.write(label_binary_data)
    out_file.close()

    l = zpl.Label(152.4, 101.6, 8)
    l.origin(0, 0)
    image_width = 99
    l.write_graphic(Image.open(out_path), image_width)
    l.endorigin()

    out_file = open(out_path_zpl, 'w')
    out_file.write(l.dumpZPL())
    out_file.close()

    # CHILD BOX
    print("\nChild labels:")
    child_package_list = []
    for index_package, package in enumerate(json_packages[1:], start=2):
        index_package = create_package(sequence_number=index_package, package_weight_value=package['weight'], package_weight_units="KG", physical_packaging="BOX")
        child_package_list.append(index_package)

    for child_package in child_package_list:
        shipment.RequestedShipment.RequestedPackageLineItems = [child_package]
        shipment.RequestedShipment.MasterTrackingId.TrackingNumber = master_tracking_number
        shipment.RequestedShipment.MasterTrackingId.TrackingIdType = master_tracking_id_type
        shipment.RequestedShipment.MasterTrackingId.FormId = master_tracking_form_id

        shipment.send_request()

        for label in shipment.response.CompletedShipmentDetail.CompletedPackageDetails:
            print("\nChild Tracking_number:", label.TrackingIds[0].TrackingNumber)
            ascii_label_data = label.Label.Parts[0].Image
            label_binary_data = binascii.a2b_base64(ascii_label_data)
            out_path = os.path.join(f'./label/{master_tracking_number}', 'label_%s.%s' % (label.TrackingIds[0].TrackingNumber, GENERATE_IMAGE_TYPE.lower()))
            out_path_zpl = os.path.join(f'./label/{master_tracking_number}', 'label_%s.zplii' % label.TrackingIds[0].TrackingNumber,)
            print("Writing to file {}".format(out_path))
            out_file = open(out_path, 'wb')
            out_file.write(label_binary_data)
            out_file.close()

            l = zpl.Label(152.4, 101.6, 8)
            l.origin(0, 0)
            image_width = 99
            l.write_graphic(Image.open(out_path), image_width)
            l.endorigin()

            out_file = open(out_path_zpl, 'w')
            out_file.write(l.dumpZPL())
            out_file.close()

    # MERGE ZPL LABEL
    source_dir = f'./label/{master_tracking_number}/'
    if not os.path.exists(f'./label/{master_tracking_number}'+'/master/'):
        os.makedirs(f'./label/{master_tracking_number}'+'/master/')
    with open(source_dir + f'/master/masterlabel_{master_tracking_number}.zplii', "a") as master_file:
        for item in os.listdir(source_dir):
            if item.endswith('zplii'):
                with open(source_dir + item, "r") as file:
                    master_file.writelines(file)
    with open(source_dir + f'/master/masterlabel_{master_tracking_number}.pdf', "wb") as master_file:
        master_file.write(img2pdf.convert(glob.glob(f"{source_dir}/*.png")))

    # POST FILE ZPL AND PDF
    with open(source_dir + f'/master/masterlabel_{master_tracking_number}.zplii', "rb") as master_file:
        encoded_string = base64.b64encode(master_file.read())
        data = {"file_name": f"fedex/{ORDER_NAME}.zplii", "file": str(encoded_string)[2:-1], "file_type": "shipment"}
        postdata = services.post_label_data(data)
    with open(source_dir + f'/master/masterlabel_{master_tracking_number}.pdf', "rb") as master_file:
        encoded_string = base64.b64encode(master_file.read())
        data = {"file_name": f"fedex/{ORDER_NAME}.pdf", "file": str(encoded_string)[2:-1], "file_type": "shipment"}
        postdata = services.post_label_data(data)

    # shutil.rmtree(source_dir)

except Exception as err:
    checkerrors = True
    exception_err = err
    print(exception_err)

finally:
    print('DONE')
    if checkerrors:
        print(exception_err)
        data = {"id": ORDER_ID, "shipment_error": exception_err}
        posterr = services.post_shipments_data(data)
    else:
        data = {"id": ORDER_ID, "shipment_finished": 210}
        posterr = services.post_shipments_data(data)
