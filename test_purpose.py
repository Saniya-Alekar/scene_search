import json, io, chardet, unicodedata
from preprocessor import fetch_plot_data, fetch_subtitle_data, get_scene_stamps, plot_sub_assigner, sub_shot_assigner, plot_shot_assigner, similarity_fn1
DIR_PLOTS = '/Users/arun/Movies/BetterCallSaul/BCS_PLOTS'
DIR_STAMPS = '/Users/arun/Movies/BetterCallSaul/BCS_STAMPS'
DIR_SUBS = '/Users/arun/Movies/BetterCallSaul/BCS_SUBS'
DIR_VIDS = '/Users/arun/Movies/BetterCallSaul'
DIR_PLTSUB = '/Users/arun/Movies/BetterCallSaul/BCS_PLTSUB'
DIR_SUBSHOT = '/Users/arun/Movies/BetterCallSaul/BCS_SUBSHOT'
DIR_PLOTSHOT = '/Users/arun/Movies/BetterCallSaul/BCS_PLOTSHOT'
file_names = ["BCS1E01", "BCS1E02", "BCS1E03", "BCS1E04", "BCS1E05", "BCS1E06", "BCS1E07", "BCS1E08", "BCS1E09", "BCS1E10"] # to ignore the DS file in mac
no_episodes = len(file_names)


video_file_names = ["Better.Call.Saul.S01E01.HDTV.x264-KILLERS", "better.call.saul.102.hdtv-lol", "better.call.saul.103.hdtv-lol", "better.call.saul.104.hdtv-lol", "better.call.saul.105.hdtv-lol", "BCS1E06", "better.call.saul.S01E07", "BCS1E08", "BCS1E09", "better.call.saul.110.hdtv-lol"]

time_stamps, scene_stamps = [], []
for vid_file in video_file_names:
    time_stamps_path = DIR_STAMPS+"/"+vid_file+"_proc_ts.json"
    scene_stamps_path = DIR_STAMPS+"/"+vid_file+"_proc_ss.json"
    try:
        with open(time_stamps_path, 'r') as fp1, open(scene_stamps_path, 'r') as fp2:
            time_stamps.append(json.load(fp1))
            scene_stamps.append(json.load(fp2))
    except IOError:
        with open(time_stamps_path, 'w') as fp1, open(scene_stamps_path, 'w') as fp2:
            t1, t2 = get_scene_stamps(DIR_VIDS+"/"+vid_file+".mp4")
            time_stamps.append(t1)
            scene_stamps.append(t2)
            json.dump(time_stamps[-1], fp1)
            json.dump(scene_stamps[-1], fp2)

plot_sentences = []
for plot in file_names:
    # storing the processed part in json
    file_path = DIR_PLOTS+"/"+plot+"_proc_plot.json"
    try:
        with open(file_path, 'r') as fp:
            plot_sentences.append(json.load(fp))
    except IOError:
        with open(file_path, 'w') as fp:
            plot_sentences.append(fetch_plot_data(DIR_PLOTS+"/"+plot+"_plot.txt"))
            json.dump(plot_sentences[-1], fp)

# should run only the first time!
# preprocess the srt files and convert them to utf-8
# supposed to be non destructive (but f that)
# for f in file_names:
#     file_path = DIR_SUBS+"/"+f+".srt"
#     if chardet.detect("file_path")["encoding"] != "utf-8"
#         data = open(file_path).read()
#         with open(file_path, "w") as fp:
#             fp.write(data.decode('Windows-1252').encode('utf-8'))
#             fp.write(data.decode(char.detect("file_path")["encoding"]).encode("utf-8"))
# alternatively for the last line -> instead of windows use detected value

