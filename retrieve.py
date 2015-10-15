import re
import requests
import bs4
import xlrd
import time
import datetime
import unicodecsv as csv

# import argparse
# from multiprocessing import Pool

__author__ = 'whchen'

input_file_path_base    = '/Users/whchen/Desktop/'
input_file_path_name    = 'fire_events.xls'
input_file_path_full    = input_file_path_base + input_file_path_name
output_file_path_base   = input_file_path_base
output_file_path_name   = input_file_path_name.split('.')[0] + '_result.csv'
output_file_path_full   = output_file_path_base + output_file_path_name

search_url_base     = 'http://tvnews.vanderbilt.edu/tvn-processquery.pl?'
search_code         = 'tvn'
search_keyword      = 'nuclear'
search_qualifier    = 'word'
search_submit       = '%A0%A0%A0Search%A0%A0'
search_network      = ''
search_comm_exclude = 'on'
search_reporters    = ''
search_sort_order   = 'Forward'
search_RC           = ''
search_url_filter_l = 'code=' + search_code + '&Quick=' + search_keyword \
                      + '&searchqualifier=' + search_qualifier + '&submit=' + search_submit
search_url_filter_r = '&Network=' + search_network + '&ExcludeCommercials=' + search_comm_exclude \
                      + '&reporters=' + search_reporters + '&SortOrder=' + search_sort_order + '&RC=' + search_RC

csv_headers = ['Headline', 'Date', 'Duration', 'Network', 'Type', 'Abstract']


def get_search_keywords_list():

    xls_content = xlrd.open_workbook(input_file_path_full).sheets()[0]
    xls_rows = xls_content.nrows
    search_keywords_list = []

    for xls_row in range(2, xls_rows):
        xls_value = re.sub('\d', '', xls_content.cell(xls_row, 1).value).rstrip().split(' ')
        search_keywords_list.append('+'.join(xls_value))

    return sorted(set(search_keywords_list))


def get_search_items_date_boundary(input_file_path_full):

    xls_content = xlrd.open_workbook(input_file_path_full).sheets()[0]
    xls_rows = xls_content.nrows
    search_items_date_boundary = []

    for xls_row in range(1, xls_rows):
        search_item_date_boundary = {}
        xls_lower_date = xls_content.cell(xls_row, 3).value.lstrip().split(' ')
        xls_upper_date = xls_content.cell(xls_row, 4).value.lstrip().split(' ')
        search_item_date_boundary['Month'] = \
            datetime.datetime.strptime(xls_lower_date[0], '%B').strftime('%m').lstrip('0')
        search_item_date_boundary['Date'] = xls_lower_date[1].rstrip(',')
        search_item_date_boundary['Year'] = xls_lower_date[2]
        search_item_date_boundary['EndMonth'] =  \
            datetime.datetime.strptime(xls_upper_date[0], '%B').strftime('%m').lstrip('0')
        search_item_date_boundary['EndDay'] = xls_upper_date[1].rstrip(',')
        search_item_date_boundary['EndYear'] = xls_upper_date[2]
        search_items_date_boundary.append(search_item_date_boundary)

    return search_items_date_boundary


def get_search_results(search_url_full):

    search_results_page_links = get_search_results_page_links(search_url_full)

    if len(search_results_page_links) == 1 and search_results_page_links[0] == 'single':
        search_result_data = get_search_result_data('single', search_url_full)
        write_search_result_data(search_result_data)
        print(search_result_data)
    elif len(search_results_page_links) == 1 and search_results_page_links[0] == 'none':
        search_result_data = {}
        print(search_result_data)
    else:
        for search_results_page_link in search_results_page_links:
            print(search_results_page_link)
            search_result_items = get_search_results_items(search_results_page_link)
            for search_result_item in search_result_items:
                search_result_item_link = get_search_result_item_link(search_result_item)
                if search_result_item_link is not None:
                    search_result_data = get_search_result_data('list', search_result_item_link)
                    if len(search_result_data):
                        write_search_result_data(search_result_data)
                        print(search_result_data)


def write_search_result_data(search_result_data):

    with open(output_file_path_full, 'a+') as csv_file:
        csv_file = csv.DictWriter(csv_file, csv_headers, extrasaction='ignore')
        csv_file.writerow(search_result_data)


