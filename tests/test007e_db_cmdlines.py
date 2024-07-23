#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import rpt_dosi.utils as utils
import rpt_dosi.db as rtpdb
from rpt_dosi.utils import start_test, stop_test, end_tests

if __name__ == "__main__":
    # folders
    data_folder, ref_folder, output_folder = utils.get_tests_folders("test007e")
    ref_folder = ref_folder / "ref_json"
    print(f"Input data folder = {data_folder}")
    print(f"Ref data folder = {ref_folder}")
    print(f"Output data folder = {output_folder}")

    # cmd lines tools
    # DONE rpt_db_info

    # create a db
    input_db = output_folder/"test007e.json"
    log_file = output_folder/"test007e.log"
    rtpdb.create_test_db(data_folder, input_db)

    # test (only check it runs without fail)
    start_test(f'cmd line rpt_db_info')
    cmd = f"rpt_db_info {input_db} -v > {log_file}"
    b = utils.run_cmd(cmd, data_folder / "..")
    stop_test(b, f'cmd')

    cmd = f"rpt_db_info {input_db} -vv > {log_file}"
    b = utils.run_cmd(cmd, data_folder / "..")
    stop_test(b, f'cmd')

    cmd = f"rpt_db_info {input_db} -vvv > {log_file}"
    b = utils.run_cmd(cmd, data_folder / "..")
    stop_test(b, f'cmd')

    start_test(f'cmd line rpt_db_info check')
    cmd = f"rpt_db_info {input_db} -c"
    b = utils.run_cmd(cmd, data_folder / "..")
    stop_test(b, f'cmd')

    start_test(f'cmd line rpt_db_info sync')
    cmd = f"rpt_db_info {input_db} -s auto"
    b = utils.run_cmd(cmd, data_folder / "..")
    stop_test(b, f'cmd')

    # end
    end_tests()
