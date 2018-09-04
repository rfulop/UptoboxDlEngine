import sys
import re
import os
import time
import argparse
import requests
import bs4 as BeautifulSoup
import config


class ZoneTel(object):
    def __init__(self):
        self.pathurl = 'https://ww1.zone-telechargement1.org/index.php?do=search'
        self.results = []
        self.API_KEY = config.API_KEY

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

    def process(self, searched_file):
        self.search(searched_file)
        self.results = sorted(self.results, key=lambda k: int(k['quality'][:-1]) if k['quality'] and k['quality'][:-1].isdigit() else 0, reverse=True)
        if not self.results:
            print('0 result has been found for "%s".' % searched_file)
            return

        try:
            chosen_url = self.pick_choice()
            protected_url = self.get_protected_link(chosen_url)
            self.get_uptobox_link(protected_url)
        except Exception as e:
            print(e)
            return

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

        print('Found results :')

        i = 1
        links_tab = []
        for lang in sorted_res:
            print('%s :' % lang)
            for link in sorted_res[lang]:
                print('\t%d - %s %s -> %s' % (i, link['language'], link['format'], link['name']))
                i += 1
                links_tab.append(link['zt_url'])

        while True:
            try:
                pick = int(input('\nWhat do you want to download ? : '))
                if pick and 1 <= pick <= i - 1:
                    break
                else:
                    print('Enter a number between %d and %d.' % (1, i - 1))
            except (ValueError, NameError):
                print('Enter a number between %d and %d.' % (1, i - 1))

        return links_tab[pick - 1]

    @staticmethod
    def get_protected_link(zt_url):
        r = requests.get(zt_url)
        reg = re.findall('Lien premium(.*)Uptobox(.*)', r.text)
        if not reg:
            reg = re.findall('Uptobox(.*)', r.text)
            if not reg:
                raise ('No uptobox link has been found.')


        reg_res = re.search('href="(.*)"', str(reg))
        reg_res = str(reg_res.group(1))
        delimiter = reg_res.find('"')
        protected_url = reg_res[:delimiter]

        return protected_url

    def get_uptobox_link(self, protected_url):

        r = requests.post(protected_url, data={'submit': 'Continuer'})

        link_soup = BeautifulSoup.BeautifulSoup(r.text, features="lxml")
        t = link_soup.find('div', attrs={'class': 'lienet'})
        if not t:
            raise ('We could not get uptobox link on dl-protect.')
        else:
            uptobox_url = t.string
            print(uptobox_url)
            file_id = uptobox_url.split('/')[-1]

            if not self.API_KEY:
                print("We have detected that you do not have an Uptobox token. We can not build your download link. "
                      "However, you can go to this uptobox link to generate it by yourself:\n%s" % uptobox_url)
                return

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
            os.system('curl %s --output %s ' % (dl_link, sys.argv[1].replace(' ', '_')))


def parser_cl():
    parser = argparse.ArgumentParser()
    parser.add_argument('file', help='File you want to download.')
    args = parser.parse_args()
    return args


if __name__ == '__main__':
    if sys.version_info[0] < 3:
        print('You have to run this scrpt on Python 3.')
        sys.exit()
    elif len(sys.argv) != 2:
        sys.argv[1] = ' '.join(sys.argv[1:])
        sys.argv = sys.argv[:2]

    args = parser_cl()
    engine = ZoneTel()
    engine.process(args.file)
