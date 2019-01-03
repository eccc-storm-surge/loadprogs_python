from pathlib import Path

from main import main


if __name__ == '__main__':
    main(config_path=Path("configs/rdsps/forecast/FC70E16V2.cfg"))
    main(config_path=Path("configs/rdsps/forecast/op_during_FC70E16V2.cfg"))