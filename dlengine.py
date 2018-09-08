import sys
import os
import re
import time
import argparse
import requests
import bs4 as BeautifulSoup
import subprocess

import config


class ZoneTel(object):
    def __init__(self, searched_file=None):
        self.pathurl = 'https://ww1.zone-telechargement1.org/index.php?do=search'
        self.results = []
        self.API_KEY = config.API_KEY
        self.searched_file = searched_file

    def reset(self):
        self.results = []

    def search(self, searched_file):
        result_from = 1
        search_start = 1
        while True:
            data = {
                'do': 'search',
                'subaction': 'search',
                'search_start': search_start,
                'full_search': '0',
                'result_from': result_from,
                'story': searched_file
            }
            resp = requests.post(url=self.pathurl, data=data)
            if not self.parse(resp):
                break

            result_from += 25
            search_start += 1

    def process(self, searched_file=None):
        if not searched_file:
            searched_file = self.searched_file

        self.search(searched_file)
        self.results = sorted(self.results, key=lambda k: int(k['quality'][:-1]) if k['quality'] and k['quality'][:-1].isdigit() else 0, reverse=True)
        if not self.results:
            print('0 result has been found for "%s".' % searched_file)
            return

        try:
            protected_urls = None
            while not protected_urls:
                os.system('clear')
                chosen_url = self.pick_choice()
                os.system('clear')
                if chosen_url is None:
                    return
                protected_urls = self.get_protected_link(chosen_url)
                os.system('clear')

            uptobox_links = [self.get_uptobox_link(protected_url) for protected_url in protected_urls]

        except Exception as e:
            print(e)
            return

        uptobox_engine = UptoboxDlEngine(uptobox_links)
        uptobox_engine.download()
        os.system('clear')

        while True:
            query = input('Do you want to search something else ? (yes / no) : ')
            if query == '' or not query[0].lower() in ['y', 'n']:
                print('Please answer with yes or no!')
            else:
                break
        if query[0].lower() == 'n':
            sys.exit()
        else:
            self.searched_file = input('New search: ')
            self.reset()
            self.process()

    def parse(self, response):
        soup = BeautifulSoup.BeautifulSoup(response.text, features="lxml")
        links = soup.findAll('div', attrs={"class": u"cover_infos_title"})
        if not links:
            return
        else:
            for link in links:
                found_url = link.find('a')
                infos = str(link.find('b').string).split()
                language = re.sub('[( )]', '', str(link.find('span', attrs={'style': 'color:#ffad0a'}).string))
                result = {
                    'name': found_url.string,
                    'zt_url': found_url['href'],
                    'format': str(infos[0]),
                    'language': language,
                    'quality': str(infos[1]) if len(infos) is 2 else ''

                }
                self.results.append(result)
        return True

    def pick_choice(self):

        sorted_res = {}
        for i in self.results:
            if i['language'] not in sorted_res:
                sorted_res[i['language']] = []
            sorted_res[i['language']].append(i)

        print("Results found for '%s' :" % self.searched_file)

        i = 1
        links_tab = []
        for lang in sorted_res:
            print('In %s :' % lang)
            for link in sorted_res[lang]:
                print('\t%d - %s %s -> %s' % (i, link['quality'], link['format'], link['name']))
                i += 1
                links_tab.append(link['zt_url'])
        print('\n%d - New search' % i)
        print('0 - Quit')

        while True:
            try:
                pick = int(input('\nWhat do you want to download ? '))
                if 0 <= pick <= i:
                    break
                else:
                    print('Enter a number between %d and %d.' % (0, i))
            except (ValueError, NameError):
                print('Enter a number between %d and %d.' % (0, i))

        if not pick:
            return None
        if pick is i:
            self.searched_file = input('New search: ')
            self.reset()
            self.process()
            return None

        return links_tab[pick - 1]

    def get_protected_link(self, zt_url):
        r = requests.get(zt_url)

        str_start = '<div class="postinfo"><font color=red>'
        title_start = r.text.find(str_start)
        tmp_text = r.text[title_start:]
        title_end = tmp_text.find('</font>')
        title = r.text[title_start+len(str_start):title_start+title_end]

        print('You are about to download %s.' % title)

        resp = r.text[:r.text.find('Commentaires')]

        def find_end_del(str):
            domains = [
                'Uploaded',
                'Turbobit',
                'Nitroflare',
                'Rapidgator',
                '1fichier',
            ]
            delimiters = []
            for domain in domains:
                delimiter = str.find(domain)
                if delimiter is not -1:
                    delimiters.append(delimiter)
            return min(delimiters)

        text_groups = []
        start = 0
        searched_str = 'Uptobox</div></b>'
        while True:
            delimiter = resp[start:].find(searched_str)
            if delimiter is -1:
                break
            start = delimiter + start + len(searched_str)
            end = find_end_del(resp[start:])
            text_groups.append(resp[start:start + end])

        all_protect_links = []
        for text_group in text_groups:
            soup = BeautifulSoup.BeautifulSoup(text_group, features="lxml")
            b_tags = soup.findAll('b')

            dl_protect_links = []
            for b_tag in b_tags:
                a_tags = b_tag.findAll('a')
                for a_tag in a_tags:
                    if a_tag and 'https://www.dl-protect1.com' in a_tag['href']:
                        dl_protect_links.append({'name': a_tag.text, 'url': a_tag['href']})

            all_protect_links.append(dl_protect_links)

        lens = [len(group) for group in all_protect_links]

        min_lens = min(lens)
        if min_lens is 1:
            for elem in all_protect_links:
                if len(elem) is 1:
                    return [elem[0]['url']]

        print('\nWe found this parts:')
        i = 1
        if len(all_protect_links) is 1:
            for link in all_protect_links[0]:
                print('%d - %s' % (i, link['name']))
                i = i + 1
            print('\n0 - Download everything')
            print('%d - Go back' % i)
            print('%d - Quit' % (i + 1))

            #todo: its a copy/paste from above / change this asap, this is ugly
            while True:
                try:
                    pick = int(input('\nWhat do you want to download ? '))
                    if 0 <= pick <= i + 1:
                        break
                    else:
                        print('Enter a number between %d and %d.' % (0, i + 1))
                except (ValueError, NameError):
                    print('Enter a number between %d and %d.' % (0, i + 1))

            if not pick:
                return [link['url'] for link in all_protect_links[0]]
            elif pick is i:
                return None

            elif pick is i + 1:
                sys.exit()
            else:
                return [all_protect_links[0][pick - 1]['url']]
        else:
            #todo:
            pass


    @staticmethod
    def get_uptobox_link(protected_url):

        r = requests.post(protected_url, data={'submit': 'Continuer'})

        link_soup = BeautifulSoup.BeautifulSoup(r.text, features="lxml")
        t = link_soup.find('div', attrs={'class': 'lienet'})
        if not t:
            raise ('We could not get uptobox link on dl-protect.')
        else:
            uptobox_url = t.string

        return uptobox_url


