# read about monkey patch in the references folder in gevent.txt
from gevent import monkey; monkey.patch_all()
import json, io, chardet, unicodedata, os
from bottle import Bottle, template, static_file, run, request, route, redirect
import preprocessor    # use preprocessor.module to use that module
from nltk.tokenize import word_tokenize

# run the app for fewer episodes with better query support
app = Bottle()
list_of_shows = ['DD', 'BCS']
DIR_PLOTS = {'DD': '/Users/arun/Movies/Daredevil/DD_PLOTS', 'BCS':'/Users/arun/Movies/BetterCallSaul/BCS_PLOTS'}
DIR_STAMPS = {'DD': '/Users/arun/Movies/Daredevil/DD_STAMPS', 'BCS':'/Users/arun/Movies/BetterCallSaul/BCS_STAMPS'}
DIR_SUBS = {'DD': '/Users/arun/Movies/Daredevil/DD_SUBS', 'BCS':'/Users/arun/Movies/BetterCallSaul/BCS_SUBS'}
DIR_VIDS = {'DD': '/Users/arun/Movies/Daredevil', 'BCS':'/Users/arun/Movies/BetterCallSaul'}
DIR_PLTSUB = {'DD': '/Users/arun/Movies/Daredevil/DD_PLTSUB', 'BCS':'/Users/arun/Movies/BetterCallSaul/BCS_PLTSUB'}
DIR_SUBSHOT = {'DD': '/Users/arun/Movies/Daredevil/DD_SUBSHOT', 'BCS':'/Users/arun/Movies/BetterCallSaul/BCS_SUBSHOT'}
DIR_PLOTSHOT = {'DD': '/Users/arun/Movies/Daredevil/DD_PLOTSHOT', 'BCS':'/Users/arun/Movies/BetterCallSaul/BCS_PLOTSHOT'}
DIR_TRANSC = {'DD': '/Users/arun/Movies/Daredevil/DD_TRANSCRIPTS', 'BCS':'/Users/arun/Movies/BetterCallSaul/BCS_TRANSCRIPTS'}

# the names of the video files on disk (without their .mp4 extension)
video_file_names = {}
for show in list_of_shows:
    # store the names of all files in the path that end with a .mp4 extension
    video_file_names[show] = [i[:-4] for i in os.listdir(DIR_VIDS[show]) if i.endswith('.mp4')]
    video_file_names[show].sort()

# for example no_episodes can contain {'DD': 4, 'BCS': 10}
no_episodes = {}
for show in list_of_shows:
    no_episodes[show] = len(video_file_names[show])

# storing time and scene stamps for multiple shows
# time stamp is a list of transition points between shows
# scene_stamps is a list of the duration of scenes
time_stamps, scene_stamps = {}, {}
for show in list_of_shows:
    time_stamps[show], scene_stamps[show] = {}, {}
    for episode_name in video_file_names[show]:
        time_stamps[show][episode_name] = None
        scene_stamps[show][episode_name] = None

# retrieve time_stamps and scene_stamps from disk copies (if they exist)
for show in list_of_shows:
    for episode_name in video_file_names[show]:
        time_stamps_path = DIR_STAMPS[show]+'/'+episode_name+'_timestamps.json'
        scene_stamps_path = DIR_STAMPS[show]+'/'+episode_name+'_scenestamps.json'
        try:
            with open(time_stamps_path, 'r') as fp1, open(scene_stamps_path, 'r') as fp2:
                time_stamps[show][episode_name] = json.load(fp1)
                scene_stamps[show][episode_name] = json.load(fp2)
        except IOError:
        # if no time_stamps/scene_stamps exist, fetch them and store a copy on disk
        # the get scene_stamps function gets time and scene_stamps
            episode_path = DIR_VIDS[show]+'/'+episode_name+'.mp4'
            result = preprocessor.get_scene_stamps(episode_path)
            time_stamps[show][episode_name] = result['time_stamps']
            scene_stamps[show][episode_name] = result['scene_stamps']
            # json converts tuples into lists
            with open(time_stamps_path, 'w') as fp1, open(scene_stamps_path, 'w') as fp2:
                json.dump(time_stamps[show][episode_name], fp1)
                json.dump(scene_stamps[show][episode_name], fp2)

