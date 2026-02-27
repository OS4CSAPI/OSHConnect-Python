#!/usr/bin/env python3
"""
enrich_sensorml.py  –  Deep SensorML metadata enrichment for ODAS C-UAS systems
=================================================================================
Adds standardised SensorML 3.0 metadata to all 43 systems on the OSH SensorHub:
  • keywords          – discovery tokens
  • identifiers       – shortName, manufacturer, model, serial
  • classifiers       – sensorType, platformType, intendedApplication
  • contacts          – manufacturer / operator organisations
  • documents         – product photo, ODAS GitHub, papers, wiki, demo video
  • characteristics   – physical properties (dimensions, weight, mic count, etc.)
  • capabilities      – measurement specs (sample rate, resolution, channels, etc.)

Uses SensorML JSON (application/sml+json) PUT via ?f=sml3 endpoint.

Usage:
    python scripts/enrich_sensorml.py [--dry-run]
"""

import argparse
import json
import sys
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from base64 import b64encode
from copy import deepcopy

BASE = "http://45.55.99.236:8080/sensorhub/api"
AUTH = "Basic " + b64encode(b"ogc:ogc").decode()

# ─── System ID map ───────────────────────────────────────────────────────────

PARENTS = {
    "AZ-MA-1":   {"id": "04ng", "lat": 31.663006, "lon": -110.272897},
    "AZ-MA-2":   {"id": "04o0", "lat": 31.662510, "lon": -110.273200},
    "AZ-MA-3":   {"id": "04og", "lat": 31.662200, "lon": -110.272500},
    "AZ-MA-NET": {"id": "04n0", "lat": 31.662572, "lon": -110.272866},
}

SUBSYSTEMS = {
    "AZ-MA-1": {
        "tripod":  "04p0", "micarray": "04pg", "edge":    "04q0",
        "comms":   "04qg", "power":    "04r0", "actuator": "04rg",
        "mic1":    "04s0", "mic2":     "04sg", "mic3":    "04t0",
        "mic4":    "04tg", "mic5":     "04u0", "mic6":    "04ug",
        "mic7":    "04v0",
    },
    "AZ-MA-2": {
        "tripod":  "04vg", "micarray": "0500", "edge":    "050g",
        "comms":   "0510", "power":    "051g", "actuator": "0520",
        "mic1":    "052g", "mic2":     "0530", "mic3":    "053g",
        "mic4":    "0540", "mic5":     "054g", "mic6":    "0550",
        "mic7":    "055g",
    },
    "AZ-MA-3": {
        "tripod":  "0560", "micarray": "056g", "edge":    "0570",
        "comms":   "057g", "power":    "0580", "actuator": "058g",
        "mic1":    "0590", "mic2":     "059g", "mic3":    "05a0",
        "mic4":    "05ag", "mic5":     "05b0", "mic6":    "05bg",
        "mic7":    "05c0",
    },
}

# ─── Shared metadata fragments ──────────────────────────────────────────────

ODAS_KEYWORDS_COMMON = ["ODAS", "C-UAS", "acoustic detection", "Ft. Huachuca"]

ODAS_DOCUMENTS_COMMON = [
    {
        "role": "http://dbpedia.org/resource/Software",
        "name": "ODAS Library",
        "description": "Open embeddeD Audition System — C library for SSL, SST, separation, post-filtering. MIT-licensed.",
        "link": {"href": "https://github.com/introlab/odas", "type": "text/html"},
    },
    {
        "role": "http://dbpedia.org/resource/Scientific_publication",
        "name": "ODAS Paper",
        "description": "Grondin et al. 'ODAS: Open embeddeD Audition System', Frontiers in Robotics and AI, Vol. 9, 2022.",
        "link": {"href": "https://www.frontiersin.org/article/10.3389/frobt.2022.854444", "type": "text/html"},
    },
    {
        "role": "http://dbpedia.org/resource/Scientific_publication",
        "name": "SSL/SST Methods Paper",
        "description": "Grondin & Michaud 'Lightweight and Optimized Sound Source Localization and Tracking Methods', Robotics and Autonomous Systems, 2019.",
        "link": {"href": "https://arxiv.org/pdf/1812.00115", "type": "application/pdf"},
    },
    {
        "role": "http://dbpedia.org/resource/Web_page",
        "name": "ODAS Wiki — Configuration",
        "description": "Configuration reference for microphone geometry, SSL, SST, SSS, and classification parameters.",
        "link": {"href": "https://github.com/introlab/odas/wiki/Configuration", "type": "text/html"},
    },
    {
        "role": "http://dbpedia.org/resource/Video",
        "name": "ODAS Demonstration Video",
        "description": "Live demonstration of ODAS sound source localization and tracking.",
        "link": {"href": "https://youtu.be/n7y2rLAnd5I", "type": "text/html"},
    },
]

