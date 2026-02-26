# Changelog v2.3

- Property resources: qualifiers are now valid SWE Common Text components (type/definition/label/value), matching SWE Common JSON schemas.
- DataStream create templates: normalized closer to the official datastream create example by omitting system@link on create.
- Added create_datastreams_root variants for servers that require system@link.
- Added replay_config.json + generate_curl_replay.py to map NDJSON files to create templates and produce curl replay commands.
