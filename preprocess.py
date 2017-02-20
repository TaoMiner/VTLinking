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

    def splitCapitalWords(self, item):
        # split with Capital letter
        return re.sub(r'(?=[A-Z])', ' ', item).strip()

    # extract text, mention users, hashtags
    def extractMeta(self, tweet):
        # extract user mentions and hasgtags
        indices_del = []
        at_users = []
        hashtags = []
        if u'entities' in tweet and u'user_mentions' in tweet[u'entities']:
            for um in tweet[u'entities'][u'user_mentions']:
                if u'id_str' in um and u'name' in um and u'indices' in um:
                    at_users.append([um[u'id_str'], um[u'name']])
                    indices_del.append(um[u'indices'])
        if u'entities' in tweet and u'hashtags' in tweet[u'entities']:
            for htag in tweet[u'entities'][u'hashtags']:
                if u'text' in htag and u'indices' in htag:
                    hashtags.append(htag[u'text'])
                    indices_del.append(htag[u'indices'])
        # delete user mentions and hashtags in text
        tmp_text = tweet[u'text']
        text = ''
        start_pos = 0
        end_pos = 0
        for ind in indices_del:
            if len(ind) != 2 : continue
            end_pos = ind[0]
            text += tmp_text[start_pos:end_pos]
            start_pos = ind[1]
        if start_pos < len(tmp_text):
            end_pos = len(tmp_text)
            text += tmp_text[start_pos:end_pos]
        # delete hyperlinks
        text = re.sub(r'http(.*?)( |$)', ' ', text.strip())
        # split sentences
        sentences = re.split(r'[\.,?!]', text)
        sentences_cl = []
        for sent in sentences:
            sent_cl = []
            items = sent.split()
            for item in items:
                if item == u'RT' or len(item) < 1:
                    continue
                else:
                    sent_cl.append(item)
            if len(sent_cl) > 0:
                sentences_cl.append(sent_cl)
        return sentences_cl, at_users, hashtags

    def parseTweet(self, tweet):
        # [id, text, user, [at_users,...], [#,...], [mentions], [photo_urls]]
        parsed_tweet = {}
        parsed_tweet[u'id'] = tweet[u'id']
        user = ['','']
        if u'user' in tweet and u'id_str' in tweet[u'user']:
            user[0] = tweet[u'user'][u'id_str']
        if u'user' in tweet and u'name' in tweet[u'user']:
            user[1] = tweet[u'user'][u'name']
        parsed_tweet[u'user'] = user
        sents, at_users, hashtags = self.extractMeta(tweet)
        p_text = ''
        # [[pos, length, string, type],...], pos : [0, len(text)-1]
        mentions = []
        mention = ''
        mention_type = ''
        if self.ner_parser:
            # extract mentions from text
            for sent in sents:
                tagged_text = self.ner_parser.tag(sent)
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
                    p_text += mention + ' '
                    mention = ''
                    mention_type = ''
                p_text += '. '
            # extract mentions from hashtags
            tags_cl = []
            mention = ''
            mention_type = ''
            tag_count = 0
            for m in hashtags:
                tag_count += 1
                tagged_m = self.ner_parser.tag(m.split())
                tmp_text = ''
                for tm in tagged_m:
                    if tm[1] == u'PERSON' or tm[1] == u'ORGANIZATION' or tm[1] == u'LOCATION':
                        if len(mention_type) > 0 and tm[1] == mention_type:
                            mention += ' ' + tm[0]
                        else:
                            if len(mention) > 0:
                                mentions.append([tag_count, len(tmp_text), mention, mention_type])
                                tmp_text += mention + ' '
                            mention = tm[0]
                            mention_type = tm[1]
                    else:
                        if len(mention) > 0:
                            mentions.append([tag_count, len(tmp_text), mention, mention_type])
                            tmp_text += mention + ' '
                        tmp_text += tm[0] + ' '
                        mention = ''
                        mention_type = ''
                if len(mention) > 0:
                    mentions.append([tag_count, len(tmp_text), mention, mention_type])
                    tmp_text += mention
                tags_cl.append(tmp_text.strip())
        parsed_tweet[u'text'] = p_text.strip()
        parsed_tweet[u'user_mentions'] = at_users
        parsed_tweet[u'hashtags'] = tags_cl
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
                    if u'lang' not in tweet or u'en' != tweet[u'lang']:
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
    # print tr.ner_parser.tag('Cummings: Trump made up story about a canceled meeting'.split())
