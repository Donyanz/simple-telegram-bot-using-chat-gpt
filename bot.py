import telegram
import socket
import requests
import json
import stat
import websockets
import io
import asyncio
import sys
from vosk import Model, KaldiRecognizer, SetLogLevel
import os
import wave
import base64
import logging
import openai
import io
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from pydub import AudioSegment
from telegram import Bot, InputFile
from telegram import ForceReply, Update, Message, Audio
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters , CallbackQueryHandler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)
global websocket
global token


def main():
    application = Application.builder().token(
        "your bot token").build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.VOICE , answer))
    application.add_handler(CommandHandler("help",help))
    application.add_handler(MessageHandler(filters.TEXT , help))
    application.add_handler(CallbackQueryHandler(button_callback))

    application.run_polling()



async def start(update , context):
    await update.message.reply_text("سلام \n ربات آماده دریافت پیام است")
    global websocket
    websocket = await websockets.connect('ws://localhost:2700')


async def answer(update , context):
    new_file = await context.bot.get_file(update.message.voice.file_id)
    print('new_file')

    print(new_file)
    await update.message.reply_text('لطفا صبر کنید')
    filepath = await new_file.download_to_drive()
    global websocket
    websocket = await websockets.connect('ws://localhost:2700')

    proc = await asyncio.create_subprocess_exec(
        'ffmpeg', '-nostdin', '-loglevel', 'quiet', '-i', filepath,
        '-ar', '16000', '-ac', '1', '-f', 's16le', '-',
        stdout=asyncio.subprocess.PIPE)

    await websocket.send('{ "config" : { "sample_rate" : 16000 } }')

    text = ""
    while True:
        data = await proc.stdout.read(8000)

        if len(data) == 0:
            break

        await websocket.send(data)
        result = json.loads(await websocket.recv())
        text += result.get('text', '')

    await websocket.send('{"eof" : 1}')
    result = json.loads(await websocket.recv())
    text += result.get('text', '')

    await update.message.reply_text(f'شما گفتید: {text}')
    

    os.remove(filepath)
    
    openai.api_key = "your api key"

    user_question = text

    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=f"Q: {user_question}\nA:",
        temperature=0.5,
        max_tokens=1024,
        top_p=1,
        frequency_penalty=0.0,
        presence_penalty=0.0,
    )

    #await update.message.reply_text(response.choices[0].text)


    message_text = (response.choices[0].text)
    print(message_text)
    await update.message.reply_text('در حال تبدیل به فایل صوتی')
    req = requests.get('http://api.farsireader.com/ArianaCloudService/ReadTextGET',params={'APIKey':'your api key','Text':message_text,'Speaker':'Female1','Format':'mp3'})
    print(req.content)
    
    if req.status_code == requests.codes.ok:
        audio_file = InputFile(req.content, filename='audio.mp3')
        await context.bot.send_audio(chat_id=update.effective_chat.id, audio=audio_file)
        print('Audio sent to user')
    else:
        await update.message.reply_text('Failed to download audio')
    

async def help(update , context):
    await update.message.reply_text("برای ارتباط با ربات از ویس استفاده کنید.")    



        
        

        






if __name__ == "__main__":
    main()