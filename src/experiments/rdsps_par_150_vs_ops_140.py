from pathlib import Path
from main import main


do_pa = False

if __name__ == '__main__':
    if do_pa:
        main(config_path=Path("configs/CPOP_RDSPS_150_par_vs_RDSPS_140_ops/rdsps_pa_ops_140.cfg"))
        main(config_path=Path("configs/CPOP_RDSPS_150_par_vs_RDSPS_140_ops/rdsps_pa_par_150.cfg"))

    main(config_path=Path("configs/CPOP_RDSPS_150_par_vs_RDSPS_140_ops/rdsps_fc_ops_140.cfg"))
    main(config_path=Path("configs/CPOP_RDSPS_150_par_vs_RDSPS_140_ops/rdsps_fc_par_150.cfg"))