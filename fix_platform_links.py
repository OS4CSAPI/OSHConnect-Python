"""One-shot script: update the 5 NDBC station deployments with the corrected
platform@link.href that includes the /systems/ path segment."""
import base64
from publishers.bootstrap_helpers import api_put, get_config, _auth_header

cfg = get_config()
base_url = cfg['base_url']
auth = _auth_header(cfg['user'], cfg['password'])

# (station_id, display_name, lon, lat, deployment_server_id, system_server_id)
stations = [
    ('44025', 'Long Island, NY',         -73.164, 40.251,  '7c12dd2f-0dcf-4322-9528-d59dedbe6607', 'd5bb1466-dbf0-492f-a30b-380739e0d499'),
    ('41009', 'Cape Canaveral East, FL', -80.166, 28.519,  '3078389a-c539-42b3-be4f-124045694cdc', '24e78589-74a8-48b3-939c-402c2c6bba40'),
    ('42036', 'Gulf of Mexico',          -84.517, 28.5,    '4405bded-558f-4dda-b466-ff699968ea97', '0a72b89e-e0b7-40d7-8259-0d481a8bc654'),
    ('46025', 'Santa Monica Basin, CA',  -119.053, 33.749, '0022a672-807b-4963-a217-dc583740dac5', '83c9707b-ac5f-4f7d-87c4-26cf21f67441'),
    ('46013', 'Bodega Bay, CA',          -123.301, 38.242, 'c063a2bf-7a0d-4546-92d5-fd896aa19dd6', 'd8cf20d5-f03a-4f87-bd3a-95574227e544'),
]

VALID_TIME_START = '2026-01-01T00:00:00Z'

for st_id, name, lon, lat, dep_id, sys_id in stations:
    system_href = base_url.rstrip('/') + '/systems/' + sys_id
    body = {
        'type': 'Feature',
        'geometry': {'type': 'Point', 'coordinates': [lon, lat]},
        'properties': {
            'featureType': 'sosa:Deployment',
            'uid': 'urn:os4csapi:deployment:ndbc-' + st_id + ':v1',
            'name': 'Buoy ' + st_id + ' Feed',
            'description': 'NDBC buoy ' + st_id + ' (' + name + ') observation feed.',
            'validTime': [VALID_TIME_START, '..'],
            'platform@link': {
                'href': system_href,
                'uid': 'urn:os4csapi:system:ndbc:' + st_id + ':v1',
                'title': 'NDBC ' + st_id,
            },
        },
    }
    api_put(base_url, 'deployments/' + dep_id, body, auth, content_type='application/json')
    print('  [PUT] deployments/' + dep_id + ' (' + st_id + ') -> platform@link.href = ' + system_href)

print('Done.')