sub_stamps, sub_text, untouched_sub_text = [], [], []
for sub_file in file_names:
    # storing the processed part in json
    sub_stamps_path = DIR_SUBS+"/"+sub_file+"_proc_sub_st.json"
    sub_text_path = DIR_SUBS+"/"+sub_file+"_proc_sub_tx.json"
    sub_unttext_path = DIR_SUBS+"/"+sub_file+"_proc_sub_untx.json"
    temp_path = DIR_SUBS+"/"+"temp.srt"
    try:
        with open(sub_stamps_path, 'r') as fp1, open(sub_text_path, 'r') as fp2, open(sub_unttext_path, 'r') as fp3:
            sub_stamps.append(json.load(fp1))
            sub_text.append(json.load(fp2))
            untouched_sub_text.append(json.load(fp3))
    except IOError:
        with open(sub_stamps_path, 'w') as fp1, open(sub_text_path, 'w') as fp2, open(sub_unttext_path, 'w') as fp3:
            with io.open(DIR_SUBS+"/"+sub_file+".srt", "r", encoding="utf-8") as sub,  open(temp_path, 'w') as temp_fp:
                # temporary file containing semi preprocessed subtitle
                temp_fp.write(unicodedata.normalize("NFKD", sub.read()).encode("ascii", "ignore"))  # replace unicode chars with closest equivalents
            t1, t2, t3 = fetch_subtitle_data(temp_path)
            sub_stamps.append(t1)
            sub_text.append(t2)
            untouched_sub_text.append(t3)
            json.dump(sub_stamps[-1], fp1)
            json.dump(sub_text[-1], fp2)
            json.dump(untouched_sub_text[-1], fp3)

# for plot to subtitle and subtitle to shot
# will work for the first time
plot_to_sub = [None for i in range(no_episodes)]
idf = [None for i in range(no_episodes)]
tf_idf = [None for i in range(no_episodes)]
for index, vid_file in enumerate(file_names):
    plot_to_sub_path = DIR_PLTSUB+"/"+vid_file+"_proc_pltsub.json"
    idf_path = DIR_PLTSUB+"/"+vid_file+"_idf.json"
    tf_idf_path = DIR_PLTSUB+"/"+vid_file+"_tf_idf.json"
    try:
        with open(plot_to_sub_path, 'r') as fp1, open(idf_path, 'r') as fp2, open(tf_idf_path, 'r') as fp3:
            plot_to_sub[index] = json.load(fp1)
            idf[index] = json.load(fp2)
            tf_idf[index] = {int(k):v for k,v in json.load(fp3).items()}
    except IOError:
        with open(plot_to_sub_path, 'w') as fp1, open(idf_path, 'w') as fp2, open(tf_idf_path, 'w') as fp3:
            t1, t2, t3 = plot_sub_assigner(plot_sentences[index], sub_text[index])
            plot_to_sub[index], idf[index], tf_idf[index] = t1, t2, t3
            json.dump(plot_to_sub[index], fp1)
            json.dump(idf[index], fp2)
            json.dump(tf_idf[index], fp3)

sub_to_shot = [None for i in range(no_episodes)]
for index, vid_file in enumerate(file_names):
    # storing the processed part in json
    sub_to_shot_path = DIR_SUBSHOT+"/"+vid_file+"_proc_subshot.json"
    try:
        with open(sub_to_shot_path, 'r') as fp1:
            sub_to_shot[index] = json.load(fp1)
    except IOError:
        with open(sub_to_shot_path, 'w') as fp1:
            sub_to_shot[index] = sub_shot_assigner(sub_stamps[index], scene_stamps[index])
            json.dump(sub_to_shot[index], fp1)

plot_to_shot = [None for i in range(no_episodes)]
for index, vid_file in enumerate(file_names):
    # storing the processed part in json
    plot_to_shot_path = DIR_PLOTSHOT+"/"+vid_file+"_proc_plotshot.json"
    try:
        with open(plot_to_shot_path, 'r') as fp1:
            plot_to_shot[index] = json.load(fp1)
    except IOError:
        with open(plot_to_shot_path, 'w') as fp1:
            plot_to_shot[index] = plot_shot_assigner(plot_to_sub[index], sub_to_shot[index])
            json.dump(plot_to_shot[index], fp1)

shot_timestamps, video_descr, shots_list = None, None, None
episode_num, query = 1, "jimmy"
shot_timestamps, video_descr, shots_list = similarity_fn1(time_stamps[episode_num-1], sub_to_shot[episode_num-1], idf[episode_num-1], tf_idf[episode_num-1], plot_sentences[episode_num-1], plot_to_sub[episode_num-1], sub_text[episode_num-1], untouched_sub_text[episode_num-1], plot_to_shot[episode_num-1], query)
