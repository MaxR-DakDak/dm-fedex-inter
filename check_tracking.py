import logging
import sys
from config import CONFIG_OBJ
from fedex.services.track_service import FedexTrackRequest

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

track = FedexTrackRequest(CONFIG_OBJ)

track.SelectionDetails.PackageIdentifier.Type = 'TRACKING_NUMBER_OR_DOORTAG'
track.SelectionDetails.PackageIdentifier.Value = '852426136339225'

# FedEx operating company or delete
del track.SelectionDetails.OperatingCompany

# print(track.client)
# print(track.SelectionDetails)
# print(track.ClientDetail)
# print(track.TransactionDetail)

track.send_request()
print(track.response)

# from fedex.tools.conversion import sobject_to_json
# print(sobject_to_json(track.response))

print("== Results ==")
for match in track.response.CompletedTrackDetails[0].TrackDetails:
    print("Tracking #: {}".format(match.TrackingNumber))
    if hasattr(match, 'TrackingNumberUniqueIdentifier'):
        print("Tracking # UniqueID: {}".format(match.TrackingNumberUniqueIdentifier))
    if hasattr(match, 'StatusDetail'):
        if hasattr(getattr(match, 'StatusDetail'), 'Description'):
            print("Status Description: {}".format(match.StatusDetail.Description))
        if hasattr(getattr(match, 'StatusDetail'), 'AncillaryDetails'):
            print("Status AncillaryDetails Reason: {}".format(match.StatusDetail.AncillaryDetails[-1].Reason))
            print("Status AncillaryDetails Description: {}"
                  "".format(match.StatusDetail.AncillaryDetails[-1].ReasonDescription))
    if hasattr(match, 'ServiceCommitMessage'):
        print("Commit Message: {}".format(match.ServiceCommitMessage))
    if hasattr(match, 'Notification'):
        print("Notification Severity: {}".format(match.Notification.Severity))
        print("Notification Code: {}".format(match.Notification.Code))
        print("Notification Message: {}".format(match.Notification.Message))
    print("")

    event_details = []
    if hasattr(match, 'Events'):
        for j in range(len(match.Events)):
            event_match = match.Events[j]
            event_details.append({'created': event_match.Timestamp, 'type': event_match.EventType,
                                  'description': event_match.EventDescription})

            if hasattr(event_match, 'StatusExceptionDescription'):
                event_details[j]['exception_description'] = event_match.StatusExceptionDescription

            print("Event {}: {}".format(j + 1, event_details[j]))