ODAS_CONTACTS_COMMON = [
    {
        "role": "http://sensorml.com/ont/swe/property/Operator",
        "organisationName": "IntRoLab — Université de Sherbrooke",
        "contactInfo": {
            "website": "https://introlab.3it.usherbrooke.ca",
            "address": {
                "city": "Sherbrooke",
                "administrativeArea": "QC",
                "country": "Canada",
            },
        },
    },
]

MIC_ARRAY_PHOTO = {
    "role": "http://dbpedia.org/resource/Photograph",
    "name": "Microphone Array Photo",
    "description": "XMOS xCore 7-microphone array PCB with labeled mic positions (1-7).",
    "link": {"href": "https://raw.githubusercontent.com/OS4CSAPI/ogc-csapi-explorer/refs/heads/demo/acoustic-cuas-targeting/demo/public/xmos-7mic-array.jpg", "type": "image/jpeg"},
}

ODAS_WEB_GUI = {
    "role": "http://dbpedia.org/resource/Web_page",
    "name": "ODAS Web GUI",
    "description": "Browser-based visualisation tool for ODAS SSL/SST output data.",
    "link": {"href": "https://github.com/introlab/odas_web", "type": "text/html"},
}


# ─── Per-subsystem-type metadata builders ────────────────────────────────────