# process and store the plot on the drive
plot_sentences = {}
for show in list_of_shows:
    plot_sentences[show] = {}

for show in list_of_shows:
    for episode_name in video_file_names[show]:
    # storing the processed part in json
        file_path = DIR_PLOTS[show]+'/'+episode_name+'_proc_plot.json'
        try:
            with open(file_path, 'r') as fp:
                plot_sentences[show][episode_name] = json.load(fp)
        except IOError:
            plot_sentences[show][episode_name] = preprocessor.fetch_plot_data(DIR_PLOTS[show]+'/'+episode_name+'_plot.txt')
            with open(file_path, 'w') as fp:
                json.dump(plot_sentences[show][episode_name], fp)

# should run only the first time!
# preprocess the srt files and convert them to utf-8
# is destructive
# for show in list_of_shows:
#     for f in video_file_names[show]:
#         file_path = DIR_SUBS[show]+'/'+f+'.srt'
#         if chardet.detect(file_path)['encoding'] not in ['utf-8', 'ascii']:
#             data = open(file_path).read()
#             with open(file_path, 'w') as fp:
#                 fp.write(data.decode(char.detect(file_path)['encoding']).encode('utf-8'))
# alternatively for the last line -> instead of windows use detected value

sub_stamps, sub_text, raw_sub_text = {}, {}, {}
for show in list_of_shows:
    sub_stamps[show], sub_text[show], raw_sub_text[show] = {}, {}, {}

for show in list_of_shows:
    for episode_name in video_file_names[show]:
        # storing the processed part in json
        sub_stamps_path = DIR_SUBS[show]+'/'+episode_name+'_proc_sub_st.json'
        sub_text_path = DIR_SUBS[show]+'/'+episode_name+'_proc_sub_tx.json'
        sub_unttext_path = DIR_SUBS[show]+'/'+episode_name+'_proc_sub_untx.json'
        temp_path = DIR_SUBS[show]+'/'+'temp.srt'
        try:
            with open(sub_stamps_path, 'r') as fp1, open(sub_text_path, 'r') as fp2, open(sub_unttext_path, 'r') as fp3:
                sub_stamps[show][episode_name] = json.load(fp1)
                sub_text[show][episode_name] = json.load(fp2)
                raw_sub_text[show][episode_name] = json.load(fp3)
        except IOError:
            # is this required?
            with io.open(DIR_SUBS[show]+'/'+episode_name+'.srt', 'r', encoding='utf-8') as sub,  open(temp_path, 'w') as temp_fp:
                # temporary file containing semi preprocessed subtitle
                # don't use if doing preprocessing?
                temp_fp.write(unicodedata.normalize('NFKD', sub.read()).encode('ascii', 'ignore'))  # replace unicode chars with closest equivalents
            result = preprocessor.fetch_subtitle_data(temp_path)
            sub_stamps[show][episode_name] = result['sub_stamps']
            sub_text[show][episode_name] = result['sub_text']
            raw_sub_text[show][episode_name] = result['raw_sub_text']
            with open(sub_stamps_path, 'w') as fp1, open(sub_text_path, 'w') as fp2, open(sub_unttext_path, 'w') as fp3:
                json.dump(sub_stamps[show][episode_name], fp1)
                json.dump(sub_text[show][episode_name], fp2)
                json.dump(raw_sub_text[show][episode_name], fp3)

# for plot to subtitle mapping in a variable
plot_to_sub, idf, tf_idf = {}, {}, {}
for show in list_of_shows:
    plot_to_sub[show] = {}
    idf[show] = {}
    tf_idf[show] = {}

