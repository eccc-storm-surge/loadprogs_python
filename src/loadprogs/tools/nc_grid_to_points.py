#!/usr/bin/env python

import argparse
from pathlib import Path
import netCDF4

from loadprogs.data import obs
from netCDF4 import Dataset, num2date, stringtochar

"""
Extract timeseries for stations from netcdf files and 
save them in netcdf format

similar to: 

netcdf W_CN-ECCC-CANADA\,MODELE\,SURCOTES+SPM+NETCDF_C_CWAO_20210310120000 {
dimensions:
        time_counter = 121 ;
        station_index = 3 ;
        string256 = 256 ;
variables:
        double time_counter(time_counter) ;
                time_counter:_FillValue = NaN ;
                time_counter:standard_name = "time" ;
                time_counter:units = "minutes since 2021-03-10T12:00:00" ;
                time_counter:calendar = "standard" ;
        float nav_lon(station_index) ;
                nav_lon:_FillValue = NaNf ;
                nav_lon:standard_name = "longitude" ;
                nav_lon:long_name = "Longitude" ;
                nav_lon:units = "degrees_east" ;
        float nav_lat(station_index) ;
                nav_lat:_FillValue = NaNf ;
                nav_lat:standard_name = "latitude" ;
                nav_lat:long_name = "Latitude" ;
                nav_lat:units = "degrees_north" ;
        char station_name(station_index, string256) ;
        char station_id(station_index, string256) ;
        char station_status(station_index, string256) ;
                station_status:units = "-" ;
                station_status:long_name = "" ;
                station_status:description = "trusted: enough current observations to verify directly against model\nverified: enough historical observations to confirm behaviour at point is coherent with observations\nunverified: no or not enough observations, use at your own risks\nnonrepresentative: local effects are not resolved at a given model resolution" ;
        float etas(time_counter, station_index) ;
                etas:_FillValue = NaNf ;
                etas:least_significant_digit = 6LL ;
                etas:units = "m" ;
                etas:long_name = "storm surge" ;
                etas:nomvar = "ETAS" ;
                etas:comment = "storm surge from Dalcoast" ;
                etas:standard_name = "non_tidal_elevation_of_sea_surface_height" ;
"""


def read_cmd_args():
    parser = argparse.ArgumentParser(description="run experiment")

    parser.add_argument("--obs", required=True, type=Path,
                        help="path to a file containing obs station metadata (coordinates, ids, names)")

    parser.add_argument("--inp", required=True, type=Path,
                        help="path to the input netcdf file (2D)")

    parser.add_argument("--out", required=True, type=Path,
                        help="path to the output netcdf file (1D)")

    parser.add_argument("--timn", required=False, default="time_counter",
                        help="name of the time variable")

    parser.add_argument("--transpose-index", required=False, default="T",
                        type=lambda flag: True if flag.lower() == "t" else False,
                        help="T (default) if the order of indices in the .obs file should be "
                             "transposed before getting the corresponding gridcell"
                             "lon,lat or lat,lon")

    parser.add_argument("--change-time-units-to", required=False, default="minutes",
                        help="time units to be used in the output file: seconds, minutes (default), hours")

    args = parser.parse_args()

    assert args.inp.exists(), f"should exist: {args.inp}"
    assert args.obs.exists(), f"should exist: {args.inp}"

    return args


def get_sec_multiplier(units="minutes"):
    if units == "minutes":
        return 60
    elif units == "hours":
        return 3600
    elif units == "seconds":
        return 1
    else:
        raise ValueError(f"Unrecognised time units: {units}")


def convert(inp_file, out_file, stations_info, varnames: dict = None,
            transpose_index=False, reftime_format="%Y:%m:%dT%H:%M:%S",
            out_time_units="minutes"):
    """

    Args:
        out_time_units: time units in the time variable s,m (default),h
        reftime_format: format of the reference time written to the netcdf file
                        in the units attribute
        inp_file:
        out_file:
        stations_info: indices are 1-based as in Fortran
        varnames:
        transpose_index: whether to transpose indices read from the .obs files
    """
    if varnames is None:
        varnames = {
            "time": "time_counter",
            "lon": "nav_lon",
            "lat": "nav_lat"
        }

    station_dim = "station_index"
    i_arr, j_arr = [stations_info[label].values - 1 for label in ["DATA.I", "DATA.J"]]

    if transpose_index:
        i_arr, j_arr = j_arr, i_arr

    # write data to the output netcdf
    with Dataset(out_file, mode="w") as ds_out:
        assert isinstance(ds_out, Dataset)

        with Dataset(inp_file) as ds_inp:
            assert isinstance(ds_inp, Dataset)
            t_var_in = ds_inp[varnames["time"]]

            # create dimensions
            ds_out.createDimension(varnames["time"], len(t_var_in))
            ds_out.createDimension(station_dim, len(stations_info))

            nchars = 256
            ds_out.createDimension("nchars", nchars)
            s_type = f"S{nchars}"

            station_name = ds_out.createVariable("station_name", "c", (station_dim, "nchars"))
            station_name[:] = stringtochar(stations_info["ID"].astype(s_type).values)

            station_name = ds_out.createVariable("station_id", "c", (station_dim, "nchars"))
            station_name[:] = stringtochar(stations_info["NO"].astype(s_type).values)

            t_var_out = ds_out.createVariable(varnames["time"], t_var_in.datatype, t_var_in.dimensions)
            t_var_out.setncatts({key: t_var_in.getncattr(key) for key in t_var_in.ncattrs()})
            t_ref = num2date(0, t_var_in.units, t_var_in.calendar)

            units_inp = t_var_in.units.split("since")[0].strip().lower()
            mult_inp = get_sec_multiplier(units=units_inp)
            mult_out = get_sec_multiplier(units=out_time_units)

            t_var_out.units = f"{out_time_units} since {t_ref.strftime(reftime_format)}"
            t_var_out[:] = t_var_in[:] * mult_inp // mult_out

            for vn in ds_inp.variables:
                v = ds_inp[vn]
                if v.name in [varnames["time"], ]:
                    continue

                dimensions = (station_dim, )
                query = (i_arr, j_arr)
                if varnames["time"] in v.dimensions:
                    dimensions = (v.dimensions[0], ) + dimensions
                    query = (slice(None), ) + query

                v_out = ds_out.createVariable(v.name, v.datatype, dimensions=dimensions)
                assert isinstance(v_out, netCDF4.Variable)
                v_out.setncatts({key: v.getncattr(key) for key in v.ncattrs()})
                print(vn, v[:][query].shape)
                v_out[:] = v[:][query]


def main():
    args = read_cmd_args()
    convert(args.inp, args.out,
            obs.read_station_metadata(args.obs), transpose_index=args.transpose_index)


def test():
    inp = Path("/home/olh001/Bash/gdsps_grib2_for_mf/data/output_grdtype_O/netcdf/gdsps_2015032201000000_2015032300000000.nc")
    out = Path("data/test_nc_grid_to_points.nc")
    _obs = Path("/home/olh001/Python/obs_to_grid_mapping/resps/resps_1_12_MF.obs")
    convert(inp, out,
            obs.read_station_metadata(_obs), transpose_index=True)


if __name__ == '__main__':
    main()
    # test()
