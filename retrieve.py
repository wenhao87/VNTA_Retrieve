__author__ = 'whchen'

import re
import requests
import bs4
import xlrd
import time
import datetime
import argparse
from multiprocessing import Pool

file_path_base  = '/Users/whchen/Desktop/'
file_path_name  = 'fire_events.xls'
file_path_comp  = file_path_base + file_path_name

search_code         = 'tvn'
search_keyword      = 'nuclear'
search_qualifier    = 'word'
search_submit       = '%A0%A0%A0Search%A0%A0'
search_network      = ''
search_comm_exclude = 'on'
search_reporters    = ''
search_sort_order   = 'Forward'
search_RC           = ''

search_url_test     = 'http://tvnews.vanderbilt.edu/tvn-processquery.pl?code=tvn&Quick=nuclear&searchqualifier=word&submit=%A0%A0%A0Search%A0%A0&Month=2&Date=5&Year=2009&EndMonth=2&EndDay=17&EndYear=2009&Network=&ExcludeCommercials=on&reporters=&SortOrder=Forward&RC='
search_url_base     = 'http://tvnews.vanderbilt.edu/tvn-processquery.pl?'
search_url_filter_l = 'code=' + search_code + '&Quick=' + search_keyword \
                      + '&searchqualifier=' + search_qualifier + '&submit=' + search_submit
search_url_filter_r = '&Network=' + search_network + '&ExcludeCommercials=' + search_comm_exclude \
                      + '&reporters=' + search_reporters + '&SortOrder=' + search_sort_order + '&RC=' + search_RC

def get_search_keywords_list() :

    xls_content = xlrd.open_workbook(file_path_comp).sheets()[0]
    xls_nrows = xls_content.nrows
    search_keywords_list = []
    for xls_row in range(2, xls_nrows) :
        xls_value = re.sub('\d', '', xls_content.cell(xls_row, 1).value).rstrip().split(' ')
        search_keywords_list.append('+'.join(xls_value))

    return sorted(set(search_keywords_list))

def get_search_items_date_boundry(file_path_comp) :

    xls_content = xlrd.open_workbook(file_path_comp).sheets()[0]
    xls_nrows = xls_content.nrows
    search_items_date_boundry = []
    for xls_row in range(1, xls_nrows) :
        search_item_date_boundry = {}
        xls_lower_date = xls_content.cell(xls_row, 3).value.lstrip().split(' ')
        xls_upper_date = xls_content.cell(xls_row, 4).value.lstrip().split(' ')
        search_item_date_boundry['Month'] = datetime.datetime.strptime(xls_lower_date[0], '%B').strftime('%m').lstrip('0')
        search_item_date_boundry['Date'] = xls_lower_date[1].rstrip(',')
        search_item_date_boundry['Year'] = xls_lower_date[2]
        search_item_date_boundry['EndMonth'] =  datetime.datetime.strptime(xls_upper_date[0], '%B').strftime('%m').lstrip('0')
        search_item_date_boundry['EndDay'] = xls_upper_date[1].rstrip(',')
        search_item_date_boundry['EndYear'] = xls_upper_date[2]
        search_items_date_boundry.append(search_item_date_boundry)

    return search_items_date_boundry

def get_search_results(search_url_comp) :
    search_results_page_links = get_search_results_page_links(search_url_comp)
    if len(search_results_page_links) == 1 and search_results_page_links[0] == 'single' :
        search_result_data = get_search_result_data('single', search_url_comp)
        print(search_result_data)
    elif len(search_results_page_links) == 1 and search_results_page_links[0] == 'none' :
        search_result_data = {}
        print(search_result_data)
    else :
        for search_results_page_link in search_results_page_links :
            print(search_results_page_link)
            search_result_items = get_search_results_items(search_results_page_link)
            for search_result_item in search_result_items :
                search_result_item_link = get_search_result_item_link(search_result_item)
                if search_result_item_link is not None :
                    search_result_data = get_search_result_data('list', search_result_item_link)
                    if len(search_result_data):
                        print(search_result_data)

def get_search_results_page_links(search_url_comp) :

    response = requests.get(search_url_comp)
    soup = bs4.BeautifulSoup(response.text, "html.parser")
    search_results_page_links = []
    search_result_page_lists = soup.select('#ResultPageNumbersAll')
    search_result_page_title = soup.title.get_text()

    if len(search_result_page_lists) :
        search_results_page_links.append(search_url_comp)
        search_result_page_links_list = search_result_page_lists[0].findAll('a')
        for pagenumber in range(len(search_result_page_links_list) - 1) :
            search_results_page_links.append(search_result_page_links_list[pagenumber].get('href'))
    elif search_result_page_title.find('search results') == -1 :
        if search_result_page_title.find('No request records') == -1 :
            search_results_page_links.append('single')
        else: search_results_page_links.append('none')
    else :
        search_results_page_links.append(search_url_comp)

    return search_results_page_links

