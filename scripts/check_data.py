import os
from sdg.open_sdg import open_sdg_check

validation_successful = open_sdg_check(config='data_config.yml')
if not validation_successful:
    raise Exception('There were validation errors. See output above.')
