# -*- coding: utf-8 -*-
# above line required to make non ascii characters work
# ffmpeg -i test.mp4 -vf select='gt(scene\,0.4)' -vsync vfr thumb%04d.png
# use above to get thumbnail output
import os, re
from cos_sim import termFrequency, inverseDocumentFrequency, tfIdf, sim
from nltk.tokenize import sent_tokenize, word_tokenize    # nltk sentence and word tokenizers
from nltk.stem import WordNetLemmatizer
wordnet_lemmatizer = WordNetLemmatizer()                  # initialization of the lemmatizer
from nltk.corpus import stopwords                         # get list of stop words
from nltk import pos_tag, ne_chunk

# tokenizer functionality common to all functions
def tokenizer(to_tokenize):  # assumes that object to tokenize is a list
    temp = []
    for token in to_tokenize:
        temp_i = word_tokenize(token.lower()) # needs to be lowered for sim. 2
        temp_i = [j for j in temp_i if j not in ['...', "''",  '.', '!', '?', ',', '``', '--', '[', ']', '<', '>', '♪', '/i', '/', ';', '(', ')', '-', ':', '¡', '¿']]
        temp_i = [wordnet_lemmatizer.lemmatize(j) for j in temp_i]
        temp_i = [j for j in temp_i if j not in stopwords.words('english')]
        temp.append(temp_i)
    return temp    # return a pointer to the list

# preprocessing of the plot sentences
def fetch_plot_data(plot_txt_path):
    plot_sentences = tokenizer(sent_tokenize(open(plot_txt_path, "r").read()))
    # have to work on error of only single character in sentence
    # get rid of empty sentences
    plot_sentences = [sent for sent in plot_sentences if (sent != [] and len(sent) != 1) ]
    return plot_sentences

# preprocessing to get the scenes detected in the video
# split time stamps by reading from file and append to scene_stamps
# scene stamps contain the scene boundaries
def get_scene_stamps(video_file_path):
    # stores its output in the output.txt for further processing
    # can os.system be replaced with something faster?
    with open('output.txt', 'w') as fp:
         fp.write('')  # create a blank file for temporary use
    # figure out a way to replace with subprocess module!
    func_str = 'ffprobe -show_frames -of compact=p=0 -f lavfi "movie='+video_file_path+',select=gt(scene\,0.4)" > output.txt'
    os.system(func_str)    # call to the os to process above command
    time_stamps, scene_stamps = [0], []
    for line in open('output.txt').readlines():
        fields = line.split('|')
        # see the output file to understand the split happens this way
        time_stamps.append(float(fields[4].split('=')[1]))
        scene_stamps.append((time_stamps[-2], time_stamps[-1]))
    # so that you needn't be bothered remembering the order of the returned values
    return {'time_stamps': time_stamps, 'scene_stamps': scene_stamps}

def fetch_subtitle_data(sub_file_path):
    # to get subtitle stamps
    sub_stamps, sub_text, buf = [], [], []
    subs = open(sub_file_path).readlines()
    for index, line in enumerate(subs):
        l = line.strip()
        if l:
            buf.append(l)
        if (not l or index == len(subs)-1):
            # first process the time stamps
            temp = re.split(' --> ', buf[1])
            temp_1, temp_2 = temp[0].split(':'), temp[1].split(':')
            # convert the time stamp into seconds only...
            temp_1 = float(temp_1[1])*60 + float(''.join(temp_1[2].split(',')))/1000.0
            temp_2 = float(temp_2[1])*60 + float(''.join(temp_2[2].split(',')))/1000.0
            sub_stamps.append((temp_1, temp_2))
            sub_text.append(' '.join(buf[2:]))
            buf = []
    raw_sub_text = sub_text
    sub_text = tokenizer(sub_text)  # perform tokenization after appending all subtitles in sub_text
    return {'sub_stamps': sub_stamps, 'sub_text': sub_text, 'raw_sub_text': raw_sub_text}

def plot_sub_assigner(plot_sentences, sub_text):  # used by sim. function 1
    # plot assignment to shots
    plot_to_sub = [[] for i in range(len(plot_sentences))]
    tf = {}
    # find term frequency for all plot sentences
    for index, plot_sentence in enumerate(plot_sentences):
        tf[index] = termFrequency(plot_sentence)
    idf = inverseDocumentFrequency(plot_sentences)
    tf_idf = tfIdf(tf, idf)
    for index, sub_sentence in enumerate(sub_text):
    # which plot sentence most similar with subtitle?
        similarity = sim(sub_sentence, idf, tf_idf, len(plot_sentences))
        if similarity == (-1, -1) or similarity == (0, 'None'):    # query has a problem
            continue
        else:
            plot_to_sub[similarity[1]].append((index, similarity[0]))
    # sort plot_to_sub before return
    for i in range(len(plot_to_sub)):
        plot_to_sub[i] = sorted(plot_to_sub[i], key = lambda x: x[1], reverse=True)
    return {'plot_to_sub': plot_to_sub, 'idf': idf, 'tf_idf': tf_idf}

