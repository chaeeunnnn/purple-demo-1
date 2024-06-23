import streamlit as st
from openai import OpenAI, RateLimitError
from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build
from pytube import YouTube
import whisper
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# OpenAI API 키 설정
youtube_api_key = os.environ.get('YOUTUBE_API_KEY')
client = OpenAI(api_key=os.environ.get('API_KEY'))
#youtube_api_key = st.secrets["youtube_api_key"]
#api_key = st.secrets["api_key"]
#client = OpenAI(api_key=api_key)


# 유튜브 검색을 위한 빌드
youtube = build('youtube', 'v3', developerKey=youtube_api_key)


def translate_to_korean_idol(text):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that translates K-pop idol's English name to Korean."},
            {"role": "user", "content": "bts"}, 
            {"role": "assistant", "content": "방탄소년단"},  
            {"role": "user", "content": f"If the input is Korean, leave it alone. If not, translate the following k-pop idol's English name to Korean: {text}"}
        ],
        max_tokens=100
    )
    translation = response.choices[0].message.content
    return translation


def translate_to_korean(text):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that translates English to Korean."},
            {"role": "user", "content": f"If the input is Korean, leave it alone. If not, translate the sentence to Korean: {text}"}
        ],
        max_tokens=100
    )
    translation = response.choices[0].message.content
    return translation


def search_videos(query):
    try:
        request = youtube.search().list(
            q=query,
            part='snippet',
            type='video',
            maxResults=3
        )
        response = request.execute()
        return response['items']
    except Exception as e:
        st.error(f"Error searching videos: {e}")
        return []
    
def download_audio(video_url):
    try:
        yt = YouTube(video_url)
        stream = yt.streams.filter(only_audio=True).first()
        audio_file = stream.download()
        return audio_file
    except Exception as e:
        st.error(f"Error downloading audio: {e}")
        return None
    
def transcribe_audio(audio_file):
    try:
        audio = open(audio_file, "rb")
        transcription = client.audio.transcriptions.create(
            model="whisper-1", 
            file=audio
        )
        return transcription
    except Exception as e:
        st.error(f"Error transcribing audio: {e}")
        return ""


def get_video_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['ko', 'en'])
        return transcript
    except Exception as e:
        st.error(f"Error retrieving transcript: {e}")
        return None

#def highlight_transcript(transcript, target_sentence):
    highlighted = []
    lines = transcript.split('\n')
    for line in lines:
        if target_sentence in line:
            line = line.replace(target_sentence, f"**{target_sentence}**")
        highlighted.append(line)
    return highlighted



def get_pragmatic_explanation(sentence, context):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": f"You are a helpful assistant that explains the meaning of the expression in the following context: {context}"},
            {"role": "user", "content": f"Explain the pragmatic use of the following Korean sentence: {sentence}"}
        ],
        max_tokens=200
    )
    explanation = response.choices[0].message.content
    return explanation

def filter_videos_by_length(videos, max_length_seconds):
    filtered_videos = []
    for video in videos:
        video_id = video['id']['videoId']
        video_request = youtube.videos().list(
            part='contentDetails',
            id=video_id
        )
        video_response = video_request.execute()
        duration = video_response['items'][0]['contentDetails']['duration']
        duration_seconds = parse_youtube_duration(duration)
        if duration_seconds <= max_length_seconds:
            filtered_videos.append(video)
    return filtered_videos

def parse_youtube_duration(duration):
    import re
    match = re.match(r'PT(\d+H)?(\d+M)?(\d+S)?', duration).groups()
    hours = int(match[0][:-1]) if match[0] else 0
    minutes = int(match[1][:-1]) if match[1] else 0
    seconds = int(match[2][:-1]) if match[2] else 0
    return hours * 3600 + minutes * 60 + seconds


st.title('K-pop Idol Video-Based Korean Learning App')

st.write('Enter your favorite K-pop idol: (English or Korean)')
favorite_idol = st.text_input('Favorite Idol')

st.write(f'''Enter the English sentence you want to learn (You may also use Korean if you'd like!):''')
input_sentence = st.text_input('Korean Sentence')

max_video_length = 30  # Maximum video length in seconds

    
if favorite_idol and input_sentence:
    st.write('Processing your input...')
    translated_idol = translate_to_korean_idol(favorite_idol)
    translated_sentence = translate_to_korean(input_sentence)
    st.write(f'Translated Idol Name: {translated_idol}')
    st.write(f'Translated Sentence: {translated_sentence}')

    search_query = f"{translated_idol} {translated_sentence}"
    st.write(f'Searching for videos containing: {search_query}')
    videos = search_videos(search_query)

    if videos:
        st.write('Videos found:')
        filtered_videos = filter_videos_by_length(videos, max_video_length)
        for video in filtered_videos:
            video_id = video['id']['videoId']
            video_title = video['snippet']['title']
            video_url = f"https://www.youtube.com/watch?v={video_id}"

            st.write(f"**{video_title}**")
            st.video(video_url)
            
            st.write('Downloading and transcribing audio...')
            audio_file = download_audio(video_url)
            if audio_file:
                transcript = transcribe_audio(audio_file)
                #highlighted_transcript = highlight_transcript(transcript, translated_sentence)
                #for line in highlighted_transcript:
                #    st.write(line)
                explanation = get_pragmatic_explanation(translated_sentence, transcript)
                st.write('Pragmatic Explanation:')
                st.write(explanation)
            else:
                st.write('Transcript not available.')
    else:
        st.write('No videos found.')
