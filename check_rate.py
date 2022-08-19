import datetime
import sys
import services
from config import CONFIG_OBJ
from fedex.services.availability_commitment_service import FedexAvailabilityCommitmentRequest
from fedex.services.rate_service import FedexRateServiceRequest

# logging.basicConfig(stream=sys.stdout, level=logging.INFO)
FILE_NAME, DESTINATION_POSTAL, DESTINATION_COUNTRY, DESTINATION_POSTAL_STATE, WEIGHT = sys.argv
# DESTINATION_POSTAL_STATE = 'any'
# DESTINATION_COUNTRY = 'de'
# DESTINATION_POSTAL = '12167'
if DESTINATION_POSTAL_STATE == 'any':
    DESTINATION_POSTAL_STATE = ''

# dm_data = services.get_companies_data()[0]
# dm_data['postal']
# dm_data['co_code']

def get_available_service():
    avc_request = FedexAvailabilityCommitmentRequest(CONFIG_OBJ)

    avc_request.Origin.PostalCode = '02-798'
    avc_request.Origin.CountryCode = 'PL'

    avc_request.Destination.PostalCode = DESTINATION_POSTAL
    avc_request.Destination.CountryCode = DESTINATION_COUNTRY

    avc_request.ShipDate = datetime.date.today()

    avc_request.send_request()
    avb_service = []

    for option in avc_request.response.Options:
        if hasattr(option, 'Service'):
            avb_service.append(option.Service)

    return avb_service


def get_rate(avb_service):
    rate_request = FedexRateServiceRequest(CONFIG_OBJ)
    rate_request.RequestedShipment.DropoffType = 'REGULAR_PICKUP'
    rate_request.RequestedShipment.ServiceType = avb_service
    rate_request.RequestedShipment.PackagingType = 'YOUR_PACKAGING'

    rate_request.RequestedShipment.Shipper.Address.StateOrProvinceCode = ''
    rate_request.RequestedShipment.Shipper.Address.PostalCode = '02-798'
    rate_request.RequestedShipment.Shipper.Address.CountryCode = 'PL'
    rate_request.RequestedShipment.Shipper.Address.Residential = False

    rate_request.RequestedShipment.Recipient.Address.StateOrProvinceCode = DESTINATION_POSTAL_STATE
    rate_request.RequestedShipment.Recipient.Address.PostalCode = DESTINATION_POSTAL
    rate_request.RequestedShipment.Recipient.Address.CountryCode = DESTINATION_COUNTRY
    rate_request.RequestedShipment.Shipper.Address.Residential = False
    rate_request.RequestedShipment.EdtRequestType = 'ALL'

    rate_request.RequestedShipment.ShippingChargesPayment.PaymentType = 'SENDER'

    package1_weight = rate_request.create_wsdl_object_of_type('Weight')
    package1_weight.Value = WEIGHT
    package1_weight.Units = "KG"
    package1 = rate_request.create_wsdl_object_of_type('RequestedPackageLineItem')
    package1.Weight = package1_weight
    package1.PhysicalPackaging = 'BOX'
    package1.GroupPackageCount = 1
    rate_request.add_package(package1)

    rate_request.send_request()

    for service in rate_request.response.RateReplyDetails:
        for rate_detail in service.RatedShipmentDetails:
            return (f"{service.ServiceType}: Net FedEx Charge "
                    f"{rate_detail.ShipmentRateDetail.TotalNetFedExCharge.Currency}"
                    f"{rate_detail.ShipmentRateDetail.TotalNetFedExCharge.Amount}")


print(get_available_service())
print(get_rate('INTERNATIONAL_ECONOMY'))