def get_search_results_page_links(search_url_full):

    response = requests.get(search_url_full)
    soup = bs4.BeautifulSoup(response.text, "html.parser")
    search_results_page_links = []
    search_result_page_lists = soup.select('#ResultPageNumbersAll')
    search_result_page_title = soup.title.get_text()

    if len(search_result_page_lists):
        search_results_page_links.append(search_url_full)
        search_result_page_links_list = search_result_page_lists[0].findAll('a')
        for page_number in range(len(search_result_page_links_list) - 1):
            search_results_page_links.append(search_result_page_links_list[page_number].get('href'))
    elif search_result_page_title.find('search results') == -1:
        if search_result_page_title.find('No request records') == -1:
            search_results_page_links.append('single')
        else:
            search_results_page_links.append('none')
    else:
        search_results_page_links.append(search_url_full)

    return search_results_page_links


def get_search_results_items(search_results_page_link):

    response = requests.get(search_results_page_link)
    soup = bs4.BeautifulSoup(response.text, "html.parser")

    return soup.select('table:nth-of-type(2) tr')


def get_search_result_item_link(search_result_item):

    tds = search_result_item.findAll('td')
    if len(tds):
        search_result_item_link = tds[2].find('a').get('href').replace('code=&', 'code=tvn&')
        return search_result_item_link
    else:
        return None


def get_search_result_data(page_type, search_result_item_link):

    response = requests.get(search_result_item_link)
    soup = bs4.BeautifulSoup(response.text, "html.parser")
    search_result_data = {}

    h1_css_selector = 'h1:nth-of-type(2)'
    program_sum = soup.select(h1_css_selector)[0].get_text().split(' for ')
    if len(program_sum) == 2:
        search_result_data['Network'] = program_sum[0][0:3]
        search_result_data['Date'] = time.strftime('%m/%d/%Y', time.strptime(program_sum[1], '%A, %b %d, %Y'))
    for info_row in range(1, len(soup.select('table:nth-of-type(2) tr'))+1):
        search_result_data['Headline'] = soup.select('h2 strong')[0].get_text().encode('ascii', 'ignore')
        search_result_data['Video'] = ''
        th_css_selector = 'table:nth-of-type(2) tr:nth-of-type(' + str(info_row) + ') th'
        td_css_selector = 'table:nth-of-type(2) tr:nth-of-type(' + str(info_row) + ') td'
        if len(soup.select(th_css_selector)):
            th_col_name = soup.select(th_css_selector)[0].get_text()
            if th_col_name == 'Date:':
                search_result_data['Date'] = time.strftime('%m/%d/%Y', time.strptime(
                    soup.select(td_css_selector + ' strong')[0].get_text(), '%b %d, %Y'))
            elif th_col_name == 'Network:':
                search_result_data['Network'] = soup.select(td_css_selector)[0].get_text()
            elif th_col_name == 'Abstract:':
                search_result_data['Abstract'] = \
                    re.sub(r'\s{2,}', ' ', soup.select(td_css_selector)[0].get_text().strip().encode('ascii', 'ignore'))
            elif th_col_name == 'Broadcast Type:':
                search_result_data['Type'] = soup.select(td_css_selector + ' strong')[0].get_text()
            elif th_col_name == 'Program Time:':
                program_time = soup.select(td_css_selector)[0].get_text().encode('ascii', 'ignore')
                search_result_data['Begin'] = program_time.split(' - ')[0].replace('\xa0', ' ')
                search_result_data['End'] = program_time.split(' - ')[1].split('.')[0].replace('\xa0', ' ')
                search_result_data['Duration'] = program_time.split('\r\n')[1]
    return search_result_data


def get_search_result_abs(search_result_item_link):

    response = requests.get(search_result_item_link)
    soup = bs4.BeautifulSoup(response.text, "html.parser")

    return soup.select('table:nth-of-type(2) tr:nth-of-type(1) td')[0].get_text()

if __name__ == '__main__':

    search_items_date_boundary = get_search_items_date_boundary(input_file_path_full)

    with open(output_file_path_full, 'w') as csv_file:
        csv_file = csv.DictWriter(csv_file, csv_headers)
        csv_file.writeheader()

    start_time = time.time()
    for search_item_date_boundary in search_items_date_boundary:
        search_url_filter_m = ''
        search_url_filter_m += '&Month=' + search_item_date_boundary['Month'] \
                               + '&Date=' + search_item_date_boundary['Date'] \
                               + '&Year=' + search_item_date_boundary['Year'] \
                               + '&EndMonth=' + search_item_date_boundary['EndMonth']\
                               + '&EndDay=' + search_item_date_boundary['EndDay'] \
                               + '&EndYear=' + search_item_date_boundary['EndYear']
        search_url_full = search_url_base + search_url_filter_l + search_url_filter_m + search_url_filter_r
        get_search_results(search_url_full)
    end_time = time.time()

    print('Running Time: %f seconds' % (end_time - start_time))
    print('Goodbye')
