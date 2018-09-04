"""
Convert obs and model data into a text file where lines contain 1 record of obs and model data


example:

$ head surge_rdsps_pseudo-analysis_experimental.dat
  1   8443970 42.3600009 71.0500009 201612232200 -0.0857397 -0.1144047
  2   8443970 42.3600009 71.0500009 201612232300 -0.0982237 -0.1194047
  3   8443970 42.3600009 71.0500009 201612240000 -0.1089077 -0.1364047
  4   8443970 42.3600009 71.0500009 201612240100 -0.1184387 -0.1434047
  5   8443970 42.3600009 71.0500009 201612240200 -0.1278157 -0.1354047
  6   8443970 42.3600009 71.0500009 201612240300 -0.1375877 -0.1424047
  1   8418150 43.6600009 70.2500009 201612232200 -0.0437227 -0.1044837
  2   8418150 43.6600009 70.2500009 201612232300 -0.0562497 -0.1124837
  3   8418150 43.6600009 70.2500009 201612240000 -0.0686327 -0.1164837
  4   8418150 43.6600009 70.2500009 201612240100 -0.0808897 -0.1194837

Explanation:
col 0: validity hour since the start of the simulation
col 1: station id
col 2: latitude
col 3: longitude
col 4: date of validity of the record
col 5: observed value
col 6: modelled value
[col 7: modelled value]
[...]
"""

import configparser
from pathlib import Path


def main():
    config_path = Path("configs/gem5_research_cycle/rdsps_pseudo-analysis_experimental.cfg")
    config = configparser.ConfigParser(inline_comment_prefixes=("#", ";"),
                                       interpolation=configparser.ExtendedInterpolation())
    config_data = "[top]\n" + config_path.open().read()
    config.read_string(config_data)
    config = config["top"]

    for k, v in config.items():
        print(f"{k} => {v}")

    # TODO: Load obs

    # TODO: Do detiding

    # TODO: Load mod corresponding to obs and take out time avg

    # TODO: Dump corresponding obs and mod data into a file for scoring


if __name__ == '__main__':
    main()