class UptoboxDlEngine(object):

    def __init__(self, uptobox_links):
        self.API_KEY = config.API_KEY
        self.uptobox_links = uptobox_links


    def download(self):
        for uptobox_url in self.uptobox_links:
            self.download_uptobox_link(uptobox_url)

    def download_uptobox_link(self, uptobox_url):

        if not self.API_KEY:
            print("We have detected that you do not have an Uptobox token. We can not build your download link. "
                  "However, you can go to this uptobox link to generate it by yourself:\n%s" % uptobox_url)

        r = requests.get(uptobox_url)

        link_soup = BeautifulSoup.BeautifulSoup(r.text, features="lxml")
        title = link_soup.find('h1', attrs={'class': 'file-title'})
        title = title.text

        if title == 'File not found ':
            print('File has been removed :(')
            return

        file_id = uptobox_url.split('/')[-1]

        file_link = 'https://uptobox.com/api/link?token=%s&id=%s' % (self.API_KEY, file_id)

        r = requests.get(file_link)
        res = r.json()
        if res['message'] == 'Waiting needed':
            if not res['data']['waitingToken']:
                time_to_wait = res['data']['waiting']
                while True:
                    query = input('It seems that you already downloaded something in the last 30 minutes. You have to wait '
                                 '%d seconds. Do you want we build your download link after this time ? (yes / no) : ' % time_to_wait)
                    if query == '' or not query[0].lower() in ['y', 'n']:
                        print('Please answer with yes or no!')
                    else:
                        break

                if query[0].lower() == 'y':
                    print('Waiting for %s seconds' % time_to_wait)
                    time.sleep(time_to_wait)
                    file_link = 'https://uptobox.com/api/link?token=%s&id=%s' % (self.API_KEY, file_id)
                    r = requests.get(file_link)
                    res = r.json()

                else:
                    return

            print('As a non premium account, you have to wait 30sec.')
            time.sleep(31)
            file_link = 'https://uptobox.com/api/link?token=%s&id=%s&waitingToken=%s' % \
                        (self.API_KEY, file_id, str(res['data']['waitingToken']))
            r = requests.get(file_link)
            res = r.json()

        if res['message'] != 'Success':
            raise ('%s' % res['message'])

        dl_link = res['data']['dlLink']
        subprocess.Popen(['xterm', '-title', 'Downloading %s' % title, '-e', 'curl', dl_link, '--output', title])
        print('\n')


def parser_cl():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', help='File you want to download.')
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    if sys.version_info[0] < 3:
        print('You have to run this scrpt on Python 3.')
        sys.exit()
    elif len(sys.argv) > 2:
        sys.argv[1] = ' '.join(sys.argv[1:])
        sys.argv = sys.argv[:2]

    args = parser_cl()
    if not config.API_KEY:
        print('No Uptobox token has been found on config.py file.\nYou can have it with a registered or a premium Uptobox account.\n'
              'If this value is empty will not be able to download, but only find an Uptobox link.')
        while True:
            query = input('\nDo you still want to continue ? (yes / no) : ')
            if query == '' or not query[0].lower() in ['y', 'n']:
                print('Please answer with yes or no!')
            else:
                break
        if query[0].lower() == 'n':
            sys.exit()
        print('\n')

    engine = ZoneTel(args.file)
    engine.process()
