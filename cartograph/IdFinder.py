import requests
import urllib
from difflib import SequenceMatcher


BASE_REDIRECT_URL = 'https://%s.wikipedia.org/w/api.php?action=query&titles=%%s&redirects&format=json' 
BASE_SEARCH_URL = 'https://%s.wikipedia.org/w/api.php?action=query&list=search&srsearch=%%s&utf8=&format=json'


class IdFinder:
    '''An object of this class is responsible for converting lists of article
    titles to internal IDs.
    '''
    def __init__(self, names_to_ids, language_code=''):
        '''name_dataframe: A pandas dataframe of names to internal IDs; please
                           do not mutate
           language_code: Code for the language of the Wikipedia to refer to
        '''
        self.names_to_ids = names_to_ids
        self.language_code = language_code
        self.redirect_url = BASE_REDIRECT_URL % language_code
        self.search_url = BASE_SEARCH_URL % language_code

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
            if not response['query']['pages'].values()[0].has_key('missing'):
                title = response['query']['pages'].values()[0]['title']
                ids[title] = self.names_to_ids[title]
            else:
                bad_titles.add(title)

        return ids, bad_titles

    def get_soft_matches(self, titles):
        ids = dict()
        bad_titles = set()
        for title in titles:
            response = requests.get(self.search_url % urllib.quote(title, safe='')).json()
            if len(response[u'query'][u'search']):
                ids[title] = self.names_to_ids[unicode(response[u'query'][u'search'][0][u'title'])]
            candidate = [0]
            if SequenceMatcher(candidate[u'title'], title).ratio() >= 0.75:
                ids[title] = self.names_to_ids[title]
            else:
                bad_titles.add(title)

            return ids, bad_titles

    def get_hard_matches(self, titles):
        ids, bad_titles = self.get_raw_matches(titles)
        print("IDS so far: %s" % str(ids))
        redirect_ids, bad_titles = self.get_redirects(bad_titles)
        ids.update(redirect_ids)
        return ids, bad_titles

    def get_all_matches(self, titles):
        pass
        # ids.update(self.get_soft_matches(titles))


if __name__ == '__main__':
    id_finder = IdFinder({'Car': 1, 'Movie': 5, 'Wikipedia': 123}, language_code='simple')

    print(id_finder.get_raw_matches(['Car', 'Wikipedia']))
    print(id_finder.get_raw_matches(['Car', 'Film', 'Wikipedia']))
    print(id_finder.get_hard_matches(['Car', 'Film', 'Wikipedia']))  # Film = Movie
    print(id_finder.get_soft_matches(['Film', 'Car', 'Encyclopedia', 'Movies']))
