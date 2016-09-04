#!/usr/bin/env python
"""Queries New York Times article database via developer API.

ATTRIBUTION:
Any URLs that are delivered in the API content must link in each instance to 
the related New York Times URL. You shall not display the API content in such a 
manner that does not allow for successful linking and redirection to, and 
delivery of, NYTIMES.COM's Web page, nor may you frame any NYTIMES.COM Web page.

RESTRICTIONS
Unless otherwise consented to or permitted by NYTIMES.COM, you will:

(i) not modify or edit any content, headlines, links or metadata included in the 
API content when presenting it on your Site;

(ii) ensure that the fundamental meaning of the API content is not changed or 
distorted;

(iii) ensure that the use or display of API content does not suggest that The 
New York Times promotes or endorses you or any third party or the causes, ideas, 
Web sites, products or services of you or any third party;

(iv) not display the name, logo, trademark or other identifier of another person
(except for NYTIMES.COM or you) on your Site in such a manner as to give the 
viewer the impression that such other person is a publisher or distributor of 
the API content on the Site

(v) not archive or cache any of the API content for access by users for more 
than 24 hours after you have finished using the service; or for any period of 
time if your account is terminated.

"""

import argparse
import requests
from bs4 import BeautifulSoup
from time import time, sleep
from datetime import datetime, date


class NYTArticleRequest:
    """Configures API request for NYT article search."""
    def __init__(self, api_key, query, page=0, 
        begin_date=None, end_date=None, fields=None):
        """Initializes NYT API article request.
        
        API keys must be registered through the NYT developer portal:
        https://developer.nytimes.com/
        
        Noncommercial licenses are restricted to 1K requests/day and 5
        requests/sec.
        
        Required:
            api_key - (string) NYT developer API key
            query   - (string) search query term
        Optional:
            begin_date - (date object) filters articles by start date
            end_date   - (date object) filters articles by end date
            fields     - (string) comma-sep list of fields to return
            page       - (int) API returns pages of results (= 10 articles)
            
        """ 
                
        self.nyt_args = {}
        
        # required inputs
        self.nyt_args['api-key'] = api_key        
        self.nyt_args['q'] = query
        self.nyt_args['page'] = str(page)
        
        # optional inputs
        if fields:
            self.nyt_args['fl'] = fields
        
        NYT_DATE_FORMAT = '%Y%m%d' # YYYYMMDD
        if begin_date:
            self.nyt_args['begin_date'] = begin_date.strftime(NYT_DATE_FORMAT)
        if end_date:
            self.nyt_args['end_date'] = end_date.strftime(NYT_DATE_FORMAT)
        
    def __repr__(self):
        """Structures request data as formal request url."""
        
        NYT_API_URL = 'https://api.nytimes.com/svc/search/v2/articlesearch.json'
        
        url_args = []
        for nyt_arg in self.nyt_args.items():
            url_args.append('='.join(nyt_arg))
        
        request_url = NYT_API_URL + '?' + '&'.join(url_args)
        return request_url
        
        
def issueNYTRequests(api_key, query, num_pages=1, 
        begin_date=None, end_date=None, fields=None):
    """Sends repeated calls to NYT, extracting new page each call.
    
    The NYT returns a page of results with each API call (= 10 articles).
    Iterate over specified number of pages while accomodating required request 
    delay for noncommercial users.
    
    """
    
    API_MAX_CALLS_PER_DAY = 100 # Actually 1000                        
    API_MAX_CALLS_PER_SEC = 5   
    
    if num_pages > API_MAX_CALLS_PER_DAY:
        num_pages = API_MAX_CALLS_PER_DAY
    
    all_stories = []
    req_start = time()
    for i in xrange(0,num_pages):        
        cur_request = NYTArticleRequest(api_key, query, i, 
            begin_date, end_date, fields)
                
        # stay below max calls per second
        if i % API_MAX_CALLS_PER_SEC == 0 and i > 0:
            t_elapse = time() - req_start
            while t_elapse < 1:
                sleep(0.1)
                t_elapse = time() - req_start
        
        try:
            r = requests.get(str(cur_request))
        except requests.exceptions.RequestException as e:
            print '%s: %s request failed.' % (e, str(cur_request))
            continue
            
        content = r.json()
        page_stories = parseNYTResponse(content)
        all_stories = all_stories + page_stories
        
    return all_stories
        
def parseNYTResponse(content):
    """Repackages content retrieved from NYT.
    
    Assumes the initial request contained 'headline', 'pub_date', and 'web_url'.
    
    Output:
        dict containing following fields:
            'headline': (string) title of article
            'url': (string) url of article
            'date': (date object) date of article publication
            'content': (string) body of article
    
    """
        
    stories = []
    if content['status'] == 'OK':
        for article in content['response']['docs']:
            headline = article['headline']['main']
            web_url = article['web_url']
            pub_datetime_str = article['pub_date']
            pub_date_str = pub_datetime_str.split('T')[0]
            
            NYT_PUB_FORMAT = '%Y-%m-%d' # YYYY-MM-DD response
            pub_date = datetime.strptime(pub_date_str, NYT_PUB_FORMAT).date()
            
            try:
                r = requests.get(web_url)
            except requests.exceptions.RequestException as e:
                print '%s: %s request failed.' % (e, web_url)
                continue
                
            soup = BeautifulSoup(r.text, 'html.parser')
            story_pieces = soup.find_all('p', 
                {'class': 'story-body-text story-content'})
                
            story_body = ""
            for piece in story_pieces:
                story_body = story_body + piece.text
                
            story = {}
            story['headline'] = headline
            story['url'] = web_url
            story['date'] = pub_date
            story['content'] = story_body
            stories.append(story)
            
    return stories   
    
def main(args):
    fields = 'headline,pub_date,web_url'
    all_stories = issueNYTRequests(args.key, args.query, args.numpages, 
        args.begin, args.end, fields)
    
    for story in all_stories:
        print story['headline'], story['url'], story['date']
        # print story['content']
    
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Submit article requests.')
    parser.add_argument('-k', '--key', required=True,
        help='provide api key.')
    parser.add_argument('-q', '--query', required=True,
        help='specify article query.')
    parser.add_argument('-np', '--numpages', type=int, default=1,
        help='number of pages, 1 page = 10 articles')
    parser.add_argument('-b', '--begin', 
        help='YYYYMMDD, lower bound for publication dates.')
    parser.add_argument('-e', '--end',
        help='YYYYMMDD, upper bound for publication dates.')
    args = parser.parse_args()
       
    main(args)