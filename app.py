from flask import Flask, request, render_template, jsonify
from pytube import YouTube
from pytube import Channel
from other_functions import UDF_func as udf, UDF_connections as con, oops_file as oops

import pandas as pd

app = Flask(__name__)

@app.route('/', methods=['GET'])
def homepage():
    return render_template("index.html")

@app.route('/scrap_new_request', methods=['GET'])
def new_scrap_request():
    channel_url = request.args.get('channel_name')

    try: # trying to fetch vdo urls of the channel
        channel_url = Channel(channel_url) # pytube processing
    except:
        return "ERROR - Could not collect the channel info. Make sure the channel url is valid "

    # no of videos  user wants fetch the data of
    vdo_limit = int(request.args.get('target_nunOf_vdos'))
    target_vdo_len = int(request.args.get('target_length'))
    print(type(vdo_limit), type(target_vdo_len))

    # list for hold data for all the videos
    sql_upload_list = []
    mongo_upload_list = []
    mongo_upload_dict = {'channel_name': channel_url.channel_name,
                         'list_of_vdos': {}}

    counter = 0
    for vdo_url in channel_url.video_urls:
        yt = YouTube(vdo_url)
        print(vdo_url)

        # checking the length of the vdo from pytube api -- return in sec
        vdo_len = yt.length / 60

        # considering videos with user given target length
        if vdo_len < target_vdo_len:
            # creating new Object
            new_vdo = oops.vedio(vdo_url, vdo_len)
            print('s1----',new_vdo)

            # calling object function -- create a dict with all info that will be loaded in mysql
            sql_upload_list.append(new_vdo.create_sqlLoad_dict())
            print('s2----', sql_upload_list)

            # calling object function -- create a dict with all info that will be loaded in mongodb
            #mongo_upload_list.append(new_vdo.create_comment_info_dict())
            x = mongo_upload_dict['list_of_vdos']
            x.update( new_vdo.create_comment_info_dict())
            print('s3----')

            counter = counter + 1

        if counter > vdo_limit - 1:
            break  # if the limit is reached

    # creating df from all the vdo info
    df = pd.DataFrame(sql_upload_list)
    print('s4')

    # Uploading info to mysql
    try:
        engine = con.create_sql_engine()
        df.to_sql('basic_scrap_info', engine, if_exists='append', index=False)
        #engine.dispose()
        print('s5')
    except:
        return 'ERROR- mysql connection error, fail to insert video information to mysql'

    # connecting to mongoDb
    try:
        client = con.create_mongodb_conn()
        print('s6')
    except:
        return "ERROR: Fail to connect to mongoDb"

    # uploading to mongoDb
    try:
        db = client['mongotest']
        collection = db['testLoadtest5']
        #collection.insert_one({channel_url.channel_name: mongo_upload_list})
        collection.insert_one(mongo_upload_dict)
        print('s7')
    except:
        return "ERROR: Fail to insert data to mongoDb"


    return 'Data is loaded successfully'

@app.route('/fetch_dataFromDb', methods=['GET'])
def fetchDataFromDb():

    channel_url = request.args.get('channel_name')
    print('S1')
    try:  # trying to fetch vdo urls of the channel
        channel = Channel(channel_url)  # pytube processing
        chnnl_name = channel.channel_name
    except:
        return "ERROR - Could not collect the channel info. Make sure the channel url is valid "

    print('S2')
    basicInfo_table_text = udf.fetch_scrapped_info_frmMysql(chnnl_name)
    print(basicInfo_table_text)
    print('S3')
    comment_table_text = udf.fetch_scrapped_info_frmMongoDb(chnnl_name)
    print('S4')
    return jsonify({'basic_info' :basicInfo_table_text,
                       'comment_info': comment_table_text})

@app.route('/download_videos', methods=['GET'])
def download_vdos():
    channel_url = request.args.get('channel_name')

    try: # trying to fetch vdo urls of the channel
        channel_url = Channel(channel_url) # pytube processing
    except:
        return "ERROR - Could not collect the channel info. Make sure the channel url is valid "

    #fetching all videos
    all_video = channel_url.videos
    # no of videos  user wants fetch the data of
    vdo_limit = int(request.args.get('target_nunOf_vdos'))
    target_vdo_len = int(request.args.get('target_length'))

    counter = 0
    for vdo in all_video:
        vdo.streams.first().download(output_path='C:/Users/koust/Documents')
        counter = counter +1
        if counter > 1:
            break  # if the limit is reached

    print('download done sucessfully')
    return 'Download successful'

@app.route('/upload_vdo_toS3', methods=['GET'])
def upload_VDO_ToS3():
    import boto3
    from botocore.exceptions import NoCredentialsError
    import json
    import os

    os.environ['AWS_PROFILE'] = "Profile1"
    os.environ['AWS_DEFAULT_REGION'] = "us-west-2"
    s3 = boto3.client('s3', region_name='us-west-2')
    # Retrieves all regions/endpoints that work with S3
    response = s3.list_buckets()


    # aws_cred =json.loads( udf.getting_aws_credentials())
    # ACCESS_KEY = aws_cred['ACCESS_KEY']
    # SECRET_KEY = aws_cred['SECRET_KEY']

    bucket_name = 'yt-vdo-uploaded'
    local_file = 'C:/Users/koust/Documents/vdo1.3gpp'
    s3_file_name = 'ProdLoad.3gpp'

    def upload_to_aws(local_file, bucket, s3_file):
        # s3 = boto3.client('s3', aws_access_key_id=ACCESS_KEY,
        #                   aws_secret_access_key=SECRET_KEY)
        # print('S3',s3)
        try:
            s3.upload_file(local_file, bucket, s3_file)
            print("Upload Successful")
            return 'uploaded to AWS Successful'
        except FileNotFoundError:
            print("The file was not found")
            return False
        except NoCredentialsError:
            print("Credentials not available")
            return False

    print('Started2')
    uploaded = upload_to_aws(local_file, bucket_name, s3_file_name)
    print('done')
    return 'uploaded to AWS Successful'

if __name__ == '__main__':
    app.run(debug=True)