def build_parent(array_name: str) -> dict:
    """Parent sensor array node (e.g. AZ-MA-1)."""
    p = PARENTS[array_name]
    is_net = array_name == "AZ-MA-NET"
    if is_net:
        keywords = ODAS_KEYWORDS_COMMON + ["sensor network", "fusion", "multi-static"]
        classifiers = [
            {"definition": "http://sensorml.com/ont/swe/property/SensorType", "label": "System Type", "value": "Acoustic Sensor Network"},
            {"definition": "http://sensorml.com/ont/swe/property/IntendedApplication", "label": "Intended Application", "value": "Multi-Static Counter-UAS Acoustic Surveillance"},
        ]
        identifiers = [
            {"definition": "http://sensorml.com/ont/swe/property/ShortName", "label": "Short Name", "value": array_name},
        ]
        capabilities = [
            {"definition": "http://www.w3.org/ns/ssn/systems/SystemCapability", "label": "Network Capabilities", "capabilities": [
                {"type": "Count", "name": "num_arrays", "definition": "http://sensorml.com/ont/swe/property/NumberOfElements", "label": "Number of Sensor Arrays", "value": 3},
                {"type": "Count", "name": "total_mics", "definition": "http://sensorml.com/ont/swe/property/NumberOfElements", "label": "Total Microphones", "value": 21},
                {"type": "Count", "name": "max_fused_tracks", "definition": "http://sensorml.com/ont/swe/property/NumberOfOutputs", "label": "Max Fused Tracks", "value": 4},
            ]},
        ]
        characteristics = []
    else:
        pos_label = {"AZ-MA-1": "north", "AZ-MA-2": "southwest", "AZ-MA-3": "southeast"}[array_name]
        keywords = ODAS_KEYWORDS_COMMON + ["microphone array", "beamforming", "DOA estimation", "sound source localization"]
        classifiers = [
            {"definition": "http://sensorml.com/ont/swe/property/SensorType", "label": "System Type", "value": "Acoustic Array Sensor Node"},
            {"definition": "http://sensorml.com/ont/swe/property/IntendedApplication", "label": "Intended Application", "value": "Counter-UAS Acoustic Detection"},
        ]
        identifiers = [
            {"definition": "http://sensorml.com/ont/swe/property/ShortName", "label": "Short Name", "value": array_name},
            {"definition": "http://sensorml.com/ont/swe/property/LongName", "label": "Long Name", "value": f"ODAS Mic Array Node {array_name} ({pos_label})"},
        ]
        capabilities = [
            {"definition": "http://www.w3.org/ns/ssn/systems/SystemCapability", "label": "Acoustic Capabilities", "capabilities": [
                {"type": "Count", "name": "num_mics", "definition": "http://sensorml.com/ont/swe/property/NumberOfElements", "label": "Microphones", "value": 7},
                {"type": "Quantity", "name": "sample_rate", "definition": "http://qudt.org/vocab/quantitykind/Frequency", "label": "Sample Rate", "uom": {"code": "Hz"}, "value": 48000},
                {"type": "Count", "name": "max_tracked", "definition": "http://sensorml.com/ont/swe/property/NumberOfOutputs", "label": "Max Tracked Sources", "value": 4},
                {"type": "Count", "name": "adc_resolution", "definition": "http://sensorml.com/ont/swe/property/Resolution", "label": "ADC Resolution (bits)", "value": 24},
            ]},
        ]
        characteristics = [
            {"label": "ODAS DSP Pipeline", "characteristics": [
                {"type": "Text", "name": "ssl_method", "definition": "http://sensorml.com/ont/swe/property/AlgorithmType", "label": "SSL Method", "value": "Steered Response Power with Phase Transform (SRP-PHAT)"},
                {"type": "Text", "name": "sst_method", "definition": "http://sensorml.com/ont/swe/property/AlgorithmType", "label": "SST Method", "value": "Kalman Filter (dynamic source addition)"},
                {"type": "Text", "name": "sss_method", "definition": "http://sensorml.com/ont/swe/property/AlgorithmType", "label": "SSS Method", "value": "Delay-and-Sum (DDS) with post-filter"},
                {"type": "Count", "name": "frame_size", "definition": "http://sensorml.com/ont/swe/property/WindowSize", "label": "FFT Frame Size", "value": 256},
                {"type": "Count", "name": "hop_size", "definition": "http://sensorml.com/ont/swe/property/StepSize", "label": "Hop Size", "value": 128},
            ]},
        ]

    return _sml_body(
        uid=PARENTS[array_name]["id"],
        unique_id=f"urn:os4csapi:system:odas:{array_name.lower()}",
        definition="sosa:System" if is_net else "sosa:System",
        label=f"ODAS Mic Array Node {array_name}" if not is_net else "ODAS Acoustic Sensor Network AZ-MA-NET",
        description=_parent_desc(array_name),
        keywords=keywords, identifiers=identifiers, classifiers=classifiers,
        contacts=ODAS_CONTACTS_COMMON,
        documents=ODAS_DOCUMENTS_COMMON + ([ODAS_WEB_GUI] if not is_net else [ODAS_WEB_GUI]),
        characteristics=characteristics, capabilities=capabilities,
        lat=p["lat"], lon=p["lon"],
    )


