import json
import codecs
import nltk
import string
import regex as re
punc = re.compile('[%s]' % re.escape(string.punctuation))

class TweetReader():

    def __init__(self):
        self.ner_parser = None
        self.tweets = []

    def setNERParser(self, parser):
        self.ner_parser = parser
        print 'load parser finished!'

    def cleanItem(self, item):
        item = punc.sub(' ', item)
        item = re.sub(r'[\s]+', ' ', item)
        item = re.sub(r'(?<=\s)(\d+)(?=($|\s))', 'dddddd', item)
        item = re.sub(r'(?<=^)(\d+)(?=($|\s))', 'dddddd', item).strip()
        return item

    def splitMeta(self, item):
        # split with Capital letter
        return re.sub(r'(?=[A-Z])', ' ', item).strip()

    def cleanText(self, text):
        cl_text = ''
        users = []
        topics = []
        items = re.split(r' ', text.strip())
        for item in items:
            if item == u'RT' or item.startswith(u'http'):
                continue
            elif item.startswith(u'@'):
                item = self.cleanItem(item)
                users.append(item)
            elif item.startswith(u'#'):
                item = self.cleanItem(item)
                topics.append(item)
            else:
                item = self.cleanItem(item)
                cl_text += item + ' '
        return cl_text.strip(), users, topics

    def parseTweet(self, tweet):
        # [id, text, [@, #], [mentions], [urls]]
        parsed_tweet = {}
        parsed_tweet[u'id'] = tweet[u'id']
        text, users, topics = self.cleanText(tweet[u'text'])
        p_text = ''
        # [[pos, length, string, type],...], pos : [0, len(text)-1]
        mentions = []
        mention = ''
        mention_type = ''
        topics_cl = []
        if self.ner_parser:
            tagged_text = self.ner_parser.tag(text.split())
            for items in tagged_text:
                if items[1] == u'PERSON' or items[1] == u'ORGANIZATION' or items[1] == u'LOCATION':
                    if len(mention_type) > 0 and items[1] == mention_type:
                        mention += ' '+items[0]
                    else:
                        if len(mention) > 0:
                            mentions.append([0, len(p_text), mention, mention_type])
                            p_text += mention + ' '
                        mention = items[0]
                        mention_type = items[1]
                else:
                    if len(mention) > 0:
                        mentions.append([0, len(p_text), mention, mention_type])
                        p_text += mention + ' '
                    p_text += items[0] + ' '
                    mention = ''
                    mention_type = ''
            if len(mention) > 0:
                mentions.append([0, len(p_text), mention, mention_type])
                p_text += mention
            mention = ''
            mention_type = ''
            topic_count = 0
            for m in topics:
                topic_count += 1
                tagged_m = self.ner_parser.tag(m.split())
                tmp_text = ''
                for tm in tagged_m:
                    if tm[1] == u'PERSON' or tm[1] == u'ORGANIZATION' or tm[1] == u'LOCATION':
                        if len(mention_type) > 0 and tm[1] == mention_type:
                            mention += ' ' + tm[0]
                        else:
                            if len(mention) > 0:
                                mentions.append([topic_count, len(tmp_text), mention, mention_type])
                                tmp_text += mention + ' '
                            mention = tm[0]
                            mention_type = tm[1]
                    else:
                        if len(mention) > 0:
                            mentions.append([topic_count, len(tmp_text), mention, mention_type])
                            tmp_text += mention + ' '
                        tmp_text += tm[0] + ' '
                        mention = ''
                        mention_type = ''
                if len(mention) > 0:
                    mentions.append([topic_count, len(tmp_text), mention, mention_type])
                    tmp_text += mention
                topics_cl.append(tmp_text.strip())
        parsed_tweet[u'text'] = p_text.strip()
        parsed_tweet[u'users'] = users
        parsed_tweet[u'hashtags'] = topics_cl
        parsed_tweet[u'mentions'] = mentions
        return parsed_tweet


    def extractTweet(self, input_file, output_file):
        with codecs.open(input_file, 'r', encoding='UTF-8') as fin:
            with codecs.open(output_file, 'w', encoding='UTF-8') as fout:
                line_count = 0
                actual_tweet_num = 0
                for line in fin:
                    line_count += 1
                    if line_count % 10 == 0:
                        print 'has processd %d lines!' % line_count
                    tweet = json.loads(line)
                    # filter non english
                    if u'metadata' not in tweet or u'iso_language_code' not in tweet[u'metadata'] or u'en' != tweet[u'metadata'][u'iso_language_code']:
                        continue
                    # filter no media
                    if u'entities' not in tweet or u'media' not in tweet[u'entities']:
                        continue
                    # filter no photo
                    # u'type' not in tweet[u'entities'][u'media'] or u'photo' != tweet[u'entities'][u'media'][u'type']
                    tw_media = tweet[u'entities'][u'media']
                    photo_urls = set()
                    for m in tw_media:
                        if u'type' in m and u'photo' == m[u'type'] and u'media_url' in m:
                            photo_urls.add(m[u'media_url'])
                    if u'extended_entities' in tweet and u'media' in tweet[u'extended_entities']:
                        tw_media = tweet[u'extended_entities'][u'media']
                        for m in tw_media:
                            if u'type' in m and u'photo' == m[u'type'] and u'media_url' in m:
                                photo_urls.add(m[u'media_url'])
                    if len(photo_urls) <= 0:
                        continue
                    photo_urls = list(photo_urls)
                    # parse person, org and loc
                    parsed_tweet = self.parseTweet(tweet)
                    # data[u'entities'][u'media'][u'media_url']
                    if len(parsed_tweet[u'mentions']) > 0 :
                        parsed_tweet[u'photos'] = photo_urls
                        json_tweet = json.dumps(parsed_tweet)
                        fout.write('%s\n' % json_tweet)
                        actual_tweet_num += 1
        print 'successful extract %d tweets from %d raw data!' % (actual_tweet_num, line_count)

if __name__ == '__main__':
    raw_tweet_file = '/data/m1/cyx/VTLinking/data/tweets.json'
    tweet_file = '/data/m1/cyx/VTLinking/data/tweets_cl.json'
    parser_model = '/data/m1/cyx/VTLinking/data/english.all.3class.distsim.crf.ser.gz'
    '''
    raw_tweet_file = '/Users/ethan/Documents/data/VTLinking/tweets.json'
    tweet_file = '/Users/ethan/Documents/data/VTLinking/tweets_cl.json'
    parser_model = '/Users/ethan/Documents/data/VTLinking/english.all.3class.distsim.crf.ser.gz'
    '''
    tr = TweetReader()
    tr.setNERParser(nltk.tag.StanfordNERTagger(parser_model))
    tr.extractTweet(raw_tweet_file, tweet_file)
