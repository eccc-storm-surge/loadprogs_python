from pathlib import Path

from loadprogs.main import main


def test():
    main.main(config_path=Path("/home/olh001/Python/loadprogs_python_experiments/config/webtide/resps_2008.cfg"))


if __name__ == '__main__':
    test()