for show in list_of_shows:
    for episode_name in video_file_names[show]:
        plot_to_sub_path = DIR_PLTSUB[show]+'/'+episode_name+'_proc_pltsub.json'
        idf_path = DIR_PLTSUB[show]+'/'+episode_name+'_idf.json'
        tf_idf_path = DIR_PLTSUB[show]+'/'+episode_name+'_tf_idf.json'
        try:
            with open(plot_to_sub_path, 'r') as fp1, open(idf_path, 'r') as fp2, open(tf_idf_path, 'r') as fp3:
                plot_to_sub[show][episode_name] = json.load(fp1)
                idf[show][episode_name] = json.load(fp2)
                tf_idf[show][episode_name] = {int(k):v for k,v in json.load(fp3).items()}
        except IOError:
            result = preprocessor.plot_sub_assigner(plot_sentences[show][episode_name], sub_text[show][episode_name])
            plot_to_sub[show][episode_name] = result['plot_to_sub']
            idf[show][episode_name] = result['idf']
            tf_idf[show][episode_name] = result['tf_idf']
            with open(plot_to_sub_path, 'w') as fp1, open(idf_path, 'w') as fp2, open(tf_idf_path, 'w') as fp3:
                json.dump(plot_to_sub[show][episode_name], fp1)
                json.dump(idf[show][episode_name], fp2)
                json.dump(tf_idf[show][episode_name], fp3)

# subtitle to shot mapping
sub_to_shot = {}
for show in list_of_shows:
    sub_to_shot[show] = {}

for show in list_of_shows:
    for episode_name in video_file_names[show]:
        sub_to_shot_path = DIR_SUBSHOT[show]+'/'+episode_name+'_proc_subshot.json'
        try:
            with open(sub_to_shot_path, 'r') as fp1:
                sub_to_shot[show][episode_name] = json.load(fp1)
        except IOError:
            sub_to_shot[show][episode_name] = preprocessor.sub_shot_assigner(sub_stamps[show][episode_name], scene_stamps[show][episode_name])
            with open(sub_to_shot_path, 'w') as fp1:
                json.dump(sub_to_shot[show][episode_name], fp1)

# plot to shot mapping
plot_to_shot = {}
for show in list_of_shows:
    plot_to_shot[show] = {}

for show in list_of_shows:
    for episode_name in video_file_names[show]:
        # storing the processed part in json
        plot_to_shot_path = DIR_PLOTSHOT[show]+'/'+episode_name+'_proc_plotshot.json'
        try:
            with open(plot_to_shot_path, 'r') as fp1:
                plot_to_shot[show][episode_name] = json.load(fp1)
        except IOError:
            plot_to_shot[show][episode_name] = preprocessor.plot_shot_assigner(plot_to_sub[show][episode_name], sub_to_shot[show][episode_name])
            with open(plot_to_shot_path, 'w') as fp1:
                json.dump(plot_to_shot[show][episode_name], fp1)

# fetch transcripts
# fetching transcripts depends on the availability of one...
action_stamps = {}
for show in list_of_shows:
    action_stamps[show] = {}

# get list of directory files
for show in list_of_shows:
    # check whether transcripts exist?
    dir_entries = [i[:-4] for i in os.listdir(DIR_TRANSC[show]) if i.endswith('.txt')]
    for f in dir_entries:  # got rid of txt suffix
        # storing the processed part in json
        file_path = DIR_TRANSC[show]+'/'+f+'_ac.json' # action stamps
        try:
            with open(file_path, 'r') as fp:
                action_stamps[show][f[:-7]] = json.load(fp)
        except IOError:
            # for the first time
            transc_text = preprocessor.get_transcript_data(DIR_TRANSC[show]+'/'+f+'.txt')
            # preprocessing for transcripts
            utx = [None for i in range(len(raw_sub_text[show][f[:-7]]))]
            for i, j in enumerate(raw_sub_text[show][f[:-7]]):
                temp_i = word_tokenize(j.lower())
                temp_i = [k for k in temp_i if k not in ['...', "''",  ".", "!", "?", ",", "``", "--", "[", "]", "<", ">", ';', "/", "(", ")", "-"]]
                utx[i] = temp_i
            transc_stamps = preprocessor.get_transcript_stamps1(utx, transc_text, sub_stamps[show][f[:-7]])
            transc_stamps = preprocessor.get_transcript_stamps2(transc_stamps)
            action_stamps[show][f[:-7]] = preprocessor.get_action_stamps(transc_text, transc_stamps)
            with open(file_path, 'w') as fp:
                json.dump(action_stamps[show][f[:-7]], fp)