def sub_shot_assigner(sub_stamps, scene_stamps):
    # first part assigns shot numbers to each part of a subtitle
    # optimizations can be done here
    temp_sub_shot = [[0, 0] for i in range(len(sub_stamps))]
    for sub_index, sub in enumerate(sub_stamps):
        for scene_index, scene in enumerate(scene_stamps):
            if (sub[0] < scene[1]):
                temp_sub_shot[sub_index][0] = scene_index
                break
    for sub_index, sub in enumerate(sub_stamps):
        for scene_index, scene in enumerate(scene_stamps):
            if (sub[1] < scene[1]):
                temp_sub_shot[sub_index][1] = scene_index
                break
    # second part assigns the subtitles properly to shots based on above information
    sub_to_shot = [None]*len(temp_sub_shot)
    for index, tup in enumerate(temp_sub_shot):
        if (tup[0] == tup[1]):    # subtitle start and end in the same shot
            sub_to_shot[index] = tup[0]
        else:    # tup[1] - tup[0] >= 1
            diff = tup[1] - tup[0]    # (scene gap between the subtitle start and end) + 1
            for i in range(1, diff):    # if difference is 1 it won't work
                sub_to_shot[index+i] = tup[0] + i
            if ((scene_stamps[tup[0]][1]-sub_stamps[index][0])/float(scene_stamps[tup[0]][1]-scene_stamps[tup[0]][0])) > ((sub_stamps[index][1]-scene_stamps[tup[1]][0])/float(scene_stamps[tup[1]][1]-scene_stamps[tup[1]][0])):
                sub_to_shot[index] = tup[0]
            else:
                sub_to_shot[index] = tup[1]
    return sub_to_shot

def plot_shot_assigner(plot_to_sub, sub_to_shot):
    # plot_to_sub[i] gives the matching list of subtitle sentences -> [(35, 0.2656571164563915), (604, 0.2658152134299805), (619, 0.26629063540377135), (624, 0.44261725639867383), (687, 0.3904935983047358)]
    temp, plot_to_shot = [[] for i in range(len(plot_to_sub))], [[] for i in range(len(plot_to_sub))]  # as many as the number of plot sentences
    for i in range(len(plot_to_sub)):
        temp[i] = [sub_to_shot[j[0]] for j in plot_to_sub[i]]
    # use this method instead of list(set())
    for i in range(len(plot_to_sub)):
        for item in temp[i]:
            if item not in plot_to_shot[i]:
                plot_to_shot[i].append(item)
    # now plot_to_shot has the sorted list of shots
    return plot_to_shot

# def plot_to_char(plot_sentences):
#     speakers_in_plt_sent = {}
#     for i in range(len(plot_sentences)):
#         speakers_in_plt_sent[i] = []
#     for index, sentence in enumerate(plot_sentences):  # hacked away
#         pos_tags = pos_tag(sentence)
#         temp = ne_chunk(pos_tags).pos()
#         for words in temp:
#             if words[1] == "PERSON":
#                 speakers_in_plt_sent[index].append(words[0][0])
#     return speakers_in_plt_sent
#
# def sub_to_char(transc_path, sub_text):
#     transc, speakers, dialogs = [], [], []
#     t = open(transc_path, "r").readlines()
#     #remove lines without ':' so that actions, narrations are removed
#     for line in t:
#         if ':' in line:                       # transc contains lines without actions/narrations
#             transc.append(line.strip().split(":"))  # strip to get rid of the newline characters
#             if len(transc[-1]) > 10:
#                 transc.remove(transc[-1])           # get rid of the last element if char. name > 10
#     for item in transc:                             # make seperate lists of items and transcripts
#         speakers.append(item[0])
#         dialogs.append(item[1])
#     dialogs, sub_to_speaker = tokenizer(dialogs), {}
#
#     sub_to_speaker = [0]*len(sub_text)
#     for sub_index, sub in enumerate(sub_text):
#         for dialog_index, dialog in enumerate(dialogs):
#             cnt = 0
#             for word in sub:
#                 if word in dialog:  # like trigram comparison
#                     cnt += 1
#                     if sub_to_speaker[sub_index] == 0:
#                         if cnt >= 3 or cnt == len(sub):   # len(sub) because a subtitle may be 2/1 words
#                             sub_to_speaker[sub_index] = speakers[dialog_index]
#                         else:
#                             sub_to_speaker[sub_index] = 0
#                 else:
#                     cnt = 0
#     return sub_to_speaker
#
# def shot_to_speakers(sub_to_shot, sub_to_speaker, len_time_stamps):
#     shot_to_speaker = {}
#     for i in range(len_time_stamps):
#         shot_to_speaker[i] = []
#     for index, character in enumerate(sub_to_speaker):
#         shot_to_speaker[sub_to_shot[index]].append(character)
#     for i in range(len(shot_to_speaker)):
#         shot_to_speaker[i] = list(set([item for item in shot_to_speaker[i] if item != 0]))
#     return shot_to_speaker

