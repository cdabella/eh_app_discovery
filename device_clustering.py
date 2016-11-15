#!/usr/bin/env python2.7

import json
import os
import sys
import operator

from Discovery import Discoverer
from PIL import Image,ImageDraw
from math import sqrt

def main():
    print_startup_message()

    raw_data = get_device_data()
    raw_file_name = raw_input('\nFile name for raw data: ')
    store_json_file(discoverer.devices_cache, raw_file_name)

    device_list = etl(raw_data)
    print "Starting cluster analysis"
    clust = hcluster(device_list)

    jpg_name = raw_input('\nFile name for dendrogram JPEG: ')
    drawdendrogram(clust,jpeg=jpg_name)


def create_discoverer(host=None, apikey=None, lb=0):
    if host == None or apikey == None or lb == 0:
        host   = raw_input('ExtraHop hostname or IP: ')
        apikey = raw_input('API key: ')
        lb = raw_input('Lookback (in ms): ')
        print ''
        if (lb == ''):
            lb = 0
        else:
            lb = -1 * int(lb)
    return Discoverer(apikey,host,lookback=lb)

def get_device_data(host=None, apikey=None, lookback=0):
    discoverer = create_discoverer(host, apikey, lookback)
    discoverer.load_all_active_devices_into_cache()

    discoverer.filter_cached_devices()

    discoverer.add_device_metrics_to_cache('extrahop.device.app','bytes_in')
    discoverer.add_device_metrics_to_cache('extrahop.device.app','bytes_out')
    discoverer.add_device_metrics_to_cache('extrahop.device.net_detail','bytes_in')
    discoverer.add_device_metrics_to_cache('extrahop.device.net_detail','bytes_out')

    return discoverer.devices_cache

def store_json_file(data, file_name):
    with open(file_name, 'w') as outfile:
        json.dump(data, outfile)

def load_json_file(path=''):
    if path == '':
        path = raw_input('Path of data file (without quotes): ')

    assert os.path.exists(path), "No file found at " + str(path)

    with open(path) as data_file:
        try:
            print 'Attemping to load data file ' + path
            data = json.load(data_file)
        except:
            print 'Loading data file failed'
            raise

    return data

def flatten_count_metric(metric):
    if metric == []:
        return {}

    assert metric['vtype'] == 'count'

    if metric['key']['key_type'] == 'string':
        key = metric['key']['str']
    elif metric['key']['key_type'] == 'ipaddr':
        key = metric['key']['addr']
    else:
        print 'Unknown key_type: ' + metric['key']['key_type']

    return {key : metric['value']}

def etl(raw_data):
    print 'Performing ETL against raw data'
    etl_data = []
    for raw_device in raw_data:
        oid = raw_device['id']
        ipaddr = raw_device['ipaddr4']
        name = raw_device['display_name']
        metrics = {}

        for metric_category in raw_device['device_metrics']:

            for metric in raw_device['device_metrics'][metric_category]:
                flat_entries = {}

                # Flatten every metric into key:value pairs
                for entry in raw_device['device_metrics'][metric_category][metric]:
                    flat_entries.update(flatten_count_metric(entry))

                if flat_entries == {}:
                    continue

                # Create sorted list of tuples from dict
                # Top N entries for the metric
                # TODO likely need to tune
                sorted_flat_entries = sorted(flat_entries.items(), key=operator.itemgetter(1))[:20]

                metrics[metric_category+':'+metric] = dict(sorted_flat_entries)

        # Ignore devices which don't have inbound/outbound peers/protocols
        if len(metrics) != 4:
            continue

        etl_data.append(device(oid, ipaddr, name, metrics))

    return etl_data

def distance(device1, device2):
    # Get the list of shared_items
    sum_of_square = 0
    shared_entry = False
    for metric in device1.metrics:

        for entry in device1.metrics[metric]:
            if entry not in device2.metrics[metric]:
                device2.metrics[metric][entry] = 0
        for entry in device2.metrics[metric]:
            if entry not in device1.metrics[metric]:
                device1.metrics[metric][entry] = 0

        sum_of_square += sum(map(lambda entry: pow(device1.metrics[metric][entry]-device2.metrics[metric][entry], 2), device1.metrics[metric]))

    return 1.0 - 10.0**8/(10.0**8 + sqrt(sum_of_square))


class bicluster:
    def __init__(self,device,left=None,right=None,distance=0.0,id=None):
        self.left = left
        self.right = right
        self.device = device
        self.id = id
        self.distance = distance

class device:
    def __init__(self, oid, ipaddr, name, metrics):
        self.oid = oid
        self.ipaddr = ipaddr
        self.name = name
        self.metrics = metrics
    def __str__(self):
        return str(self.oid)+':'+self.ipaddr + ' ' + json.dumps(self.metrics)

