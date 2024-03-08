#!/usr/bin/env python3
# Telegram Download Daemon
# Author: Alfonso E.M. <alfonso@el-magnifico.org>
# You need to install telethon (and cryptg to speed up downloads)

from os import getenv, path
from shutil import move
import subprocess
import math
import time
import random
import string
import os.path
from mimetypes import guess_extension


from sessionManager import getSession, saveSession

from telethon import TelegramClient, events, __version__
from telethon.tl.types import PeerChannel, DocumentAttributeFilename, DocumentAttributeVideo
import logging

logging.basicConfig(format='[%(levelname) 5s/%(asctime)s]%(name)s:%(message)s',
                    level=logging.WARNING)

import multiprocessing
import argparse
import asyncio


TDD_VERSION="1.14"

TELEGRAM_DAEMON_API_ID = getenv("TELEGRAM_DAEMON_API_ID")
TELEGRAM_DAEMON_API_HASH = getenv("TELEGRAM_DAEMON_API_HASH")
TELEGRAM_DAEMON_CHANNEL = getenv("TELEGRAM_DAEMON_CHANNEL")

TELEGRAM_DAEMON_SESSION_PATH = getenv("TELEGRAM_DAEMON_SESSION_PATH")

TELEGRAM_DAEMON_DEST=getenv("TELEGRAM_DAEMON_DEST", "/telegram-downloads")
TELEGRAM_DAEMON_TEMP=getenv("TELEGRAM_DAEMON_TEMP", "")
TELEGRAM_DAEMON_DUPLICATES=getenv("TELEGRAM_DAEMON_DUPLICATES", "rename")

TELEGRAM_DAEMON_TEMP_SUFFIX="tdd"

TELEGRAM_DAEMON_WORKERS=getenv("TELEGRAM_DAEMON_WORKERS", multiprocessing.cpu_count())

parser = argparse.ArgumentParser(
    description="Script to download files from a Telegram Channel.")
parser.add_argument(
    "--api-id",
    required=TELEGRAM_DAEMON_API_ID == None,
    type=int,
    default=TELEGRAM_DAEMON_API_ID,
    help=
    'api_id from https://core.telegram.org/api/obtaining_api_id (default is TELEGRAM_DAEMON_API_ID env var)'
)
parser.add_argument(
    "--api-hash",
    required=TELEGRAM_DAEMON_API_HASH == None,
    type=str,
    default=TELEGRAM_DAEMON_API_HASH,
    help=
    'api_hash from https://core.telegram.org/api/obtaining_api_id (default is TELEGRAM_DAEMON_API_HASH env var)'
)
parser.add_argument(
    "--dest",
    type=str,
    default=TELEGRAM_DAEMON_DEST,
    help=
    'Destination path for downloaded files (default is /telegram-downloads).')
parser.add_argument(
    "--temp",
    type=str,
    default=TELEGRAM_DAEMON_TEMP,
    help=
    'Destination path for temporary files (default is using the same downloaded files directory).')
parser.add_argument(
    "--channel",
    required=TELEGRAM_DAEMON_CHANNEL == None,
    type=int,
    default=TELEGRAM_DAEMON_CHANNEL,
    help=
    'Channel id to download from it (default is TELEGRAM_DAEMON_CHANNEL env var'
)
parser.add_argument(
    "--duplicates",
    choices=["ignore", "rename", "overwrite"],
    type=str,
    default=TELEGRAM_DAEMON_DUPLICATES,
    help=
    '"ignore"=do not download duplicated files, "rename"=add a random suffix, "overwrite"=redownload and overwrite.'
)
parser.add_argument(
    "--workers",
    type=int,
    default=TELEGRAM_DAEMON_WORKERS,
    help=
    'number of simultaneous downloads'
)
args = parser.parse_args()

api_id = args.api_id
api_hash = args.api_hash
channel_id = args.channel
downloadFolder = args.dest
tempFolder = args.temp
duplicates=args.duplicates
worker_count = args.workers
updateFrequency = 10
lastUpdate = 0

if not tempFolder:
    tempFolder = downloadFolder
   
# Edit these lines:
proxy = None

# End of interesting parameters

async def sendHelloMessage(client, peerChannel):
    entity = await client.get_entity(peerChannel)
    print("Telegram Download Daemon "+TDD_VERSION+" using Telethon "+__version__)
    print("  Simultaneous downloads:"+str(worker_count))
    await client.send_message(entity, "Telegram Download Daemon "+TDD_VERSION+" using Telethon "+__version__+"\nMod By SunLaria")
 

async def log_reply(message, reply):
    await message.edit(reply)

def getRandomId(len):
    chars=string.ascii_lowercase + string.digits
    return  ''.join(random.choice(chars) for x in range(len))
 
def getFilename(event: events.NewMessage.Event):
    mediaFileName = "unknown"

    if hasattr(event.media, 'photo'):
        mediaFileName = str(event.media.photo.id)+".jpeg"
    elif hasattr(event.media, 'document'):
        for attribute in event.media.document.attributes:
            if isinstance(attribute, DocumentAttributeFilename): 
              mediaFileName=attribute.file_name
              break     
    mediaFileName="".join(c for c in mediaFileName if c.isalnum() or c in "()._- ")
    return mediaFileName
in_progress={}

async def set_progress(filename, message, received, total, current_movie_name):
    global lastUpdate
    global updateFrequency
    
    if received >= total:
        try: in_progress.pop(filename)
        except: pass
        return

    percentage = (received / total) * 100 
    progress_length = 10
    filled_length = int((percentage / 100) * progress_length) 
    progress_message = 'Downloading..\n' + current_movie_name + '\n' + filename + '\n' + '[' + '█' * filled_length + '░' * (progress_length - filled_length) + ']' + str(round(percentage,2)) + '%'

    in_progress[filename] = progress_message

    currentTime=time.time()
    if (currentTime - lastUpdate) > updateFrequency:
        await log_reply(message, progress_message)
        lastUpdate=currentTime