def build_micarray(array_name: str) -> dict:
    """Microphone array subsystem."""
    p = PARENTS[array_name]
    sid = SUBSYSTEMS[array_name]["micarray"]
    return _sml_body(
        uid=sid,
        unique_id=f"urn:os4csapi:system:odas:{array_name.lower()}:micarray",
        definition="sosa:Sensor",
        label=f"{array_name} MICARRAY",
        description=f"7-microphone circular PDM MEMS array for {array_name}. 38mm diameter phased array using XMOS xCORE-200 multicore controller. Captures omnidirectional audio on all 7 channels simultaneously at 48 kHz / 24-bit. Spatial geometry enables beamforming and cross-correlation-based DOA estimation.",
        keywords=ODAS_KEYWORDS_COMMON + ["microphone array", "beamforming", "DOA estimation", "MEMS", "XMOS xCore", "phased array"],
        identifiers=[
            {"definition": "http://sensorml.com/ont/swe/property/ShortName", "label": "Short Name", "value": "XMOS xCore 7-Mic Array"},
            {"definition": "http://sensorml.com/ont/swe/property/Manufacturer", "label": "Manufacturer", "value": "XMOS Ltd."},
            {"definition": "http://sensorml.com/ont/swe/property/ModelNumber", "label": "Model Number", "value": "xCORE-200 MC Mic Array"},
        ],
        classifiers=[
            {"definition": "http://sensorml.com/ont/swe/property/SensorType", "label": "Sensor Type", "value": "Acoustic Microphone Array"},
            {"definition": "http://sensorml.com/ont/swe/property/IntendedApplication", "label": "Intended Application", "value": "Counter-UAS Acoustic Detection"},
        ],
        contacts=[
            {"role": "http://sensorml.com/ont/swe/property/Manufacturer", "organisationName": "XMOS Ltd.", "contactInfo": {"website": "https://www.xmos.com"}},
        ] + ODAS_CONTACTS_COMMON,
        documents=[MIC_ARRAY_PHOTO] + ODAS_DOCUMENTS_COMMON,
        characteristics=[
            {"label": "Physical Characteristics", "characteristics": [
                {"type": "Count", "name": "num_mics", "definition": "http://sensorml.com/ont/swe/property/NumberOfElements", "label": "Number of Microphones", "value": 7},
                {"type": "Quantity", "name": "array_diameter", "definition": "http://qudt.org/vocab/quantitykind/Diameter", "label": "Array Diameter", "uom": {"code": "mm"}, "value": 38.0},
                {"type": "Text", "name": "mic_type", "definition": "http://sensorml.com/ont/swe/property/ComponentType", "label": "Microphone Type", "value": "MEMS PDM Omnidirectional"},
                {"type": "Text", "name": "mic_pattern", "definition": "http://sensorml.com/ont/swe/property/GeometryType", "label": "Array Geometry", "value": "Circular planar (6 perimeter + 1 center)"},
            ]},
        ],
        capabilities=[
            {"definition": "http://www.w3.org/ns/ssn/systems/SystemCapability", "label": "Measurement Capabilities", "capabilities": [
                {"type": "Quantity", "name": "sample_rate", "definition": "http://qudt.org/vocab/quantitykind/Frequency", "label": "Sample Rate", "uom": {"code": "Hz"}, "value": 48000},
                {"type": "Count", "name": "adc_resolution", "definition": "http://sensorml.com/ont/swe/property/Resolution", "label": "ADC Resolution (bits)", "value": 24},
                {"type": "Count", "name": "num_channels", "definition": "http://sensorml.com/ont/swe/property/NumberOfOutputs", "label": "Audio Channels", "value": 7},
                {"type": "Count", "name": "max_tracked", "definition": "http://sensorml.com/ont/swe/property/NumberOfOutputs", "label": "Max Simultaneous Tracked Sources", "value": 4},
                {"type": "Quantity", "name": "freq_min", "definition": "http://qudt.org/vocab/quantitykind/Frequency", "label": "Min Frequency", "uom": {"code": "Hz"}, "value": 100},
                {"type": "Quantity", "name": "freq_max", "definition": "http://qudt.org/vocab/quantitykind/Frequency", "label": "Max Frequency", "uom": {"code": "Hz"}, "value": 8000},
            ]},
        ],
        lat=p["lat"], lon=p["lon"],
    )


