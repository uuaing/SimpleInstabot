import requests
import json
import time
import random
import traceback

class IGAPI:
    url = 'https://www.instagram.com/'
    url_likes = 'web/likes/%s/like/'
    url_comment = 'web/comments/%s/add/'
    url_follow = 'web/friendships/%s/follow/'
    url_unfollow = 'web/friendships/%s/unfollow/'
    url_login = 'accounts/login/ajax/'
    url_logout = 'accounts/logout/'
    url_media_detail = 'p/%s/?__a=1'
    url_user_detail = '%s/?__a=1'
    url_tag = 'explore/tags/%s/?__a=1'

    isLoggedIn = False
    username = ''
    password = ''

    LastResponse = None
    LastJson = None

         
    def __init__(self, username, password, proxy):
        self.username = username
        self.password = password
        self.s = requests.session()
        user_agent = ("Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/48.0.2564.103 Safari/537.36")       
        self.s.cookies.update({
                        'sessionid': '',
                        'mid': '',
                        'ig_pr': '',
                        'ig_vw': '',
                        'csrftoken': '',
                        's_network': '',
                        'ds_user_id': ''})
        self.s.headers.update ({
                        'Accept-Encoding': 'gzip, deflate',
                        'Accept-Language': 'en-US,en;q=0.8,en;q=0.6',
                        'Connection': 'keep-alive',
                        'Content-Length': '0',
                        'Host': 'www.instagram.com',
                        'Origin': 'https://www.instagram.com',
                        'Referer': 'https://www.instagram.com/',
                        'User-Agent': user_agent,
                        'X-Instagram-AJAX': '1',
                        'X-Requested-With': 'XMLHttpRequest'
                        })
        if proxy != "":
            proxies = {
                    'http': 'http://' + proxy,
                    'https': 'http://' + proxy,
            }
            self.s.proxies.update(proxies)

    def login(self):
        params = {
                'username':self.username,
                'password':self.password}
        r = self.s.get(self.url)
        if r.status_code != 200:
            print ("Login failed " + str(r.status_code))
        else:
            self.s.headers.update({'X-CSRFToken': r.cookies['csrftoken']})
            time.sleep(5 * random.random())
            if(self.send(self.url_login, params, True)):
                self.s.headers.update({'X-CSRFToken': self.LastResponse.cookies['csrftoken']})
                self.isLoggedIn = True

    def get_id_by_name(self, user_name):
        if self.send(self.url_user_detail % user_name):
            return self.LastJson['user']['id']
        return 0

    def like(self, media_id):
        return self.send(self.url_likes % media_id, ' ')

    def follow(self, user_id):
        return self.send(self.url_follow % user_id, ' ')

    def unfollow(self, user_id):
        return self.send(self.url_unfollow % user_id, ' ')

    def get_medias(self, tag):
        medias = []
        if self.send(self.url_tag % (tag)):
            edges = list(self.LastJson['tag']['media']['nodes'])
            for media in edges:
                medias.append({
                    'user_id':media['owner']['id'],
                    'user_name':'',
                    'media_code':media['code'],
                    'likes_count':media['likes']['count'],
                    'media_id':media['id']
                    })
        return medias

    def comment(self, media_id, comment):
        return self.send(self.url_comment % media_id, { 'comment_text': comment })

    def check_media_comment(self, media_id, user_id):
        try:
            if self.send(self.url_media_detail % media_id):
                if self.LastJson['graphql']['shortcode_media']['owner']['id'] == user_id:
                    return False
                for d in list(self.LastJson['graphql']['shortcode_media']['edge_media_to_comment']['edges']):
                    if d['node']['owner']['id'] == user_id:
                        return False
        except:
            return False
        return True

    def get_user_detail(self, user_name):
        if self.send(self.url_user_detail % user_name):
            user = self.LastJson['user']
            follows = user['follows']['count']
            follower = user['followed_by']['count']
            follow_viewer = user['follows_viewer']
            followed_by_viewer = user['followed_by_viewer']
            return follows, follower, follow_viewer, followed_by_viewer

    def get_username(self, media_code):
        self.send(self.url_media_detail % media_code)
        try:
            return self.LastJson['graphql']['shortcode_media']['owner']['username']
        except:
            return 'NA'

    def send(self, endpoint, post = None, isLogin = False):
        if (not self.isLoggedIn and not isLogin):
            raise Exception("Not logged in!\n")
            return;

        if (post != None):
            response = self.s.post(self.url + endpoint, data=post) 
        else:
            response = self.s.get(self.url + endpoint) 

        if response.status_code == 200:
            self.LastResponse = response
            self.LastJson = json.loads(response.text)
            return True
        else:
            print ("Request return " + str(response.status_code) + " error! %s" % endpoint)
            try:
                self.LastResponse = response
                self.LastJson = json.loads(response.text)
            except:
                traceback.format_exc()
                pass
            return False