movie_name={}

with TelegramClient(getSession(), api_id, api_hash,
                    proxy=proxy).start() as client:

    saveSession(client.session)

    queue = asyncio.Queue()
    peerChannel = PeerChannel(channel_id)

    @client.on(events.NewMessage())
    async def handler(event):
        global movie_name
        

        if event.to_id != peerChannel:
            return
        
        try:

            if not event.media and event.message:
                command = event.message.message
                output = "Unknown command"
                if '(' in command:
                    try:
                        movie_name = {}
                        movie_name['name'] = command.strip()
                        output = f"The Movie Will Be Renamed to {movie_name['name']}"
                    except:
                        output = "Error Getting Movie Name"
                
                elif command == "/status":
                    try:
                        output = "".join([ "{0}\n\n".format(value) for (key, value) in in_progress.items()])
                        if output: 
                            output = "Active downloads:\n\n" + output
                        else: 
                            output = "No active downloads"
                    except:
                        output = "Some error occured while checking the status. Retry."
                elif command == "/clean":
                    try:
                        [os.remove(temp_folder_path) for temp_folder_path in [os.path.join(root, file) for root, dirs, files in os.walk(tempFolder) for file in files] if temp_folder_path.endswith('.tdd')]
                        output = "Successfully Cleaned Temp Folder"
                    except:
                        output = f"Error Cleaning Temp Folder"
                elif command == "/queue":
                    try:
                        files_in_queue = []
                        for q in queue.__dict__['_queue']:
                            files_in_queue.append(q[2])
                        output = "".join([ "{0}\n".format(filename) for (filename) in files_in_queue])
                        if output: 
                            output = "Files in queue:\n\n" + output
                        else: 
                            output = "Queue is empty"
                    except:
                        output = "Some error occured while checking the queue. Retry."
                else:
                    output = "Available commands: /status, /clean, /queue"

                await log_reply(event, output)

            if event.media:
                print(event.media)
                if hasattr(event.media, 'document') or hasattr(event.media,'photo'):
                    try:
                        filename=getFilename(event)
                    except:
                        print('getFilename function error')
                    if ( path.exists("{0}/{1}.{2}".format(tempFolder,filename,TELEGRAM_DAEMON_TEMP_SUFFIX)) or path.exists("{0}/{1}".format(downloadFolder,filename)) ) and duplicates == "ignore":
                        message=await event.reply("{0} already exists. Ignoring it.".format(filename))
                    else:
                        try:
                            if movie_name.get('name')!=-1:
                                message=await event.reply("{0} added to queue".format(filename))
                                await queue.put([event, message,movie_name['name']])
                                movie_name.clear()
                            else:
                                message=await event.reply("Failed, Please Provide 'Movie Name (Year)' With The File")
                        except:
                            message=await event.reply("Failed, Please Provide 'Movie Name (Year)' With The File")
                
                else:
                    message=await event.reply("That is not downloadable.\nTry to send it as a file.")

        except Exception as e:
            print('Events handler error: ', e)

    async def worker():
        global movie_name
        while True:
            try:
                element = await queue.get()
                event=element[0]
                message=element[1]
                current_movie_name = element[2]
                                
                filename=getFilename(event)
                fileName, fileExtension = os.path.splitext(filename)
                tempfilename=fileName+"-"+getRandomId(8)+fileExtension

                if path.exists("{0}/{1}.{2}".format(tempFolder,tempfilename,TELEGRAM_DAEMON_TEMP_SUFFIX)) or path.exists("{0}/{1}".format(downloadFolder,filename)):
                    if duplicates == "rename":
                       filename=tempfilename
 
                if hasattr(event.media, 'photo'):
                   size = 0
                else: 
                   size=event.media.document.size

                await log_reply(
                    message,
                    "Downloading file\n{0} - {1} bytes".format(filename,size)
                )

                download_callback = lambda received, total: set_progress(filename, message, received, total, current_movie_name)

                await client.download_media(event.message, "{0}/{1}.{2}".format(tempFolder,filename,TELEGRAM_DAEMON_TEMP_SUFFIX), progress_callback = download_callback)
                set_progress(filename, message, 100, 100, current_movie_name)
                folder_path = os.path.join(downloadFolder, current_movie_name)
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)
                # Move the file into the folder with the new filename
                await log_reply(message, f"Moving..\n {current_movie_name} > {downloadFolder} ")
                move("{0}/{1}.{2}".format(tempFolder, filename, TELEGRAM_DAEMON_TEMP_SUFFIX), 
                    "{0}/{1}/{2}".format(downloadFolder, current_movie_name, current_movie_name+fileExtension))
                while not os.path.exists(f"{downloadFolder}/{current_movie_name}/{current_movie_name+fileExtension}"):
                    pass
                os.chmod(f"{downloadFolder}/{current_movie_name}/{current_movie_name+fileExtension}",0o777)
                await log_reply(message, "{0}\nDownloaded Successfully".format(current_movie_name))
                queue.task_done()
            except Exception as e:
                try: await log_reply(message, "Error: {}".format(str(e))) # If it failed, inform the user about it.
                except: pass
                print('Queue worker error: ', e)
 
    async def start():

        tasks = []
        loop = asyncio.get_event_loop()
        for i in range(worker_count):
            task = loop.create_task(worker())
            tasks.append(task)
        await sendHelloMessage(client, peerChannel)
        await client.run_until_disconnected()
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    client.loop.run_until_complete(start())