def build_mic(array_name: str, mic_num: int) -> dict:
    """Individual microphone element (mic1–mic7)."""
    p = PARENTS[array_name]
    key = f"mic{mic_num}"
    sid = SUBSYSTEMS[array_name][key]
    position_desc = "center" if mic_num == 7 else f"position {mic_num} (perimeter)"
    return _sml_body(
        uid=sid,
        unique_id=f"urn:os4csapi:system:odas:{array_name.lower()}:{key}",
        definition="sosa:Sensor",
        label=f"{array_name} MIC{mic_num}",
        description=f"MEMS PDM omnidirectional microphone element #{mic_num} ({position_desc}) in the {array_name} 7-channel circular array. Digital Pulse-Density Modulation output at 48 kHz / 24-bit.",
        keywords=["MEMS microphone", "PDM", "omnidirectional", "acoustic sensor"],
        identifiers=[
            {"definition": "http://sensorml.com/ont/swe/property/ShortName", "label": "Short Name", "value": f"Mic {mic_num} ({position_desc})"},
        ],
        classifiers=[
            {"definition": "http://sensorml.com/ont/swe/property/SensorType", "label": "Sensor Type", "value": "MEMS Microphone"},
        ],
        contacts=[
            {"role": "http://sensorml.com/ont/swe/property/Manufacturer", "organisationName": "XMOS Ltd.", "contactInfo": {"website": "https://www.xmos.com"}},
        ],
        documents=[MIC_ARRAY_PHOTO],
        characteristics=[
            {"label": "Microphone Characteristics", "characteristics": [
                {"type": "Text", "name": "transducer_type", "definition": "http://sensorml.com/ont/swe/property/ComponentType", "label": "Transducer Type", "value": "MEMS PDM Omnidirectional"},
                {"type": "Text", "name": "position_in_array", "definition": "http://sensorml.com/ont/swe/property/SpatialPosition", "label": "Position in Array", "value": position_desc},
            ]},
        ],
        capabilities=[
            {"definition": "http://www.w3.org/ns/ssn/systems/SystemCapability", "label": "Microphone Capabilities", "capabilities": [
                {"type": "Quantity", "name": "sample_rate", "definition": "http://qudt.org/vocab/quantitykind/Frequency", "label": "Sample Rate", "uom": {"code": "Hz"}, "value": 48000},
                {"type": "Count", "name": "bit_depth", "definition": "http://sensorml.com/ont/swe/property/Resolution", "label": "Bit Depth", "value": 24},
                {"type": "Quantity", "name": "sensitivity", "definition": "http://qudt.org/vocab/quantitykind/SoundPressureLevel", "label": "Typical Sensitivity", "uom": {"code": "dB"}, "value": -26.0},
            ]},
        ],
        lat=p["lat"], lon=p["lon"],
    )


def build_edge(array_name: str) -> dict:
    """Edge processor subsystem."""
    p = PARENTS[array_name]
    sid = SUBSYSTEMS[array_name]["edge"]
    return _sml_body(
        uid=sid,
        unique_id=f"urn:os4csapi:system:odas:{array_name.lower()}:edge",
        definition="sosa:Platform",
        label=f"{array_name} EDGE",
        description=f"Edge compute module for {array_name}. Runs the ODAS DSP pipeline (SSL → SST → LOB) on a low-power ARM/x86 SBC. Processes 7-channel 48 kHz audio in real-time and publishes results via JSON socket output.",
        keywords=ODAS_KEYWORDS_COMMON + ["edge computing", "embedded", "DSP", "SBC"],
        identifiers=[
            {"definition": "http://sensorml.com/ont/swe/property/ShortName", "label": "Short Name", "value": f"{array_name} Edge Processor"},
        ],
        classifiers=[
            {"definition": "http://sensorml.com/ont/swe/property/SensorType", "label": "Component Type", "value": "Edge Compute Module"},
            {"definition": "http://sensorml.com/ont/swe/property/IntendedApplication", "label": "Intended Application", "value": "Real-time Acoustic DSP Processing"},
        ],
        contacts=ODAS_CONTACTS_COMMON,
        documents=ODAS_DOCUMENTS_COMMON,
        characteristics=[
            {"label": "Processing Characteristics", "characteristics": [
                {"type": "Text", "name": "runtime", "definition": "http://sensorml.com/ont/swe/property/SoftwareType", "label": "DSP Runtime", "value": "ODAS odaslive (C, MIT license)"},
                {"type": "Text", "name": "os", "definition": "http://sensorml.com/ont/swe/property/SoftwareType", "label": "Operating System", "value": "Linux (embedded)"},
                {"type": "Count", "name": "frame_size", "definition": "http://sensorml.com/ont/swe/property/WindowSize", "label": "FFT Frame Size", "value": 256},
                {"type": "Count", "name": "hop_size", "definition": "http://sensorml.com/ont/swe/property/StepSize", "label": "Hop Size", "value": 128},
                {"type": "Quantity", "name": "internal_rate", "definition": "http://qudt.org/vocab/quantitykind/Frequency", "label": "Internal Sample Rate", "uom": {"code": "Hz"}, "value": 16000},
            ]},
        ],
        capabilities=[],
        lat=p["lat"], lon=p["lon"],
    )


