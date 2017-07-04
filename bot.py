from IGAPI import IGAPI
from time import time, sleep
from db import instabot_db
import random
import datetime
import traceback
import os.path

class bot():
    login_user_id = 0
    keep_days_for_not_followed_me = 2
    keep_days_for_followed_me = 5

    likes_max_count = 50
    follower_max_count = 350
    tags = []

    like_per_day = 0
    follow_per_day = 0
    comments_per_day = 0
    unfollow_per_day = 0    

    action_interval = {"like": 0, "follow": 0, "unfollow": 0, "comment": 0}
    action_iteration = {"like": 0, "follow": 0, "unfollow": 0, "comment": 0}
    action_count = {"like": 0, "follow": 0, "unfollow": 0, "comment": 0}

    unfollow_whitelist = []
    current_medias = []

    comments = []
    unfollow_retry_times = 0
    current_tag_index = -1

    def __init__(self
                 ,username
                 ,password
                 ,follow_per_day = 1000
                 ,tags = ['f4f', 'follow4follow']
                 ,comments = ["WOW!", "Amazing!", "Cool!", "Wonderful!", "Great!", "Beautiful shot!", "Excellent!", "So beautiful!"]
                 ,likes_max_count = 50
                 ,follower_max_count = 350
                 ,like_per_day = None
                 ,unfollow_per_day = None
                 ,comments_per_day = None
                 ,proxy = ''
                 ,keep_days_for_not_followed_me = 1
                 ,keep_days_for_followed_me = 5
                 ):
        self.login_user_name = username
        self.tags = tags
        self.likes_max_count = likes_max_count
        self.follower_max_count = follower_max_count
        self.follow_per_day = follow_per_day
        self.like_per_day = like_per_day == None and self.follow_per_day * 0.7 or like_per_day
        self.unfollow_per_day = unfollow_per_day == None and self.follow_per_day or unfollow_per_day
        self.comments_per_day = comments_per_day == None and self.follow_per_day * 0.5 or comments_per_day
        self.keep_days_for_followed_me = keep_days_for_followed_me
        self.keep_days_for_not_followed_me = keep_days_for_not_followed_me
        self.comments = comments

        self.IG = IGAPI(username,password,proxy)
        self.action_interval_calc()
        self.db = instabot_db()

        #get white list from unfollow_whitelist.txt
        if os.path.exists('unfollow_whitelist.txt'):
             with open('unfollow_whitelist.txt') as f:
                 unfollow_whitelist = [line.rstrip('\n') for line in f]

    def login(self):        
        while True:
            try:
                self.logger('Login with %s...' % self.login_user_name)
                self.IG.login()
                self.login_user_id = self.IG.get_id_by_name(self.login_user_name)
                if self.login_user_id == 0:
                    self.logger('Login failed, retry in 3 mins later...')
                    sleep(180)
                else:
                    self.logger('Login success!')
                    break
            except:
                sleep(180)

    def run(self):        
        self.login()

        while True:
            try:   
                if self.retrieve_medias():                    
                    try:
                        self.find_next_available_media()
                        if len(self.current_medias) == 0:
                            continue

                        while True:
                            sleep(2)
                            m = self.current_medias[0]
                            liked = self.like(m['media_id'])
                            followed = self.follow(m['user_id'], m['user_name'])
                            commented = self.comment(m['media_id'], m['media_code'], self.login_user_id)
                            self.unfollow()
                            #any one of like, follow, comment performed, got to next media
                            if liked or followed or commented:
                                del self.current_medias[0]
                                break                            
                    except:
                        traceback.print_exc()
                        del self.current_medias[0]
                self.sleep(2)
            except:
                traceback.print_exc()
                self.login()

    def retrieve_medias(self):
        if len(self.current_medias) == 0:
            tag = self.next_tag()
            self.current_medias = self.remove_duplicate_media(self.IG.get_medias(tag))
            self.logger('Received %i medias by Tag: #%s' % (len(self.current_medias), self.tags[self.current_tag_index]))
        return len(self.current_medias) > 0

    def unfollow(self):
        if self.is_next_ready('unfollow'):
            user_id, user_name, isfollow_by_me, isfollowed_me, insert_time = self.db.get_next_unfollower(self.keep_days_for_not_followed_me, self.keep_days_for_followed_me)
            #check if this use followed me
            if user_id !=0: 
                if isfollowed_me == '0':
                    #todo: get user detail return exception
                    foer_count, fos_count, is_fo_you, is_fo = self.IG.get_user_detail(user_name)
                    #set user as disable if there is error when finding a user
                    if foer_count is None:
                        self.db.set_disable(user_id)    
                    elif is_fo_you:
                        #if the use followed you, update database and find next unfollow
                        self.db.set_follows(user_id)
                        self.logger('%s, %s is followed you, now set as followed' % (str(user_id), user_name))
                        return                
                 
                if not any(u == user_name for u in self.unfollow_whitelist):  
                    if self.IG.unfollow(user_id):
                        self.db.unfollow(user_id)
                        self.prepare_next('unfollow')
                    else:
                        self.unfollow_retry_times += 1
                        sleep(3)
                        if self.unfollow_retry_times == 3:
                            self.unfollow_retry_times = 0
                            self.db.unfollow(user_id)                            
                            self.logger('Retry failed, unfollow focelly. user: %s, username: %s' % (str(user_id), user_name))
                                        
    
    def comment(self, media_id, media_code, user_id):
        if self.is_next_ready('comment') and self.IG.check_media_comment(media_code, user_id):
            if self.IG.comment(media_id, random.choice(self.comments)):
                self.prepare_next('comment')
                return True
            else:
                raise Exception('comment error for %s' % media_code)
        return False               

    def follow(self, user_id, user_name):
        #check db
        if self.is_next_ready('follow'):
            if not self.db.is_followed(user_id):
                if self.IG.follow(user_id):                    
                    self.db.follow(user_id, user_name)
                    self.prepare_next('follow')
                    return True
                else:
                    raise Exception('follow error for %s' % user_name)
        return False

    def like(self, media_id):
        if self.is_next_ready('like'):
            if self.IG.like(media_id):
                self.prepare_next('like')
                return True
            else:
                raise Exception('like error for %s' % media_id)
        return False

    def next_tag(self):
        if self.current_tag_index == len(self.tags):
            self.current_tag_index = 0
        else:
            self.current_tag_index += 1
        return self.tags[self.current_tag_index]

    #remove duplicate medias which posted by same user
    def remove_duplicate_media(self, medias):        
        new = []
        seen = set()
        for m in medias:
            if m['user_id'] not in seen:
                seen.add(m['user_id'])
                new.append(m)
        return new

    def is_next_ready(self, type):
        return self.action_interval[type] !=0 and time() > self.action_iteration[type]

    def find_next_available_media(self):        
        while True:
            if len(self.current_medias) == 0:
                break
            m = self.current_medias[0]
            if m['likes_count'] > self.likes_max_count:
                self.logger('  REMOVE >> more likes: %i' % (m['likes_count']))
                del self.current_medias[0]
                continue
            else:
                user_name = self.IG.get_username(m['media_code'])
                if user_name == 'NA':
                    del self.current_medias[0]
                    continue
                m['user_name'] = user_name
                foer_count, fos_count, is_fo_you, is_fo = self.IG.get_user_detail(user_name)
                is_ignore = False
                
                if foer_count > self.follower_max_count:
                    is_ignore = True

                if foer_count * 0.9 > fos_count:
                    is_ignore = True

                if foer_count * 1.5 < fos_count:
                    is_ignore = False

                if is_fo_you:
                    is_ignore = True


                if is_ignore:
                    self.logger('  REMOVE >> %s:%i, %i, %s, %s, %s' % (m['user_name'], foer_count, fos_count, m['likes_count'], str(is_fo_you), str(is_fo)))
                    del self.current_medias[0]
                    continue
                else:
                    self.logger('  KEEP   >> %s:%i, %i, %s, %s, %s' % (m['user_name'], foer_count, fos_count, m['likes_count'], str(is_fo_you), str(is_fo)))
                    break   
            sleep(1)         

    def action_interval_calc(self):
        seconds_in_day = 24 * 60 * 60
        self.action_interval['like'] = self.like_per_day != 0 and seconds_in_day/self.like_per_day or 0
        self.action_interval['follow'] = self.follow_per_day != 0 and seconds_in_day/self.follow_per_day or 0
        self.action_interval['comment'] = self.comments_per_day != 0 and seconds_in_day/self.comments_per_day or 0
        self.action_interval['unfollow'] = self.unfollow_per_day != 0 and seconds_in_day/self.unfollow_per_day or 0

    def prepare_next(self, type):
        self.action_count[type] +=1
        self.action_iteration[type] = time() + self.action_interval[type]
        time_str = datetime.datetime.fromtimestamp(self.action_iteration[type]).strftime('%H:%M:%S')
        self.logger('%s, #%i, %s next: %s' % (type.capitalize(), self.action_count[type], self.current_medias[0]['user_name'], time_str)) 
        self.sleep(2)

    def logger(self, log):
        print('%s %s' % (datetime.datetime.now().strftime("%y/%m/%d %H:%M  "), log))

    def sleep(self, sec):
        return sleep(sec * 0.8 + sec * random.random())