# video_description contains the description of the links in html (subtitle text)
# for now for links in the episode list
with open('metadata/video_description.json') as fp1:
    video_description = json.load(fp1)
shot_timestamps, video_descr, shots_list = None, None, None

@app.route('/')
def index_page():
    redirect('/index')

@app.route('/index')
def index_page():
    return template('index')

@app.route('/login')  # get method here...
def login():
    return template('login')

# login logic
@app.route('/login', method='POST')
def login():
    username = request.forms.get('userid')
    password = request.forms.get('passid')
    list_ids = {'chinmay123': '123456'}
    if (username in list_ids and password == list_ids[username]):
        print 'hello', username
        redirect('/show_select')
    else:
        return '<p style="text-align: center">Login failed.</p>'

@app.route('/show_select')
def show_selection():
    return template('list_of_shows')

@app.route('/show_episodes/<show_name>')
def show_selection(show_name):
    return template("episode_list", show_name=show_name, video_description=video_description[show_name])

@app.route('/view_episode/<show_name>/<episode_num:int>')
def show_episode(show_name, episode_num):
    print "display episode"
    return template("episode_display", video_path=DIR_VIDS[show_name]+'/'+video_file_names[show_name][episode_num]+'.mp4', show_name=show_name)

@app.route('/search/<show_name>/<episode_num:int>')
def search(show_name, episode_num):
    return template('search_page', show_name=show_name)

@app.route('/search/<show_name>/<episode_num:int>', method='POST')  # get method here...
def search_routine(show_name, episode_num):
    query = request.forms.get('searcher')
    print 'You searched for :', query
    redirect('/search/'+show_name+'/'+str(episode_num)+'/'+query)

@app.route('/search/<show_name>/<episode_num:int>/<query>')
def query_parse(show_name, episode_num, query): # arbitrary name
    # caching of 3 queries for faster retrieval can be done here...
    global shot_timestamps, video_descr, shots_list
    print "Searching through episode number :", episode_num
    episode_name = video_file_names[show_name][episode_num]
    result = preprocessor.similarity_fn1(time_stamps[show_name][episode_name], sub_to_shot[show_name][episode_name], idf[show_name][episode_name], tf_idf[show_name][episode_name], plot_sentences[show_name][episode_name], plot_to_sub[show_name][episode_name], sub_text[show_name][episode_name], raw_sub_text[show_name][episode_name], plot_to_shot[show_name][episode_name], query)
    shot_timestamps = result['shot_timestamps']
    video_descr = result['video_descr']
    shots_list, max_sim1 = result['shots_list'], result['max_sim']
    if (shot_timestamps == -1):
        redirect('/search/'+show_name+'/'+str(episode_num)+'/query/NaQ')
    #print len(shot_timestamps), len(shots_list)
    #raw_input('wait here')
    # max sim sentence is a number
    max_sim2, max_sim_sentence = preprocessor.similarity_fn2(action_stamps[show_name][episode_name], query)
    u = action_stamps[show_name][episode_name][max_sim_sentence]
    a_shot_timestamp, a_video_descr = u[1][0], ' '.join(u[0])
    try:# or if no results
        if max_sim2 >= max_sim1:
            shot_timestamps[0] = a_shot_timestamp
            video_descr[0] = a_video_descr
            print 'replace hua!', max_sim2
    except:
        print 'No replace'
    print "The values are", shot_timestamps, video_descr
    if ((shot_timestamps, video_descr) == (-1, -1)):
        redirect('/search/'+show_name+'/'+str(episode_num)+'/query/NaQ')
    if (len(shot_timestamps) >= 3):
        redirect('/search/'+show_name+'/'+str(episode_num)+'/query/0')
    elif (len(shot_timestamps) != 0):  # lies between 0 and 3
        redirect('/search/'+show_name+'/'+str(episode_num)+'/query/single')
    elif (len(shot_timestamps) == 0):  # replace with else
        redirect('/search/'+show_name+'/'+str(episode_num)+'/query/NaQ')

