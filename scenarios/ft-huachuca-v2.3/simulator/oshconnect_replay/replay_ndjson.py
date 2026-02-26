import pathlib
BASE=pathlib.Path(__file__).resolve().parents[2]/"examples"/"sample_data"
for folder in ["observations","commands"]:
  for p in (BASE/folder).glob("*.ndjson"):
    print(folder,p.name,sum(1 for _ in p.read_text(encoding="utf-8").splitlines()))