# def plot_to_shot_2(speakers_in_plt_sent, shot_to_speaker):                 # used by similarity 2
#     # count = 1
#     plt_shot = {}
#     for i in range(len(speakers_in_plt_sent)):
#         plt_shot[i] = []
#     # for i in shot_to_speaker:
#     #     for j in speakers_in_plt_sent: #sorted(speakers_in_plt_sent.keys(), reverse=True):
#     #         if len(set(shot_to_speaker[i])&set(speakers_in_plt_sent[j])) >= count:
#     #             count += 1
#     #             plt_shot[j].append(i)
#     #     count = 1
#     shots_per_plot = int(round(len(shot_to_speaker)/float(len(speakers_in_plt_sent))))
#     for i in range(len(shot_to_speaker)/shots_per_plot):
#         score, final_scores = [0]*shots_per_plot, []
#         for j in range(shots_per_plot*i, i*shots_per_plot+shots_per_plot):
#             score[j%shots_per_plot] = len(set(shot_to_speaker[j])&set(speakers_in_plt_sent[i]))
#             if (len(set(shot_to_speaker[j])) == score[j%shots_per_plot]):
#                 score[j%shots_per_plot] += 1
#             final_scores.append((j, score[j%shots_per_plot]))
#         final_scores = sorted(final_scores, key = lambda x: x[1], reverse=True)
#         #print final_scores
#         plt_shot[i].extend([final_scores[0][0], final_scores[1][0], final_scores[2][0]])
#     return plt_shot

def get_transcript_data(path):
    with open(path) as fp1:
        transcript = fp1.readlines()
    transc_text = []
    for line in transcript:
        if ':' in line:            # lines without actions/narrations
            transc_text.append([line.strip().split(':')[1], 'd'])  # strip to get rid of the newline characters
        else:
            temp = sent_tokenize(line.strip())
            for i in temp:
                if i != '':  # if line not empty
                    #print temp
                    #raw_input('here')
                    transc_text.append([i, 'a'])
    for i, j in enumerate(transc_text):
        # if j[1] == 'd':
        temp_i = word_tokenize(j[0].lower())
        temp_i = [k for k in temp_i if k not in ["...", "''",  ".", "!", "?", ",", "``", "--", "[", "]", "<", ';', ">", "/", "(", ")", "-"]]
        transc_text[i][0] = temp_i
    return transc_text

def get_transcript_stamps1(utx, transc_text, sub_stamps):
    transc_stamps, index, l = [0]*len(transc_text), 0, len(utx)
    for dialog_index, dialog in enumerate(transc_text):
        if dialog[1] == 'd':
            for i in range(index, l):
                count = 0
                for word in dialog[0]:
                    if word in utx[i]:  # like trigram comparison run it
                        count += 1
                # if i == 173:
                    # print 'here', count
                if transc_stamps[dialog_index] == 0: # if no time stamps assigned
                    if count >= 3 or count == len(utx[i]) or count == len(dialog[0]):
                        index = i
                        # if i == 635:
                            # 'dialog_nm', dialog_index
                            # print dialog, 'matched', raw_sub_text[i], 'with count', count, 'at', i
                        # print dialog, 'matched', raw_sub_text[i], 'with count', count, 'at', i
                        # raw_input('next')
                        transc_stamps[dialog_index] = sub_stamps[i]
                        break
    return transc_stamps
    #tems