def build_comms(array_name: str) -> dict:
    """Communications module subsystem."""
    p = PARENTS[array_name]
    sid = SUBSYSTEMS[array_name]["comms"]
    return _sml_body(
        uid=sid,
        unique_id=f"urn:os4csapi:system:odas:{array_name.lower()}:comms",
        definition="sosa:Platform",
        label=f"{array_name} COMMS",
        description=f"Communications module for {array_name}. Provides mesh-network connectivity (Wi-Fi / Ethernet) between the edge processor and the central fusion node (AZ-MA-NET). Supports JSON socket output from ODAS for SST/SSL data relay.",
        keywords=ODAS_KEYWORDS_COMMON + ["communications", "mesh network", "telemetry"],
        identifiers=[
            {"definition": "http://sensorml.com/ont/swe/property/ShortName", "label": "Short Name", "value": f"{array_name} Comms Module"},
        ],
        classifiers=[
            {"definition": "http://sensorml.com/ont/swe/property/SensorType", "label": "Component Type", "value": "Communications Module"},
        ],
        contacts=ODAS_CONTACTS_COMMON,
        documents=[],
        characteristics=[],
        capabilities=[],
        lat=p["lat"], lon=p["lon"],
    )


def build_power(array_name: str) -> dict:
    """Power supply subsystem."""
    p = PARENTS[array_name]
    sid = SUBSYSTEMS[array_name]["power"]
    return _sml_body(
        uid=sid,
        unique_id=f"urn:os4csapi:system:odas:{array_name.lower()}:power",
        definition="sosa:Platform",
        label=f"{array_name} POWER",
        description=f"Power supply module for {array_name}. Provides regulated DC power to the microphone array, edge processor, comms module, and pan-tilt actuator. Supports both battery (LiFePO4) and solar panel input for sustained field operation.",
        keywords=ODAS_KEYWORDS_COMMON + ["power supply", "battery", "solar"],
        identifiers=[
            {"definition": "http://sensorml.com/ont/swe/property/ShortName", "label": "Short Name", "value": f"{array_name} Power Supply"},
        ],
        classifiers=[
            {"definition": "http://sensorml.com/ont/swe/property/SensorType", "label": "Component Type", "value": "Power Supply Module"},
        ],
        contacts=ODAS_CONTACTS_COMMON,
        documents=[],
        characteristics=[
            {"label": "Power Characteristics", "characteristics": [
                {"type": "Text", "name": "battery_type", "definition": "http://sensorml.com/ont/swe/property/ComponentType", "label": "Battery Chemistry", "value": "LiFePO4"},
                {"type": "Text", "name": "charging", "definition": "http://sensorml.com/ont/swe/property/ComponentType", "label": "Charging Source", "value": "Solar panel + DC input"},
            ]},
        ],
        capabilities=[],
        lat=p["lat"], lon=p["lon"],
    )


def build_tripod(array_name: str) -> dict:
    """Tripod platform subsystem."""
    p = PARENTS[array_name]
    sid = SUBSYSTEMS[array_name]["tripod"]
    return _sml_body(
        uid=sid,
        unique_id=f"urn:os4csapi:system:odas:{array_name.lower()}:tripod",
        definition="sosa:Platform",
        label=f"{array_name} TRIPOD",
        description=f"Tripod platform for {array_name}. Provides stable elevated mounting for the microphone array and pan-tilt actuator. Adjustable height (1.2–2.0 m) with ground stakes for wind resistance.",
        keywords=ODAS_KEYWORDS_COMMON + ["tripod", "platform", "mounting"],
        identifiers=[
            {"definition": "http://sensorml.com/ont/swe/property/ShortName", "label": "Short Name", "value": f"{array_name} Tripod Platform"},
        ],
        classifiers=[
            {"definition": "http://sensorml.com/ont/swe/property/PlatformType", "label": "Platform Type", "value": "Tripod Mast"},
        ],
        contacts=ODAS_CONTACTS_COMMON,
        documents=[],
        characteristics=[
            {"label": "Physical Characteristics", "characteristics": [
                {"type": "Quantity", "name": "height_min", "definition": "http://qudt.org/vocab/quantitykind/Height", "label": "Min Height", "uom": {"code": "m"}, "value": 1.2},
                {"type": "Quantity", "name": "height_max", "definition": "http://qudt.org/vocab/quantitykind/Height", "label": "Max Height", "uom": {"code": "m"}, "value": 2.0},
            ]},
        ],
        capabilities=[],
        lat=p["lat"], lon=p["lon"],
    )