def merge_devices(device1, device2):
    metrics = {}
    for metric in device1.metrics:
        metrics[metric] = {}
        for entry in device1.metrics[metric]:
            if entry not in device2.metrics[metric]:
                metrics[metric][entry] =  device1.metrics[metric][entry] / 2.0
            else:
                metrics[metric][entry] = (device1.metrics[metric][entry] + \
                                          device2.metrics[metric][entry]) / 2.0
        # Loop through device2 to find metrics not in device1
        for entry in device2.metrics[metric]:
            if entry not in device1.metrics[metric]:
                metrics[metric][entry] =  device2.metrics[metric][entry] / 2.0

    return device(-1,'0.0.0.0','branch', metrics)


def hcluster(devices, distance=distance):
    distances = {}
    currentclustid = -1

  # Clusters are initially just the devices
    clust = [bicluster(devices[i], id=i) for i in range(len(devices))]

    while len(clust) > 1:
        lowestpair = (0, 1)
        closest = distance(clust[0].device, clust[1].device)

    # loop through every pair looking for the smallest distance
        for i in range(len(clust)):
            for j in range(i + 1, len(clust)):
        # distances is the cache of distance calculations
                if (clust[i].id, clust[j].id) not in distances:
                    distances[(clust[i].id, clust[j].id)] = \
                        distance(clust[i].device, clust[j].device)

                d = distances[(clust[i].id, clust[j].id)]

                if d < closest:
                    closest = d
                    lowestpair = (i, j)


                _print_status_bar(i,j,len(clust))

    # calculate the average of the two clusters
        merged_device = merge_devices(clust[lowestpair[0]].device, clust[lowestpair[1]].device)

    # create the new cluster
        newcluster = bicluster(merged_device, left=clust[lowestpair[0]],
                               right=clust[lowestpair[1]], distance=closest,
                               id=currentclustid)

    # cluster ids that weren't in the original set are negative
        currentclustid -= 1
        del clust[lowestpair[1]]
        del clust[lowestpair[0]]
        clust.append(newcluster)

    return clust[0]


def printclust(clust, n=0):
  # indent to make a hierarchy layout
    for i in range(n):
        print ' ',
    if clust.id < 0:
    # negative id means that this is branch
        print '-'
    else:
    # positive id means that this is an endpoint
        print clust.device.ipaddr

  # now print the right and left branches
    if clust.left != None:
        printclust(clust.left, n=n + 1)
    if clust.right != None:
        printclust(clust.right, n=n + 1)


def getheight(clust):
  # Is this an endpoint? Then the height is just 1
    if clust.left == None and clust.right == None:
        return 1

  # Otherwise the height is the same of the heights of
  # each branch
    return getheight(clust.left) + getheight(clust.right)


def getdepth(clust):
  # The distance of an endpoint is 0.0
    if clust.left == None and clust.right == None:
        return 0

  # The distance of a branch is the greater of its two sides
  # plus its own distance
    return max(getdepth(clust.left), getdepth(clust.right)) + clust.distance


def drawdendrogram(clust, jpeg='clusters.jpg'):
  # height and width
    h = getheight(clust) * 20
    w = 2000
    pad = 200
    depth = getdepth(clust)

  # width is fixed, so scale distances accordingly
    scaling = float(w - 150) / depth

  # Create a new image with a white background
    img = Image.new('RGB', (w + pad, h), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    draw.line((0, h / 2, 10, h / 2), fill=(255, 0, 0))

  # Draw the first node
    drawnode(draw, clust, 10, h / 2, scaling)
    img.save(jpeg, 'JPEG')


def drawnode(draw, clust, x, y, scaling):
    if clust.id < 0:
        h1 = getheight(clust.left) * 20
        h2 = getheight(clust.right) * 20
        top = y - (h1 + h2) / 2
        bottom = y + (h1 + h2) / 2
    # Line length
        ll = clust.distance * scaling
    # Vertical line from this cluster to children
        draw.line((x, top + h1 / 2, x, bottom - h2 / 2), fill=(255, 0, 0))

    # Horizontal line to left item
        draw.line((x, top + h1 / 2, x + ll, top + h1 / 2), fill=(255, 0, 0))

    # Horizontal line to right item
        draw.line((x, bottom - h2 / 2, x + ll, bottom - h2 / 2), fill=(255, 0,
                  0))

    # Call the function to draw the left and right nodes
        drawnode(draw, clust.left,  x + ll, top + h1 / 2,    scaling)
        drawnode(draw, clust.right, x + ll, bottom - h2 / 2, scaling)
    else:
    # If this is an endpoint, draw the item label
        draw.text((x + 5, y - 7), clust.device.name + ' (' + clust.device.ipaddr + ')', (0, 0, 0))

# TODO write startup message
def print_startup_message():
    print r"""
################################################################################

################################################################################

"""

def print_error_header():
    print r"""
############################### <ERROR> ########################################"""

def print_error_footer():
    print r"""############################### </ERROR> #######################################
"""

def _print_status_bar(outer_numerator, inner_numerator, denominator):
    assert denominator > 0, 'Denominator cannot be zero'
    outer_progress = float(outer_numerator)/denominator * 100
    inner_progress = float(inner_numerator)/denominator * 100
    sys.stdout.write("\rCluster count:%4s\tOuter loop:%.2f%%\tInner loop:%.2f%%" % (denominator, outer_progress, inner_progress ))
    sys.stdout.flush()

if __name__ == "__main__":
    main()
