# -*- coding: utf-8 -*-
"""
Spyder Editor

This is a temporary script file.
"""

###############################################################################
### BEGIN IMPORTS ###
###############################################################################


import datetime as dt
import json
import pandas as pd
import urllib.request
import urllib.parse

###############################################################################
### END IMPORTS ###
###############################################################################


###############################################################################
### BEGIN INITS ###
###############################################################################

API_URL = 'https://www.longpaddock.qld.gov.au/cgi-bin/silo'
USER = 'imchugh@unimelb.edu.au'
PASS = 'apirequest'
VAR_CODES = 'RXN'
DATE_FORMAT = '%Y%m%d'

###############################################################################
### END INITS ###
###############################################################################


###############################################################################
### BEGIN CLASSES ###
###############################################################################

# ------------------------------------------------------------------------------
class SILODataAnalyser():

    # --------------------------------------------------------------------------
    def __init__(
            self,
            latitude: int | float, longitude: int | float, start_date: str,
            finish_date: str, var_codes: str = VAR_CODES
    ) -> None:
        """
        Get location and dates, request and format data.

        Args:
            latitude: latitude of location.
            longitude: longitude of location.
            start_date: first date for which to retrieve data.
            finish_date: last date for which to retrieve data.

        Returns:
            None.

        """

        self.latitude = latitude
        self.longitude = longitude
        self.start_date = dt.datetime.strptime(start_date, DATE_FORMAT)
        self.finish_date = dt.datetime.strptime(finish_date, DATE_FORMAT)
        url = _build_url(
            lat=latitude, lon=longitude, start=start_date, finish=finish_date,
            var_codes=var_codes
        )
        self.data = _get_data(url=url)
    # --------------------------------------------------------------------------

    # --------------------------------------------------------------------------
    def get_mean_annual_precip(self) -> float:
        """
        Sum the daily rain totals to annual total.

        Returns:
            the annual total.

        """

        return round(
            self.data.daily_rain.groupby(self.data.index.year).sum().mean(),
            2
        )
    # --------------------------------------------------------------------------

    # --------------------------------------------------------------------------
    def get_mean_annual_max_temp(self) -> float:
        """
        Average the daily max temp to annual mean.

        Returns:
            the annual mean max.

        """

        return self.data.max_temp.groupby(self.data.index.year).mean().mean()
    # --------------------------------------------------------------------------

    # --------------------------------------------------------------------------
    def get_mean_annual_min_temp(self) -> float:
        """
        Average the daily min temp to annual mean.

        Returns:
            the annual mean min.

        """

        return self.data.min_temp.groupby(self.data.index.year).mean().mean()
    # --------------------------------------------------------------------------

    # --------------------------------------------------------------------------
    def get_mean_annual_temp(self) -> float:
        """
        Average the daily minima and maxima to estimate annual mean.

        Returns:
            the annual mean.

        """

        return (
            (self.get_mean_annual_max_temp() + self.get_mean_annual_min_temp())
            / 2
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
def _get_data(url: str) -> pd.DataFrame:
    """
    Retrieve data from SILO servers.

    Args:
        url: formatted data retrieval url.

    Returns:
        df: formatted dataframe.

    """

    with urllib.request.urlopen(url) as remote:
        response = json.load(remote)
    data = []
    for line in response['data']:
        d = {'date': line['date']}
        d.update(
            {
                rec['variable_code']: rec['value'] for rec in line['variables']
            }
        )
        data.append(d)
    df = pd.DataFrame(data)
    df.index = pd.to_datetime(df.date)
    df = df.drop('date', axis=1)
    return df
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
def _build_url(
        lat: int | float, lon: int | float, start: str, finish: str,
        var_codes: str) -> str:
    """
    Build the parameter set and construct the url.

    Args:
        lat: latitude of location.
        lon: longitude of location.
        start: first date for which to retrieve data.
        finish: last date for which to retrieve data.
    Returns:
        the url.

    """

    params = {
        'format': 'json',
        'lat': str(lat),
        'lon': str(lon),
        'start': start,
        'finish': finish,
        'username': USER,
        'password': PASS,
        'comment': var_codes
    }
    return API_URL + '/DataDrillDataset.php?' + urllib.parse.urlencode(params)
# ------------------------------------------------------------------------------

###############################################################################
### END FUNCTIONS ###
###############################################################################