def build_actuator(array_name: str) -> dict:
    """Pan-tilt actuator subsystem."""
    p = PARENTS[array_name]
    sid = SUBSYSTEMS[array_name]["actuator"]
    return _sml_body(
        uid=sid,
        unique_id=f"urn:os4csapi:system:odas:{array_name.lower()}:actuator",
        definition="sosa:Actuator",
        label=f"{array_name} ACTUATOR",
        description=f"Pan-tilt actuator for {array_name}. Motorised two-axis gimbal that slews the microphone array to face the strongest tracked sound source. Receives bearing commands from the edge processor based on ODAS SST output.",
        keywords=ODAS_KEYWORDS_COMMON + ["actuator", "pan-tilt", "gimbal", "pointing"],
        identifiers=[
            {"definition": "http://sensorml.com/ont/swe/property/ShortName", "label": "Short Name", "value": f"{array_name} Pan-Tilt Actuator"},
        ],
        classifiers=[
            {"definition": "http://sensorml.com/ont/swe/property/SensorType", "label": "Component Type", "value": "Pan-Tilt Actuator"},
        ],
        contacts=ODAS_CONTACTS_COMMON,
        documents=[],
        characteristics=[],
        capabilities=[
            {"definition": "http://www.w3.org/ns/ssn/systems/SystemCapability", "label": "Actuator Capabilities", "capabilities": [
                {"type": "Quantity", "name": "pan_range", "definition": "http://qudt.org/vocab/quantitykind/Angle", "label": "Pan Range", "uom": {"code": "deg"}, "value": 360},
                {"type": "Quantity", "name": "tilt_range", "definition": "http://qudt.org/vocab/quantitykind/Angle", "label": "Tilt Range", "uom": {"code": "deg"}, "value": 90},
            ]},
        ],
        lat=p["lat"], lon=p["lon"],
    )


# ─── Description helpers ─────────────────────────────────────────────────────

def _parent_desc(name: str) -> str:
    descs = {
        "AZ-MA-1": "ODAS 7-microphone circular PDM MEMS array node deployed at Ft. Huachuca, AZ. Position 1 (north). Performs real-time sound source localization (SSL), sound source tracking (SST), and line-of-bearing (LOB) estimation using the ODAS (Open embeddeD Audition System) DSP pipeline. Subsystems include tripod platform, mic array, edge processor, comms module, power supply, and pan-tilt actuator.",
        "AZ-MA-2": "ODAS 7-microphone circular PDM MEMS array node deployed at Ft. Huachuca, AZ. Position 2 (southwest). Performs real-time sound source localization (SSL), sound source tracking (SST), and line-of-bearing (LOB) estimation using the ODAS (Open embeddeD Audition System) DSP pipeline. Subsystems include tripod platform, mic array, edge processor, comms module, power supply, and pan-tilt actuator.",
        "AZ-MA-3": "ODAS 7-microphone circular PDM MEMS array node deployed at Ft. Huachuca, AZ. Position 3 (southeast). Performs real-time sound source localization (SSL), sound source tracking (SST), and line-of-bearing (LOB) estimation using the ODAS (Open embeddeD Audition System) DSP pipeline. Subsystems include tripod platform, mic array, edge processor, comms module, power supply, and pan-tilt actuator.",
        "AZ-MA-NET": "Central fusion node for the ODAS acoustic sensor network deployed at Ft. Huachuca, AZ. Aggregates SSL/SST tracks from three sensor arrays (AZ-MA-1/2/3) and performs multi-static triangulation to produce fused target tracks with estimated geo-position. Publishes consolidated track updates and network health telemetry.",
    }
    return descs[name]


# ─── SensorML body builder ───────────────────────────────────────────────────

