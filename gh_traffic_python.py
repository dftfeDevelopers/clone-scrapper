import dateutil
import argparse
import csv
import os
from collections import OrderedDict
from datetime import datetime
from datetime import date
from datetime import timedelta
import getpass
import requests


"""
TODO:
- DONE 2016-09-05: Get all repos optionally
- DONE 2016-09-06: Pretty format JSON response
- DONE 2016-09-30: Save as CSV output
- DONE 2017-02-24: Fixed path to savefiles

"""
# Globals
current_timestamp = str(datetime.now().strftime('%Y-%m-%d-%Hh-%Mm'))  # was .strftime('%Y-%m-%d'))
path = os.path.dirname(os.path.abspath(__file__))
top_dir = os.path.split(path)[0]
csv_file_name = top_dir+'/data/' + current_timestamp + '-traffic-stats.csv'

def send_request(resource, auth, repo=None, headers=None, desired_data='views'):
    """Send request to Github API
    :param resource: string - specify the API to call
    :param auth: tuple - username-password tuple
    :param repo: string - if specified, the specific repository name
    :param headers: dict - if specified, the request headers
    :return: response - GET request response
    """

    # GET /repos/:owner/:repo/traffic/views <- from developer.github.com/v3/repos/traffic/#views
    base_url = 'https://api.github.com/repos/'
    url = base_url + 'dftfeDevelopers/' + repo + '/traffic/' + desired_data
    response = requests.get(url, auth=auth)
    return response


def timestamp_to_utc(timestamp):
    """Convert unix timestamp to UTC date
    :param timestamp: int - the unix timestamp integer
    :return: utc_data - the date in YYYY-MM-DD format
    """
    # deprecated pre-10/31/2016
    timestamp = int(str(timestamp)[0:10])
    utc_date = datetime.datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d')
    # utc_date = timestamp[0:10]
    return utc_date


def json_to_table(repo, json_response):
    """Parse traffic stats in JSON and format into a table
    :param repo: str - the GitHub repository name
    :param json_response: json - the json input
    :return: table: str - for printing on command line
    """
    repo_name = repo
    total_views = str(json_response['count'])
    total_uniques = str(json_response['uniques'])

    dates_and_views = OrderedDict()
    detailed_views = json_response['views']
    for row in detailed_views:
        # utc_date = timestamp_to_utc(int(row['timestamp']))
        utc_date = str(row['timestamp'][0:10])
        dates_and_views[utc_date] = (str(row['count']), str(row['uniques']))

    """Table template
    repo_name
    Date        Views   Unique visitors
    Totals      #       #
    date        #       #
    ...         ...     ...
    """
    table_alt = repo_name + '\n' +\
        '# Total Views:' + '\t' + total_views + '\n' + '# Total Unique:' + '\t' + total_uniques + '\n' +\
        'Date' + '\t\t' + 'Views' + '\t' + 'Unique visitors' + '\n'

    table = repo_name + '\n' +\
        'Date' + '\t\t' + 'Views' + '\t' + 'Unique visitors' + '\n' +\
        'Totals' + '\t\t' + total_views + '\t' + total_uniques + '\n'
    for row in dates_and_views:
        table += row + '\t' + dates_and_views[row][0] + '\t' + dates_and_views[row][1] + '\n'

    return table


def write_text_file(repo, json_visits, json_clones, file_name):
    """Store the traffic stats as a CSV, with schema:
    repo_name, date, views, unique_visitors

    :param repo: str - the GitHub repository name
    :param json_response: json - the json input
    :return:
    """
    repo_name = repo
    # # Not writing Totals stats into the CSV to maintain normalization
    # total_views = str(json_response['count'])
    # total_uniques = str(json_response['uniques'])

    dates_and_views = OrderedDict()
    detailed_views = json_visits['views']
    for row in detailed_views:
        # utc_date = timestamp_to_utc(int(row['timestamp']))
        utc_date = str(row['timestamp'][0:13])

        #utc_date_obj = datetime.strptime(row['timestamp'][0:13], '%Y-%m-%dT%H')

        dates_and_views[utc_date] = (str(row['count']), str(row['uniques']))

    dates_and_clones = OrderedDict()
    detailed_clones = json_clones['clones']
    for row in detailed_clones:
        # utc_date = timestamp_to_utc(int(row['timestamp']))
        utc_date = str(row['timestamp'][0:13])
        dates_and_clones[utc_date] = (str(row['count']), str(row['uniques']))

    f = open(file_name, 'a')
    output_string = repo_name + " Daily Statistics:\nDate\t\tVisits\t\tUnique Visits\tClones\t\tUnique Clones\n"
    f.write(output_string)

    total_views = 0
    total_uviews = 0
    total_clones = 0
    total_uclones = 0

    utc_date_obj = date.today()

    # Loop over the past 7 days
    for i in range(-7, 0):
        target_date = utc_date_obj+timedelta(days=i)
        target_date_str = target_date.strftime('%Y-%m-%dT%H')
        if target_date_str in dates_and_views:
            views = dates_and_views[target_date_str][0]
            uviews = dates_and_views[target_date_str][1]
        else:
            views = 0
            uviews = 0

        if target_date_str in dates_and_clones:
            clones = dates_and_clones[target_date_str][0]
            uclones = dates_and_clones[target_date_str][1]
        else:
            clones = 0
            uclones = 0

        daily_stats = target_date_str + "\t" + str(views) + "\t\t" + str(uviews) + "\t\t" + str(clones) + "\t\t" + str(uclones) + "\n"

        f.write(daily_stats)
        total_views += int(views)
        total_uviews += int(uviews)
        total_clones += int(clones)
        total_uclones += int(uclones)

    output_string = "\n" + repo_name + "  Total Statistics:\n\t\tVisits\t\tUnique Visits\tClones\t\tUnique Clones\n"
    f.write(output_string)

    output_string = "\t\t" + str(total_views) + "\t\t" + str(total_uviews) + "\t\t" + str(total_clones) + "\t\t" + str(total_uclones) + "\n\n"
    f.write(output_string)
    f.close()

    return ''


def main(username):
    """Query the GitHub Traffic API
    :param username: string - GitHub username
    :param repo: string - GitHub user's repo name or by default 'ALL' repos
    :param save_csv: string - Specify if CSV log should be saved
    :return:
    """
    username = username.strip()
    auth_pair = (username,os.environ['GH_CLONE_SCRAPPER_TOKEN'])
    traffic_headers = {'Accept': 'application/vnd.github.spiderman-preview'}

    save_txt = 'save_txt'
    file_name = 'github_stats.txt'

    repo_list = ["dftfe"]

    if save_txt == 'save_txt':
        f = open(file_name, 'a')
        output_string = "\n--------- \nGitHub statistics for the past week as of "
        output_string = output_string + current_timestamp + ": \n \n"
        f.write(output_string)
        f.close()

    for repo_name in repo_list:
        repo_str = repo_name
        traffic_response = send_request('traffic', auth_pair, repo_str, traffic_headers, 'views')
        traffic_response = traffic_response.json()
        clone_response = send_request('clones', auth_pair, repo_str, traffic_headers, 'clones')
        clone_response = clone_response.json()

        if save_txt == 'save_txt':
            write_text_file(repo_name, traffic_response, clone_response, file_name)

    return ''


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('username', help='Github username')
    args = parser.parse_args()
    main(args.username)