def get_search_results_items(search_results_page_link) :

    response = requests.get(search_results_page_link)
    soup = bs4.BeautifulSoup(response.text, "html.parser")

    return soup.select('table:nth-of-type(2) tr')

def get_search_result_item_link(search_result_item) :

    tds = search_result_item.findAll('td')
    if len(tds):
        search_result_item_link = tds[2].find('a').get('href').replace('code=&','code=tvn&')
        return search_result_item_link
    else :
        return None

def get_search_result_data(type, search_result_item_link) :

    response = requests.get(search_result_item_link)
    soup = bs4.BeautifulSoup(response.text, "html.parser")
    search_result_data = {}

    h1_css_selector = ''
    if type == 'single' :
        h1_css_selector = '#pageFrame h1'
    elif type == 'list' :
        h1_css_selector = 'h1:nth-of-type(2)'
    program_sum = soup.select(h1_css_selector)[0].get_text().split(' for ')
    if len(program_sum) == 2 :
        search_result_data['network'] = program_sum[0][0:3]
        search_result_data['date'] = time.strftime('%m/%d/%Y', time.strptime(program_sum[1], '%A, %b %d, %Y'))
    for info_row in range(1, len(soup.select('table:nth-of-type(2) tr'))+1) :
        search_result_data['title'] = soup.select('h2 strong')[0].get_text()
        search_result_data['video'] = ''
        th_css_selector = 'table:nth-of-type(2) tr:nth-of-type(' + str(info_row) + ') th'
        td_css_selector = 'table:nth-of-type(2) tr:nth-of-type(' + str(info_row) + ') td'
        if len(soup.select(th_css_selector)) :
            th_col_name = soup.select(th_css_selector)[0].get_text()
            if th_col_name == 'Date:' :
                search_result_data['date'] = time.strftime('%m/%d/%Y', time.strptime(
                    soup.select(td_css_selector + ' strong')[0].get_text(), '%b %d, %Y'))
            elif th_col_name == 'Network:' :
                search_result_data['network'] = soup.select(td_css_selector)[0].get_text()
            elif th_col_name == 'Abstract:' :
                search_result_data['abstract'] = soup.select(td_css_selector)[0].get_text().lstrip()
            elif th_col_name == 'Broadcast Type:' :
                search_result_data['type'] = soup.select(td_css_selector + ' strong')[0].get_text()
            elif th_col_name == 'Program Time:' :
                program_time = soup.select(td_css_selector)[0].get_text()
                search_result_data['begin'] = program_time.split(' - ')[0].replace('\xa0', ' ')
                search_result_data['end'] = program_time.split(' - ')[1].split('.')[0].replace('\xa0', ' ')
                search_result_data['duration'] = program_time.split('\r\n')[1]
    return search_result_data

def get_search_result_abs(search_result_item_link) :
    response = requests.get(search_result_item_link)
    soup = bs4.BeautifulSoup(response.text, "html.parser")
    return soup.select('table:nth-of-type(2) tr:nth-of-type(1) td')[0].get_text()

if __name__ == '__main__' :

    search_items_date_boundry = get_search_items_date_boundry(file_path_comp)
    for search_item_dates_boundry in search_items_date_boundry :
        search_url_filter_m = ''
        search_url_filter_m += '&Month=' + search_item_dates_boundry['Month'] \
                               + '&Date=' + search_item_dates_boundry['Date'] \
                               + '&Year=' + search_item_dates_boundry['Year'] \
                               + '&EndMonth=' + search_item_dates_boundry['EndMonth']\
                               + '&EndDay=' + search_item_dates_boundry['EndDay'] \
                               + '&EndYear=' + search_item_dates_boundry['EndYear']
        search_url_full = search_url_base + search_url_filter_l + search_url_filter_m + search_url_filter_r
        get_search_results(search_url_full)

    #start_time = time.time()
    #search_keywords_list = get_search_keywords_list()
    #for search_keywords in search_keywords_list:
    #    print('====== ' + search_keywords +' ======')
    #    search_url_comp = search_url_base + search_keywords
    #    get_search_results(search_url_comp)
    #end_time = time.time()
    #print('Running Time: %f seconds' % (end_time - start_time))

    print('Goodbye')


