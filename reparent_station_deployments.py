"""Re-parent the 5 NDBC station deployments back under the Buoy Stations group.

The previous PUT to update platform@link.href used the root /deployments/{id}
endpoint which the server treated as a full replacement, severing the
ogc-rel:parentDeployment link and promoting each deployment to top-level.

Fix: delete each orphaned deployment, then re-POST under the correct parent via
/deployments/{group_id}/subdeployments with the correct platform@link.href.
"""
from publishers.bootstrap_helpers import api_post, api_delete, get_config, _auth_header, find_by_uid

cfg = get_config()
base_url = cfg['base_url']
auth = _auth_header(cfg['user'], cfg['password'])

GROUP_ID = '04d825a0-d6d9-4aba-8b4a-7eed9992ff60'  # NDBC Buoy Stations
VALID_TIME_START = '2026-01-01T00:00:00Z'

# (station_id, display_name, lon, lat, system_server_id)
stations = [
    ('44025', 'Long Island, NY',         -73.164, 40.251,  'd5bb1466-dbf0-492f-a30b-380739e0d499'),
    ('41009', 'Cape Canaveral East, FL', -80.166, 28.519,  '24e78589-74a8-48b3-939c-402c2c6bba40'),
    ('42036', 'Gulf of Mexico',          -84.517, 28.5,    '0a72b89e-e0b7-40d7-8259-0d481a8bc654'),
    ('46025', 'Santa Monica Basin, CA',  -119.053, 33.749, '83c9707b-ac5f-4f7d-87c4-26cf21f67441'),
    ('46013', 'Bodega Bay, CA',          -123.301, 38.242, 'd8cf20d5-f03a-4f87-bd3a-95574227e544'),
]

for st_id, name, lon, lat, sys_id in stations:
    uid = 'urn:os4csapi:deployment:ndbc-' + st_id + ':v1'
    system_href = base_url.rstrip('/') + '/systems/' + sys_id

    # 1. Find and delete the orphaned top-level deployment
    existing_id = find_by_uid(base_url, auth, 'deployments', uid)
    if existing_id:
        api_delete(base_url, 'deployments/' + existing_id, auth)
        print('  [DEL] deployments/' + existing_id + ' (' + st_id + ')')
    else:
        print('  [SKIP-DEL] ' + uid + ' not found at top level')

    # 2. Re-POST under the group as a subdeployment with corrected platform@link
    body = {
        'type': 'Feature',
        'geometry': {'type': 'Point', 'coordinates': [lon, lat]},
        'properties': {
            'featureType': 'sosa:Deployment',
            'uid': uid,
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
    result = api_post(base_url, 'deployments/' + GROUP_ID + '/subdeployments', body, auth)
    new_id = result.get('id') if result else None
    print('  [POST] ' + st_id + ' -> new id=' + str(new_id) + '  href=' + system_href)

print('Done.')