@app.route('/search/<show_name>/<episode_num:int>/query/<res_number:int>')
def top_result(show_name, episode_num, res_number):
    print "displaying result"
    temp1, temp2, links = [], [], None
    if res_number == 0:
        links = [1, 2]
        temp1.extend([shots_list[1], shots_list[2]])
        temp2.extend([video_descr[1], video_descr[2]])
    elif res_number == 1:
        links = [0, 2]
        temp1.extend([shots_list[0], shots_list[2]])
        temp2.extend([video_descr[0], video_descr[2]])
    elif res_number == 2:              # or replace with else
        links = [0, 1]
        temp1.extend([shots_list[0], shots_list[1]])
        temp2.extend([video_descr[0], video_descr[1]])
    return template("results_page", link_to=links, show_name=show_name, shot_timestamp=shot_timestamps[res_number], sub_fin=temp2, ts_ind=temp1, ep_name=video_file_names[show_name][episode_num], ep_num=str(episode_num), video_path=DIR_VIDS[show_name]+'/'+video_file_names[show_name][episode_num]+'.mp4')

# search specific assets
@app.route('/search/<show_name>/<episode_num:int>/query/single')
def single_result(show_name, episode_num):
    print "display only result"
    return template("results_page_single", shot_timestamp=shot_timestamps[0], show_name=show_name, video_path=DIR_VIDS[show_name]+'/'+video_file_names[show_name][episode_num]+".mp4", ep_num=str(episode_num))

@app.route('/search/<show_name>/<episode_num:int>/query/NaQ')
def no_result(show_name, episode_num):
    print 'No results to display'
    return template('no_results', show_name=show_name, episode_num=str(episode_num))

# for assets specific to the index page -> missing 404?
@app.route('/main_assets/<foldername>/<filename>')
def static_server(foldername, filename):
    return static_file(filename, root='main_assets/'+foldername)

@app.route('/main_assets/css/theme-color/<filename>')
def static_server(filename):
    return static_file(filename, root="main_assets/css/theme-color")

@app.route('/main_assets/<filename>')
def static_server(filename):
    return static_file(filename, root="main_assets")

# login page specific assets -> reduce length in the future (wildcard)
@app.route('/login_assets/<foldername>/<filename>')
def static_server(foldername, filename):
    return static_file(filename, root='login_assets/'+foldername)

# for show select specific assets
@app.route('/list_shows_assets/<foldername>/<filename>')
def static_server(foldername, filename):
    return static_file(filename, root='list_shows_assets/'+foldername)

@app.route('/list_shows_assets/<folder1>/<folder2>/<filename>')
def static_server(folder1, folder2, filename):
    return static_file(filename, root='list_shows_assets/'+folder1+'/'+folder2)

# list of episodes specific assets
@app.route('/Users/arun/Movies/<show_name>/<filename>')
def static_server(show_name, filename):
    return static_file(filename, root='/Users/arun/Movies/'+show_name)

@app.route('/episode_list_assets/<foldername>/<filename>')
def static_server(foldername, filename):
    return static_file(filename, root='episode_list_assets/'+foldername)

@app.route('/episode_list_assets/<folder1>/<folder2>/<filename>')
def static_server(folder1, folder2, filename):
    return static_file(filename, root='episode_list_assets/'+folder1+'/'+folder2)

# display episode
@app.route('/results_assets/<folder>/<filename>')
def static_server(folder, filename):
    return static_file(filename, root='results_assets/'+folder)

# search page specific assets
@app.route('/search_assets/css/<filename>')
def static_server(filename):
    return static_file(filename, root="search_assets/css")

# get request for thumbnails
# @app.route('/Users/arun/Movies/BetterCallSaul/thumbnails/<ep_name>/<filename>')
# def static_server(ep_name, filename):
#     return static_file(filename, root="/Users/arun/Movies/BetterCallSaul/thumbnails/"+ep_name)

run(app, host='127.0.0.1', port=8080, server='gevent')