def _sml_body(*, uid, unique_id, definition, label, description,
              keywords, identifiers, classifiers, contacts, documents,
              characteristics, capabilities, lat, lon) -> dict:
    """Build an ordered SensorML JSON body (type must be first key)."""
    body = {"type": "PhysicalSystem"}
    body["uniqueId"] = unique_id
    body["definition"] = definition
    body["label"] = label
    body["description"] = description
    if keywords:
        body["keywords"] = keywords
    if identifiers:
        body["identifiers"] = identifiers
    if classifiers:
        body["classifiers"] = classifiers
    body["validTime"] = ["2026-01-01T00:00:00Z", ".."]
    if characteristics:
        body["characteristics"] = characteristics
    if capabilities:
        body["capabilities"] = capabilities
    if contacts:
        body["contacts"] = contacts
    if documents:
        body["documents"] = documents
    body["position"] = {"type": "Point", "coordinates": [lon, lat]}
    return body


# ─── HTTP helpers ─────────────────────────────────────────────────────────────

def put_sml(system_id: str, body: dict, dry_run: bool = False) -> bool:
    """PUT a SensorML JSON body to the server."""
    url = f"{BASE}/systems/{system_id}?f=sml3"
    payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
    if dry_run:
        print(f"  [DRY-RUN] Would PUT {len(payload)} bytes to {url}")
        return True
    req = Request(url, data=payload, method="PUT")
    req.add_header("Authorization", AUTH)
    req.add_header("Content-Type", "application/sml+json")
    try:
        with urlopen(req) as resp:
            _ = resp.read()
        return True
    except HTTPError as e:
        err = e.read().decode()
        print(f"  ✗ HTTP {e.code}: {err}")
        return False


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Enrich ODAS systems with deep SensorML metadata")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without executing")
    args = parser.parse_args()

    ok, fail = 0, 0

    # Parents
    for name in ["AZ-MA-1", "AZ-MA-2", "AZ-MA-3", "AZ-MA-NET"]:
        pid = PARENTS[name]["id"]
        body = build_parent(name)
        fields = [k for k in ["keywords", "identifiers", "classifiers", "contacts", "documents", "characteristics", "capabilities"] if k in body]
        print(f"[{name}] {pid}  +{','.join(fields)}")
        if put_sml(pid, body, args.dry_run):
            ok += 1
        else:
            fail += 1

    # Subsystems per array
    for arr in ["AZ-MA-1", "AZ-MA-2", "AZ-MA-3"]:
        subs = SUBSYSTEMS[arr]

        # micarray
        sid = subs["micarray"]
        body = build_micarray(arr)
        fields = [k for k in ["keywords", "identifiers", "classifiers", "contacts", "documents", "characteristics", "capabilities"] if k in body]
        print(f"  [{arr} micarray] {sid}  +{','.join(fields)}")
        if put_sml(sid, body, args.dry_run):
            ok += 1
        else:
            fail += 1

        # edge
        sid = subs["edge"]
        body = build_edge(arr)
        fields = [k for k in ["keywords", "identifiers", "classifiers", "contacts", "documents", "characteristics", "capabilities"] if k in body]
        print(f"  [{arr} edge] {sid}  +{','.join(fields)}")
        if put_sml(sid, body, args.dry_run):
            ok += 1
        else:
            fail += 1

        # comms
        sid = subs["comms"]
        body = build_comms(arr)
        print(f"  [{arr} comms] {sid}")
        if put_sml(sid, body, args.dry_run):
            ok += 1
        else:
            fail += 1

        # power
        sid = subs["power"]
        body = build_power(arr)
        print(f"  [{arr} power] {sid}")
        if put_sml(sid, body, args.dry_run):
            ok += 1
        else:
            fail += 1

        # tripod
        sid = subs["tripod"]
        body = build_tripod(arr)
        print(f"  [{arr} tripod] {sid}")
        if put_sml(sid, body, args.dry_run):
            ok += 1
        else:
            fail += 1

        # actuator
        sid = subs["actuator"]
        body = build_actuator(arr)
        print(f"  [{arr} actuator] {sid}")
        if put_sml(sid, body, args.dry_run):
            ok += 1
        else:
            fail += 1

        # mic1–mic7
        for m in range(1, 8):
            key = f"mic{m}"
            sid = subs[key]
            body = build_mic(arr, m)
            print(f"  [{arr} {key}] {sid}")
            if put_sml(sid, body, args.dry_run):
                ok += 1
            else:
                fail += 1

    print(f"\nEnrichment complete: {ok} updated, {fail} failed")
    if fail:
        sys.exit(1)


if __name__ == "__main__":
    main()
