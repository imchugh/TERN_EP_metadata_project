#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Nov  7 12:25:07 2025

@author: imchugh

Module to build individual site google sheets inside a google drive folder.
Note:
    * the sheets api can't parse embedded images - we want these in the
    site-specific output sheets so we create a copy of a template sheet
    containing the requisite explanatory tabs, and then add the metadata for
    that site to a new tab without having to parse the images.'
"""

###############################################################################
### BEGIN IMPORTS ###
###############################################################################

import datetime as dt
import json
import pandas as pd

from itertools import groupby

import gsheets_api_client as gsac
import SILO_tools as silot

###############################################################################
### END IMPORTS ###
###############################################################################


###############################################################################
### BEGIN INITS ###
###############################################################################

METADATA_SHEET_ID = '1r7kinQCkOltj8HpWzNHVW8pZCkoFmkOGXbJ3tNYc_mA'
METADATA_TAB_RANGE = 'Data'
TEMPLATE_SHEET_ID = '1kZ6bxteNhfw4rjOyMDAJcUSI3gBPqlUueZJiPnO5t9U'
TEMPLATE_TAB_RANGE = 'Header definitions'
TARGET_FOLDER_ID = '1sSdrC4ukE52MzHQWQ9fD5SSA3_25_tbH'
CONFIGS_FILE = 'configs.json'
XL_EPOCH = dt.date(1899, 12, 30)
DATE_FORMAT = '%Y-%m-%d'
PIXEL_PAD = {'mult': 7, 'offset': 10}
NUMBER_ROWS = [
    9, 10, 11, 12, 14, 16, 18, 19, 22, 23, 25, 26, 27, 28, 29, 30, 31
]
SILO_START = '20000101'
SILO_FINISH = '20241231'

with open(CONFIGS_FILE) as f:
    CONFIGS = json.load(f)

###############################################################################
### END INITS ###
###############################################################################


###############################################################################
### BEGIN CLASSES ###
###############################################################################

# ------------------------------------------------------------------------------
class MetaDataSheetHandler():
    """Class that collects metadata from an existing google sheet in the dsa
    format and can be used to generate site-specific metadata sheets.
    """

    # --------------------------------------------------------------------------
    def __init__(self) -> None:
        """
        Initialise the class with the data and the explanatory fields.

        Returns:
            None.

        """

        self._get_metadata()
        self._get_explainer()
    # --------------------------------------------------------------------------

    # --------------------------------------------------------------------------
    def _get_metadata(self):
        """
        Get the metadata from the sheet and load into a dataframe, then assign
        as class attr.

        Returns:
            None.

        """

        # Get the data and put into a dataframe
        rslt = gsac.get_sheet_content(
            sheet_id=METADATA_SHEET_ID,
            tab_range=METADATA_TAB_RANGE
        )
        data = pd.DataFrame(data=rslt['values'][1:], columns=rslt['values'][0])

        # Format dataframe
        data = data.rename(CONFIGS['FIELD_ALIASES'], axis=1)
        data.index = pd.Index(
            data=[_parse_names(name) for name in data['Site name']],
            name='Site name'
        )
        data = data.drop('Site name', axis=1)
        data['Date commissioned'] = (
            data['Date commissioned'].apply(_format_dates)
        )
        data = data.replace('<br />', '', regex=True)
        self.data = data
    # --------------------------------------------------------------------------

    # --------------------------------------------------------------------------
    def _get_explainer(self):
        """
        Get the explanatory fields from the template sheet and load into
        dataframe, then assign as class attr.

        Returns:
            None.

        """

        # Get the data and put into a dataframe
        rslt = gsac.get_sheet_content(
            sheet_id=TEMPLATE_SHEET_ID,
            tab_range=TEMPLATE_TAB_RANGE
        )

        # Format dataframe
        self.explainer = (
            pd.DataFrame(
                data=rslt['values'][1:],
                columns=rslt['values'][0])
            .set_index('Information')
        )
    # --------------------------------------------------------------------------

    # --------------------------------------------------------------------------
    def get_formatted_site_metadata(self, site: str) -> pd.Series:
        """
        Grab the data for a single site.

        Args:
            site: name of site.

        Returns:
            series containing site info.

        """

        df = self.data.reset_index()
        s = (df[df['Site name'] == site]).squeeze()
        s.name = None
        add_fields = [x for x in self.explainer.index if not x in s.index]
        s = pd.concat([s, pd.Series(index=pd.Index(add_fields))])
        s = s[self.explainer.index]
        s.name = 'Current value'
        sda = silot.SILODataAnalyser(
            latitude=s['True latitude'],
            longitude=s['True longitude'],
            start_date=SILO_START,
            finish_date=SILO_FINISH
        )
        s['Mean annual temperature'] = round(sda.get_mean_annual_temp(), 1)
        s['Mean annual precipitation'] = round(sda.get_mean_annual_precip(), 1)
        s['Geodetic datum'] = 'WGS84'
        return s
    # --------------------------------------------------------------------------

    # --------------------------------------------------------------------------
    def write_site_data_to_sheet(self, site: str) -> None:
        """
        Take the formatted site-specific data and write into a single sheet
        that includes the explanatory info from the template sheet.

        Args:
            site: name of site.

        Returns:
            None.

        """

        # Inits
        tab_name = 'Metadata'

        # Get the data
        data = (
            self.get_formatted_site_metadata(site=site)
            .reset_index()
            .fillna('')
        )

        # Copy template sheet and get ID
        new_sheet_info = gsac.copy_sheet(
            sheet_id=TEMPLATE_SHEET_ID,
            dest_folder_id=TARGET_FOLDER_ID,
            new_sheet_name=site
        )
        new_sheet_id = new_sheet_info['id']

        # Create a formatting dictionary to create the new tab
        # (cannot be done in a single api call), then generate tab and get ID
        new_sheet_request = gsac._create_tab_request(
            tab_name='Metadata',
            row_count=len(data),
            col_count=len(data.columns)
        )
        new_tab_info = gsac.do_batch_update(
            sheet_id=new_sheet_id,
            body={'requests': [new_sheet_request]}
        )
        new_tab_id = (
            new_tab_info['replies'][0]['addSheet']['properties']['sheetId']
        )

        # Do formatting
        max_len = data.iloc[:, 0].astype(str).map(len).max()
        max_len = max_len * PIXEL_PAD['mult'] + PIXEL_PAD['offset']
        tab_formatter = [
            gsac._get_col_width_formatter(
                tab_id=new_tab_id, start=0, end=1, n_px=max_len
            ),
            gsac._get_col_width_formatter(
                tab_id=new_tab_id, start=1, end=2, n_px=max_len*2
            ),
            gsac._get_wrap_text_formatter(
                tab_id=new_tab_id
            ),
            gsac._get_bold_formatter(
                tab_id=new_tab_id, start_row_idx=0, end_row_idx=1
            )
        ]

        # Do dropdowns
        run_dict = {
            'IGBP':
                data.index[data.Information == 'IGBP vegetation class'].item()
                + 1,
            'Koeppen':
                data.index[data.Information == 'Koeppen climate class'].item()
                + 1,
            'Tower type':
                data.index[data.Information == 'Tower type'].item() + 1
        }
        for dropdown, idx in run_dict.items():
            tab_formatter += [
                gsac._get_data_validation_formatter(
                    tab_id=new_tab_id,
                    start_row_idx=idx,
                    end_row_idx=idx + 1,
                    start_col_idx=1,
                    end_col_idx=2,
                    rule='dropdown',
                    options=CONFIGS['DROPDOWNS'][dropdown]
                )
            ]

        # Add date formatting
        date_row_idx = (
            data.index[data.Information == 'Date commissioned'].item() + 1
        )
        tab_formatter += [
            gsac._get_data_validation_formatter(
                tab_id=new_tab_id,
                start_row_idx=date_row_idx,
                end_row_idx=date_row_idx + 1,
                start_col_idx=1,
                end_col_idx=2,
                rule='date'
            )
        ]

        # Add data validation to number cells
        for int_set in group_consecutive(nums=NUMBER_ROWS):
            tab_formatter += [
                gsac._get_data_validation_formatter(
                    tab_id=new_tab_id,
                    start_row_idx=int_set[0],
                    end_row_idx=int_set[-1] + 1,
                    start_col_idx=1,
                    end_col_idx=2,
                    rule='number'
                )
            ]

        # Add help for units for numeric fields
        for item, units in CONFIGS['UNITS'].items():
            item_loc = data.index[data.Information == item].item()
            tab_formatter += [
                gsac._get_cell_help_formatter(
                    tab_id=new_tab_id,
                    start_row_idx=item_loc + 1,
                    end_row_idx=item_loc + 2,
                    start_col_idx=1,
                    end_col_idx=2,
                    msg=f'Units = {units}'
                )
            ]

        # Lock the FLUXNET ID
        item_loc = data.index[data.Information == 'Fluxnet code'].item()
        tab_formatter += [
            gsac._get_range_lock_formatter(
                tab_id=new_tab_id,
                start_row_idx=item_loc + 1,
                end_row_idx=item_loc + 2,
                start_col_idx=1,
                end_col_idx=2,
            )
        ]

        # Reorder the tabs
        tab_formatter.append(
            gsac._get_tab_order_formatter(
                tab_id=new_tab_id, tab_idx=0
            )
        )

        # Do batch update
        gsac.do_batch_update(
            sheet_id=new_sheet_id,
            body={'requests': tab_formatter}
        )

        # Write the content
        gsac.write_info_to_sheet(
            sheet_id=new_sheet_id,
            tab_name=tab_name,
            data=data
        )
    # --------------------------------------------------------------------------

# ------------------------------------------------------------------------------

###############################################################################
### END CLASSES ###
###############################################################################


###############################################################################
### BEGIN FUNCTIONS ###
###############################################################################

# ------------------------------------------------------------------------------
def _parse_names(label: str) -> str:
    """
    Rebuild labels to match standard site names.

    Args:
        label: the site name label to edit.

    Returns:
        the edited site name label.

    """

    new_label = label.replace(' Flux Station', '')
    try:
        out_label = CONFIGS['SITE_ALIASES'][new_label]
    except KeyError:
        out_label = new_label
    return out_label.replace(' ', '')
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------


def _format_dates(date_str: str) -> str:
    """
    Format dates to Y-m-d

    Args:
        date_str: the date string to convert.

    Returns:
        formatted s=date string.

    """

    try:
        return (
            (XL_EPOCH + dt.timedelta(days=int(date_str)))
            .strftime(DATE_FORMAT)
        )
    except ValueError:
        return ''
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------


def _format_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Format source data.

    Args:
        df: dataframe to format.

    Returns:
        df: formatted dataframe.

    """

    df['Date commissioned'] = (
        df['Date commissioned'].dt.strftime('%Y-%m-%d')
    )
    df = df.replace('<br />', '', regex=True)
    return df
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------


def group_consecutive(nums: list) -> list:
    """
    Find consecutive sets of rows and group (sheets api formatting requires this)

    Args:
        nums: list of row numbers.

    Returns:
        groups: list of number groups.

    """

    groups = []
    for _, g in groupby(enumerate(nums), key=lambda x: x[0] - x[1]):
        groups.append([x[1] for x in g])
    return groups
# ------------------------------------------------------------------------------

###############################################################################
### END FUNCTIONS ###
###############################################################################
