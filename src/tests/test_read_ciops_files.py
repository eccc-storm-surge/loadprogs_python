from pathlib import Path

from data import mod
from data.obs import Station


def test_read_one_file():
    path = next(Path("~olh001/data/ppp3/ciopse/pa_links/").expanduser().glob("*"))

    print(f"reading {path}")

    mock_stations = [
        Station(station_info=dict(id="test_id", lon=-59, lat=43, name="test_name"))
    ]

    df = mod.get_mod_timeseries_closest_to(
        mock_stations, data_files=[path], nomvar="SSH"
    )
    print(df.head())


def test_all():
    test_read_one_file()


if __name__ == '__main__':
    test_all()