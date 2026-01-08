#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Nov 26 11:05:45 2025

@author: imchugh
"""
###############################################################################
### BEGIN IMPORTS ###
###############################################################################

import json
import pandas as pd

import gsheets_api_client as gsac

###############################################################################
### END IMPORTS ###
###############################################################################


###############################################################################
### BEGIN INITS ###
###############################################################################

CONFIGS_FILE = 'configs.json'
INPUT_FOLDER_ID = '1sSdrC4ukE52MzHQWQ9fD5SSA3_25_tbH'
OUTPUT_FOLDER_ID = '1rU6jZbNzOLBStdZIEH-twN2ZhKdbFAbm'
PIXEL_PAD = {'mult': 7, 'offset': 10}
LONG_COLS = ['description', 'Site history', 'purpose', 'vegetation']
LONG_COL_SIZE_PXL = 400

with open(CONFIGS_FILE) as f:
    CONFIGS = json.load(f)

###############################################################################
### END INITS ###
###############################################################################


###############################################################################
### BEGIN FUNCTIONS ###
###############################################################################

# -----------------------------------------------------------------------------


def aggregate_sheets():
    """
    Get the content of the site-specific google sheets in the directory and
    aggregate.

    Returns:
        dataframe containing the aggregated content.

    """

    # Get the list of spreadsheets
    files = gsac.get_sheet_ids(folder_id=INPUT_FOLDER_ID)

    # Get the file content for each
    df_list = []
    for file in files:
        sheet_info = gsac.get_sheet_content(
            sheet_id=file['id'],
            tab_range='Metadata'
        )
        df_list.append(
            pd.DataFrame(
                data=sheet_info['values'][2:],
                columns=['Field', sheet_info['values'][1][1]]
            )
            .set_index('Field')
            .squeeze()
        )

    # Concatenate all results, order, format and rename to DSA names
    df = (
        pd.concat(df_list, axis=1)
        .fillna('')
        .replace('<br/>', '\n')
        .rename_axis(None)
        )
    df = df[sorted(df.columns)]
    df = df.T.rename_axis('Site name')
    rename_dict = {
        value: key for key, value in CONFIGS['FIELD_ALIASES'].items()
        }
    df = df.reset_index().rename(rename_dict, axis=1).set_index(keys='name')
    return df
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------


def aggregate_mod_time():

    # Get the list of spreadsheets
    files = gsac.get_sheet_ids(folder_id=INPUT_FOLDER_ID)

    # Get the mod info
    mod_dict = {}
    for file in files:
        mod_info = gsac.get_sheet_mod_metadata(sheet_id=file['id'])
        site = mod_info.pop('name')
        mod_info.pop('id')
        mod_dict[site] = mod_info

    return mod_dict
# -----------------------------------------------------------------------------

# -----------------------------------------------------------------------------


def write_aggregated_sheet():

    df = aggregate_sheets()
    df = df.reset_index()

    sheet_id = gsac.create_sheet(
        file_name='aggregated_site_metadata',
        folder_id=OUTPUT_FOLDER_ID
        )

    max_len = df.iloc[:, 0].astype(str).map(len).max()
    max_len = max_len * PIXEL_PAD['mult'] + PIXEL_PAD['offset']
    tab_formatter = [
        gsac._get_col_width_formatter(
            tab_id=0, start=0, end=len(df.columns) + 1, n_px=max_len
            )
        ]
    tab_formatter += [
        gsac._get_col_width_formatter(
            tab_id=0,
            start=df.columns.get_loc(col),
            end=df.columns.get_loc(col) + 1,
            n_px=LONG_COL_SIZE_PXL
            )
        for col in LONG_COLS
        ]
    tab_formatter += [
        gsac._get_wrap_text_formatter(
            tab_id=0
            ),
        gsac._get_bold_formatter(
            tab_id=0, start_row_idx=0, end_row_idx=1
            )
        ]

    # Do batch update
    gsac.do_batch_update(
        sheet_id=sheet_id,
        body={'requests': tab_formatter}
    )

    # Write data
    gsac.write_info_to_sheet(
        sheet_id=sheet_id,
        tab_name='Sheet1',
        data=df
        )
# -----------------------------------------------------------------------------

###############################################################################
### END FUNCTIONS ###
###############################################################################
