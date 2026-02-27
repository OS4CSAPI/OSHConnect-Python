"""
Enrich ODAS systems on the OSH SensorHub with descriptions from the data model.

Adds `description` fields to all 43 systems + the network system via PUT updates.
The descriptions are derived from the SOSA/SSN data model document.
"""
import requests
import json
import sys

s = requests.Session()
s.auth = ('ogc', 'ogc')
BASE = 'http://45.55.99.236:8080/sensorhub/api'
H = {'Accept': 'application/json', 'Content-Type': 'application/json'}

# ── Description templates keyed by UID suffix ────────────────────────
# Parent nodes get their own unique descriptions.
# Subsystem types share a template parameterized by the parent label.

PARENT_DESCRIPTIONS = {
    'az-ma-1': (
        'ODAS 7-microphone circular PDM MEMS array node deployed at Ft. Huachuca, AZ. '
        'Position 1 (north). Performs real-time sound source localization (SSL), '
        'sound source tracking (SST), and line-of-bearing (LOB) estimation using '
        'the ODAS (Open embeddeD Audition System) DSP pipeline. '
        'Subsystems include tripod platform, mic array, edge processor, comms module, '
        'power supply, and pan-tilt actuator.'
    ),
    'az-ma-2': (
        'ODAS 7-microphone circular PDM MEMS array node deployed at Ft. Huachuca, AZ. '
        'Position 2 (southeast). Performs real-time SSL, SST, and LOB estimation. '
        'Cross-correlated with AZ-MA-1 and AZ-MA-3 for network-level triangulation.'
    ),
    'az-ma-3': (
        'ODAS 7-microphone circular PDM MEMS array node deployed at Ft. Huachuca, AZ. '
        'Position 3 (southwest). Performs real-time SSL, SST, and LOB estimation. '
        'Completes the triangulation baseline with AZ-MA-1 and AZ-MA-2.'
    ),
    'az-ma-net': (
        'Network-fused acoustic sensing system for the Ft. Huachuca C-UAS demo. '
        'Aggregates observations from AZ-MA-1, AZ-MA-2, and AZ-MA-3 to produce '
        'triangulated source positions, classification probabilities, scene summaries, '
        'and fused track updates. Acts as the central command and control hub.'
    ),
}

def subsystem_desc(parent_label: str, subsys_type: str) -> str:
    """Generate a description for a subsystem based on its type."""
    templates = {
        'tripod': (
            f'Portable aluminum survey-grade tripod platform for {parent_label}. '
            'Provides stable, leveled mounting at 1.5m height for the microphone array '
            'and associated electronics. Weather-resistant, rated for field deployment.'
        ),
        'micarray': (
            f'7-microphone circular PDM MEMS array for {parent_label}. '
            '38mm diameter phased array using XMOS xCORE-200 multicore controller. '
            'Captures omnidirectional audio on all 7 channels simultaneously at 48 kHz / 24-bit. '
            'Spatial geometry enables beamforming and cross-correlation-based DOA estimation.'
        ),
        'edge': (
            f'Edge compute module for {parent_label}. '
            'Runs the ODAS DSP pipeline (SSL, SST, LOB) on an ARM Cortex-A72 processor. '
            'Receives raw 7-channel PCM from the mic array via USB Audio Class 1.0. '
            'Outputs bearing estimates and tracked source positions via JSON over MQTT/HTTP.'
        ),
        'comms': (
            f'Communications subsystem for {parent_label}. '
            'Dual-band 802.11ac WiFi + 4G LTE cellular backhaul. Provides low-latency '
            'telemetry uplink to the network fusion node (AZ-MA-NET) and remote management access.'
        ),
        'power': (
            f'Power supply subsystem for {parent_label}. '
            '12V 100Ah LiFePO4 battery with 50W solar panel and MPPT charge controller. '
            'Provides 48+ hours of autonomous operation. Includes voltage/current monitoring.'
        ),
        'actuator': (
            f'Pan-tilt actuator for {parent_label}. '
            'Stepper-motor-driven 2-axis gimbal for remote re-pointing of the microphone array. '
            'Accepts azimuth (0-360°) and elevation (-10° to +60°) commands via the control stream.'
        ),
    }
    # Individual microphones
    if subsys_type.startswith('mic') and subsys_type != 'micarray':
        mic_num = subsys_type.replace('mic', '')
        positions = {
            '1': 'center',
            '2': '0° (north)',
            '3': '60° (NE)',
            '4': '120° (SE)',
            '5': '180° (south)',
            '6': '240° (SW)',
            '7': '300° (NW)',
        }
        pos = positions.get(mic_num, f'position {mic_num}')
        return (
            f'MEMS PDM microphone element #{mic_num} ({pos}) in {parent_label} array. '
            'Knowles SPH0645LM4H-B, omnidirectional, -26 dBFS sensitivity, 50 Hz – 15 kHz. '
            'Outputs 24-bit PCM at 48 kHz via I²S/PDM bus to the XMOS controller.'
        )
    return templates.get(subsys_type, f'{subsys_type.upper()} subsystem of {parent_label}.')


def enrich_system(system_id: str, description: str) -> bool:
    """PUT-update a system to add a description field."""
    # Fetch current system data
    r = s.get(f'{BASE}/systems/{system_id}', headers=H)
    if r.status_code != 200:
        print(f'  SKIP {system_id}: GET returned {r.status_code}')
        return False

    data = r.json()
    # Add description to properties
    data['properties']['description'] = description

    # PUT it back
    r2 = s.put(
        f'{BASE}/systems/{system_id}',
        headers=H,
        data=json.dumps(data),
    )
    if r2.status_code in (200, 204):
        return True
    else:
        print(f'  FAIL {system_id}: PUT returned {r2.status_code} - {r2.text[:200]}')
        return False


def main():
    updated = 0
    failed = 0

    # Parent systems
    parents = {
        '04ng': ('az-ma-1', 'AZ-MA-1'),
        '04o0': ('az-ma-2', 'AZ-MA-2'),
        '04og': ('az-ma-3', 'AZ-MA-3'),
        '04n0': ('az-ma-net', 'AZ-MA-NET'),
    }

    for sys_id, (key, label) in parents.items():
        desc = PARENT_DESCRIPTIONS[key]
        if enrich_system(sys_id, desc):
            updated += 1
            print(f'  ✓ {label} ({sys_id})')
        else:
            failed += 1

    # Subsystems — iterate each parent's children
    sensor_parents = {
        '04ng': 'AZ-MA-1',
        '04o0': 'AZ-MA-2',
        '04og': 'AZ-MA-3',
    }

    for parent_id, parent_label in sensor_parents.items():
        r = s.get(f'{BASE}/systems/{parent_id}/subsystems?limit=50', headers=H)
        subs = r.json().get('items', [])
        for sub in subs:
            sub_id = sub['id']
            uid = sub['properties']['uid']
            # Extract subsystem type from UID: urn:os4csapi:...:az-ma-1:micarray → micarray
            parts = uid.split(':')
            subsys_type = parts[-1] if len(parts) > 1 else 'unknown'

            desc = subsystem_desc(parent_label, subsys_type)
            if enrich_system(sub_id, desc):
                updated += 1
                print(f'  ✓ {parent_label}/{subsys_type} ({sub_id})')
            else:
                failed += 1

    print(f'\n{"="*50}')
    print(f'Enrichment complete: {updated} updated, {failed} failed')
    print(f'{"="*50}')
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