def get_transcript_stamps2(transc_stamps):
    index = 0
    #a = copy.deepcopy(transc_stamps)
    # print transc_stamps
    while index < len(transc_stamps):
        if transc_stamps[index] == 0:
            start = index
            try:
                while (transc_stamps[index] == 0):
                    index += 1
                fin = index - 1
                index -= 1
                if (start != 0):
                        t1, t2 = transc_stamps[start-1][1], transc_stamps[fin+1][0]
                else:
                    t1, t2 = 0, transc_stamps[fin+1][0]
            except: # index exceed limit of transc_stamps
                fin = index - 1
                t1, t2 = transc_stamps[start-1][1], transc_stamps[start-1][1]
            if t2-t1 >= 15:
                interval_sum = (t2-t1)/float(fin-start+2)
                j = interval_sum
                for i in range(start, fin+1):
                    transc_stamps[i] = (t1+interval_sum, t1+interval_sum+j)
                    interval_sum += j
            else:
                for i in range(start, fin+1):
                    transc_stamps[i] = (t1, t1)
            # print transc_stamps
            # print 'hello'
            # raw_input("next")
        index += 1
    return transc_stamps

def get_action_stamps(transc_text, transc_stamps):
    action_stamps = []
    for index, el in enumerate(transc_text):
        if el[1] == 'a':
            temp_i = [wordnet_lemmatizer.lemmatize(j) for j in el[0]]
            temp_i = [j for j in temp_i if j not in stopwords.words('english')]
            action_stamps.append((temp_i, transc_stamps[index]))
    return action_stamps

def similarity_fn1(time_stamps, sub_to_shot, idf, tf_idf, plot_sentences, plot_to_sub, sub_text, raw_sub_text, plot_to_shot, query):
    temp_q = tokenizer([query])[0]  # tokenizer accepts a list
    # print "temp query is :", temp_q
    # print "idf is :", idf
    # print "tf_idf is : ", tf_idf
    max_sim, max_sim_sentence = sim(temp_q, idf, tf_idf, len(plot_sentences))
    if max_sim_sentence == "None":
        print "Your query does not match any scene in the video"
        return {'shot_timestamps': -1, 'video_descr': -1,'shots_list': -1,'max_sim': -1}
    print "For query", temp_q, "the highest sim. is with", plot_sentences[max_sim_sentence], "with sim.", max_sim
    shots_list = plot_to_shot[max_sim_sentence]
    #print "Matching shots are :", shots_list
    video_descr = [raw_sub_text[sub_to_shot.index(shot)] for shot in shots_list]
    shot_timestamps = [time_stamps[shot] for shot in shots_list]
    print "The highest matching subtitle for query :", sub_text[plot_to_sub[max_sim_sentence][0][0]]
    print "The matching shot numbers :", plot_to_shot[max_sim_sentence]
    return {'shot_timestamps': shot_timestamps, 'video_descr': video_descr, 'shots_list': shots_list, 'max_sim': max_sim}

def similarity_fn2(action_stamps, query):
    tf = {}
    # find term frequency for all plot sentences
    for index, element in enumerate(action_stamps):
        tf[index] = termFrequency(element[0])
    idf = inverseDocumentFrequency([i[0] for i in action_stamps])
    tf_idf = tfIdf(tf, idf)
    temp_q = tokenizer([query])[0]
    max_sim, max_sim_sentence = sim(temp_q, idf, tf_idf, len(action_stamps))
    return max_sim, max_sim_sentence

# def query_processor_sim2(plot_sentences, plt_to_shot, time_stamps, query="Jane"):
#     temp_q = tokenizer([query])[0]  # tokenizer accepts a list
#     tf = {}
#     # find term frequency for all plot sentences
#     for index, plot_sentence in enumerate(plot_sentences):
#         tf[index] = termFrequency(plot_sentence)
#     idf = inverseDocumentFrequency(plot_sentences)
#     tf_idf = tfIdf(tf, idf)
#     max_sim, max_sim_sentence = sim(temp_q, idf, tf_idf, len(plot_sentences))
#     if max_sim_sentence == "None":
#         print "Your query does not match any scene in the video"
#         return (-1, -1, -1)
#     print "For query", temp_q, "the highest sim. is with", plot_sentences[max_sim_sentence], "with sim.", max_sim
#     shot_timestamps = [time_stamps[shot] for shot in plt_to_shot[max_sim_sentence]]
#     print "The matching shot numbers :", plt_to_shot[max_sim_sentence]
#     return shot_timestamps, ["blah", "balh", "blah"], plt_to_shot[max_sim_sentence]
