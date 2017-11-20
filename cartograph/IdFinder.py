import requests
import urllib
from difflib import SequenceMatcher


BASE_REDIRECT_URL = 'https://%s.wikipedia.org/w/api.php?action=query&titles=%%s&redirects&format=json' 
BASE_SEARCH_URL = 'https://%s.wikipedia.org/w/api.php?action=query&list=search&srsearch=%%s&utf8=&format=json'
PAGE_BY_ID_URL = 'https://www.wikidata.org/w/api.php?action=wbgetentities&props=sitelinks&ids=Q%s&format=json'
BASE_CATEGORIES_URL = 'https://%s.wikipedia.org/w/api.php?action=query&pageids=%%s&prop=categories&format=json'
DISAMBIGUATION_CATEGORY_ID = '1982926'


class IdFinder:
    '''An instance of this class is responsible for converting lists of article
    titles to internal IDs, given a map of titles to internal ids, external ids
    to internal ids, and a language code.
    '''
    def __init__(self, names_to_ids, external_ids, language_code=''):
        '''Initialize an IdFinder.

        names_to_ids: A dictionary of names to internal IDs; do not mutate
        external_ids: A dictionary of external IDs to internal IDs
        language_code: Code for the language of the Wikipedia to refer to
        '''
        self.names_to_ids = names_to_ids
        self.external_ids = external_ids
        self.language_code = language_code
        self.redirect_url = BASE_REDIRECT_URL % language_code
        self.search_url = BASE_SEARCH_URL % language_code
        self.categories_url = BASE_CATEGORIES_URL % language_code

        # Figure out what how to say "disambiguation page" in the language
        page_title_data = requests.get(PAGE_BY_ID_URL % (DISAMBIGUATION_CATEGORY_ID,)).json()
        pages_by_language = page_title_data[u'entities'][u'Q'+unicode(DISAMBIGUATION_CATEGORY_ID)][u'sitelinks']
        self.disambiguation_category_title = pages_by_language[unicode(language_code)+u'wiki'][u'title']

    def get_raw_matches(self, titles):
        '''Find and return dictionary of IDs for titles that exist in name
        dataframe; also return set of titles with no entry in name dataframe.
        '''
        # Append internal ids with the user data; set the index to 'id';
        # preserve old index (i.e. 1st column goes to 2nd column)

        ids = dict()
        bad_titles = set()
        for title in titles:
            if title in self.names_to_ids:
                ids[title] = self.names_to_ids[title]
            else:
                bad_titles.add(title)

        return ids, bad_titles

    def get_redirects(self, titles):
        '''Query the relevant Wikipedia for article titles that redirect;
        return the ID numbers of any that redirect to titles in the names
        dataframe. Also return a set of the titles for which no redirect was
        found.
        '''
        # Check that this has been configured for a particular Wikipedia language
        if not self.language_code:
            raise Exception('This IdFinder was not configured with a language code')

        # Look up redirects for raw titles
        ids = dict()
        bad_titles = set()
        for title in titles:
            response = requests.get(self.redirect_url % urllib.quote(title, safe='')).json()
            if not response[u'query'][u'pages'].values()[0].has_key(u'missing'):
                title = response[u'query'][u'pages'].values()[0][u'title']
                ids[title] = self.names_to_ids[title]
            else:
                bad_titles.add(title)

        return ids, bad_titles

    def get_soft_matches(self, titles):
        '''Given an iterable of titles, return a dictionary of titles to internal ids
        '''
        ids = dict()
        bad_titles = set()

        for title in titles:
            # Search for each title
            response = requests.get(self.search_url % urllib.quote(title, safe='')).json()

            # Find the first article whose pageid is in external_ids that is
            # not a disambiguation
            for article in response[u'query'][u'search']:
                page_id = int(article[u'pageid'])
                if page_id in self.external_ids:
                    categories_query = requests.get(self.categories_url % urllib.quote(str(page_id), safe='')).json()
                    try:
                        categories = [category[u'title'] for category in categories_query[u'query'][u'pages'][unicode(page_id)][u'categories']]
                        if self.disambiguation_category_title not in categories:
                            ids[title] = self.external_ids[int(page_id)]
                    except KeyError:
                        print(categories_query)
            else:
                bad_titles.add(title)

        return ids, bad_titles

    def get_hard_matches(self, titles):
        ids, bad_titles = self.get_raw_matches(titles)
        redirect_ids, bad_titles = self.get_redirects(bad_titles)
        ids.update(redirect_ids)
        return ids, bad_titles

    def get_all_matches(self, titles):
        pass
        # ids.update(self.get_soft_matches(titles))


if __name__ == '__main__':
    id_finder = IdFinder({u'Car': 1, u'Movie': 5, u'Wikipedia': 123}, {214943: 1, 3486: 5, 27263: 123}, language_code='simple')

    print(id_finder.get_raw_matches(['Car', 'Wikipedia']))
    print(id_finder.get_raw_matches(['Car', 'Film', 'Wikipedia']))
    print(id_finder.get_hard_matches(['Car', 'Film', 'Wikipedia']))  # Film = Movie
    print(id_finder.get_soft_matches(['Film', 'Car', 'Encyclopedia', 'Movies', 'Coach']))
