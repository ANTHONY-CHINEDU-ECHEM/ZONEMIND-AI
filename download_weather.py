"""Download the typical meteorological year weather files used by the experiments.

The files are TMY3 records distributed with the EnergyPlus project. They are already
included in ``data/weather``; this script exists so the data can be refreshed or
verified from source. Any other EPW file can be added by placing it in the same folder
and registering it under ``climates`` in ``configs/default.yaml``.
"""
import urllib.request
from pathlib import Path

BASE = "https://raw.githubusercontent.com/NREL/EnergyPlus/develop/weather/"
FILES = {
    "chicago.epw": "USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw",
    "tampa.epw": "USA_FL_Tampa.Intl.AP.722110_TMY3.epw",
    "san_francisco.epw": "USA_CA_San.Francisco.Intl.AP.724940_TMY3.epw",
    "golden.epw": "USA_CO_Golden-NREL.724666_TMY3.epw",
}

if __name__ == "__main__":
    out = Path(__file__).resolve().parents[1] / "data" / "weather"
    out.mkdir(parents=True, exist_ok=True)
    for local, remote in FILES.items():
        print("downloading", remote)
        urllib.request.urlretrieve(BASE + remote, out / local)
    print("done")
