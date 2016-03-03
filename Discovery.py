from Ehop import Ehop
import json

class Discoverer(object):
    """An application disc"""


    def __init__(self, apikey='', host='', lookback=-86400000):
        self.apikey   = apikey
        self.host     = host

        self.client   = Ehop(self.apikey, self.host)
        self.lookback = lookback

    def get_devices_by_type(self, type):

        query = 'devices?' +                                \
                'limit=0&' +                                \
                'search_type=type&' +                       \
                'value='+ type + '&' +                      \
                'active_from=' + str(self.lookback) + '&' + \
                'active_until=0'


        return json.loads(self.client.api_request('GET',
                                       query))

    def get_device_metrics(self, device_id, metric_category, metric):

        body = {
                    "cycle": "auto",
                    "from": self.lookback,
                    "metric_category": metric_category.split('.')[2],
                    "metric_specs": [{"name": metric}],
                    "object_ids": [device_id],
                    "object_type": "device",
                    "until": 0
                }

        response = json.loads(self.client.api_request('POST',
                                                      'metrics/total',
                                                      json.dumps(body)))


        return response['stats'][0]['values'][0]

    def tag_device(self, device_id, tag_id):
        path = 'tags/'+ str(tag_id) + '/devices/' + str(device_id)
        self.client.api_request('POST',path)

    def tag_by_metric_identifier(self, metric_category, metric, key, tag):

        # Check that tag exists
        tag_id      = self._make_tag(tag)

        # Determine the device type required for the metric category
        device_type = self._process_metric_category(metric_category)

        # Get a list of all devices of that device type
        devices     = self.get_devices_by_type(device_type)

        # Populate device list with the metric
        for i in range(0, len(devices)):
            device_id = devices[i]['id']
            devices[i]['device_metrics'] = self.get_device_metrics(device_id, metric_category, metric)

        # From this point, functionality can diverge.
        # A) Find known identifiers and tag accordingly.
        # B) Group all detail metrics and determine possible identifiers
        # This function will implement (A)

        for device in devices:
            if (type(device['device_metrics']) is not list):
                raise ValueError('Expecting list (Topnset)', device['device_metrics'])

            for metric in device['device_metrics']:
                if (key in metric['key']['str']):
                    self.tag_device(device['id'],tag_id)


    def _make_tag(self, tag):
        # Check that tag exist

        tags = json.loads(self.client.api_request('GET','tags'))
        for t in tags:
            if (t['name'] == tag):
                return t['id']

        # Tag does not exist
        body = {"name": tag}
        self.client.api_request('POST','tags', json.dumps(body))

        tags = json.loads(self.client.api_request('GET','tags'))
        for t in tags:
            if (t['name'] == tag):
                return t['id']

    def _process_metric_category(self, metric_category):
        # EH metrics take the form extrahop.[object_type].[metric_category]
        metric_components = metric_category.split('.')

        if (metric_components[0] != 'extrahop'):
            raise ValueError('Unexpected metric scope. Must follow form extrahop.device.[metric_category]',metric_category)
        elif (metric_components[1] != 'device'):
            raise ValueError('Tagging occurs at the device level. Must follow form extrahop.device.[metric_category]',metric_category)

        mc = metric_components[2].split('_')
        for i in range(0,len(mc)):
            # if mc[i] is server or client, the previous index holds the protocol
            if (mc[i] == 'server' or mc[i] == 'client'):
                return mc[i-1] + '_' + mc[i]

        raise ValueError('Unexpected metric category. Does not contain "server" or "client"',metric_category)
