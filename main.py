from __future__ import annotations

import os
import typing
import asyncio
import boto3
import modal
import re
import requests
from datetime import datetime

import fastapi_poe as fp

import config

def count_asian_characters_and_punctuation(text):
    # Regex to match Asian characters and punctuation
    pattern = r'[\u4e00-\u9fff\u3000-\u303F\u2000-\u206F]+'
    matches = re.findall(pattern, text)
    return sum(len(match) for match in matches)

def remove_repeated_newlines(text):
    lines = text.split('\n')
    non_empty_lines = [line for line in lines if line.strip() != '']
    return '\r\n'.join(non_empty_lines)

def split_into_segments(chapter_content):
    # tmp_content = remove_repeated_newlines(chapter_content)
    chapter_word_count = count_asian_characters_and_punctuation(chapter_content)
    print(chapter_word_count)
    x = chapter_word_count // 2400
    y: int
    if x == 0:
        return [chapter_content]
    else:
        y = chapter_word_count // (x + 1)
    
    segments = []
    current_segment = ""
    current_word_count = 0
    
    for line in chapter_content.split('\n'):
        line_word_count = count_asian_characters_and_punctuation(line)
        
        if (current_word_count > y and current_segment) or current_word_count + line_word_count > 2400:
            segments.append(current_segment)
            current_segment = line + '\n'
            current_word_count = line_word_count
        else:
            current_segment += line + '\n'
            current_word_count += line_word_count
    
    # Append the last segment if it's not empty
    if current_segment:
        segments.append(current_segment)
    
    print(segments)
    print(len(segments))
    
    return segments

def download_book(url: str) -> str:
    try:
        response = requests.get(url)
        response.raise_for_status()
        response.encoding = 'utf-8' 

        return response.text
    except requests.RequestException as e:
        raise RuntimeError(
            "Error downloading book"
            + str(e)
        )

def process_book(url: str, chapter_q: typing.List):
    try:
        index = 0
        content = download_book(url)
        chapters = content.split('#####')[1:]
        for chapter in chapters:
            index = index + 1
            chapter_text = chapter.strip()
            chapter_q.append(chapter_text)
            # upload_r2.remote(chapter, index, id)
    except Exception as e:
        print(f"Error processing book: {e}")
    return chapters

def keep_last(lst: typing.List) -> None:
    if not isinstance(lst, typing.List):
        raise TypeError(
            "Error keep_last: not a list."
        )
    if not lst:
        raise ValueError("empty List")

    lst[:] = [lst[-1]]

image_marquis = (
    modal.Image.debian_slim()
    .pip_install(*config.REQUIREMENTS)
)
stub = modal.Stub("MarquisDeSade")
stub.users = modal.Dict.new()

async def r2_wrapper(chapters: typing.List):
    _ = list(upload_r2.map.aio(chapters))
    return

@stub.function(
    image=image_marquis, 
    mounts=[
        modal.Mount.from_local_python_packages("config")
    ],
    secrets=[
        modal.Secret.from_name("poe-secret"),
        modal.Secret.from_name("r2-secret"),
    ])
def upload_r2(content: str):
    tmp_file_name = "tmp_file.txt"
    time = datetime.now()
    formatted_time = time.strftime("%y-%m-%d-%H-%M-%S")
    try:
        r2_acc_id = os.environ["R2_ACC_ID"]
        r2 = boto3.client(
            service_name = 's3', # r2 is not a solid service name for cloudflare
            endpoint_url = f"https://{r2_acc_id}.r2.cloudflarestorage.com",
            aws_access_key_id = os.environ["R2_ID"],
            aws_secret_access_key = os.environ["R2_SECRET"],
            region_name="apac"
       )

        with open(tmp_file_name, 'w', encoding='utf-8') as tmp_file:
            tmp_file.write(content)

        with open(tmp_file_name, 'rb') as tmp_file:
            r2.upload_fileobj(
                tmp_file,
                config.R2_BUCK,
                f"{formatted_time}.txt")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
    return




class MarquisBot(fp.PoeBot):
    async def get_response(
            self, request: fp.QueryRequest
    ) -> typing.AsyncIterable[fp.PartialResponse]:

        user_id = request.user_id
        query_content = request.query[-1].content
        has_unfinished_chapters = False

        if user_id not in stub.users: 
        # a user that is never seen before

            try:
                user_template: dict = {
                    "chapter_lst": [],
                    "translation_txt": "",
                    "translation_lst": []
                }
                stub.users[user_id] = user_template
            except Exception as e:
                print(f"Error: {e}")
        elif request.query[-1].attachments == []:
            # existing user but msg with no attachment
            # currently only consider the I want more situation

            has_unfinished_chapters = True

        try:
            keep_last(request.query) # no context
        except (TypeError, ValueError) as e:
            print(f"Error: {e}")

        """
        # Will try to system prompt later according to
        # community.openai.com/t/understanding-role-management-in-openais-api-two-methods-compared

        MARQUIS_SYSTEM_MESSAGE = fp.types.ProtocolMessage(
            # Poe bot receives system prompt + user prompt
            # user prompt = real user prompt + file location
            role="system", content = config.MARQUIS_SYSTEM_PROMPT
        )


        request.query = [MARQUIS_SYSTEM_MESSAGE] + request.query
        """        

        # for building up tmp_user to be assigned to stub.users[user_id]
        tmp_chapter_lst = []
        tmp_translation_txt = ""
        tmp_translation_lst= []
        is_EOF = False

        if not has_unfinished_chapters: 
            # the following code gets request ready for poe bots
            # at the same time, initialization for a new user is required

            if request.query[-1].attachments: 
                # new user + attachment

                attachment = request.query[-1].attachments[0]
                try:
                    # download and store to a persisted dict
                    process_book(
                        attachment.url,
                        tmp_chapter_lst,
                    )
                    
                    # update user
                    tmp_user: dict = {
                        "chapter_lst": tmp_chapter_lst, #updated
                        "translation_txt": tmp_translation_txt,
                        "translation_lst": tmp_translation_lst
                    }
                    stub.users[user_id] = tmp_user

                    # update request to be sent to poe bots
                    tmp_query_content = tmp_chapter_lst[0]
                except Exception as e:
                    print(f"Error processing book: {e}")
        else: 
            # the following code gets request ready for poe bots
            # at the same time, no initialization is required

            if config.SUGGESTED_REPLY_1 in query_content:
                tmp_user: dict = stub.users[user_id]
                tmp_user["chapter_lst"].pop(0)
                tmp_user["translation_lst"] += ["\n\n" + tmp_user["translation_txt"]]
                tmp_user["translation_txt"] = ""
                stub.users[user_id] = tmp_user

                if not tmp_user["chapter_lst"]: # EOF - chapter_lst empty
                    # send file
                    current_time = datetime.now()
                    formatted_current_time = current_time.strftime("%H_%M_%S")
                    with open (f"{formatted_current_time}.txt", "w", encoding="utf-8") as tmp_file:
                        for chapter in tmp_user["translation_lst"]:
                            tmp_file.write(chapter)

                    with open (f"{formatted_current_time}.txt", "rb") as tmp_file:
                        file_data = tmp_file.read()

                    await self.post_message_attachment(
                        request.access_key, 
                        request.message_id,
                        file_data = file_data,
                        filename = "translated_text.txt"
                    )

                    stub.users.pop(user_id)
                    is_EOF = True 
                    # should not communicate with Poe bots anymore
                    yield fp.PartialResponse(
                        text=(
                            "I'm afraid you have reached the end of your file. "
                            "I will get your file ready immediately!\n"
                        )
                    )
                else:
                    tmp_query_content = tmp_user["chapter_lst"][0]

            elif config.SUGGESTED_REPLY_2 in query_content:
                #update user
                tmp_user: dict = stub.users[user_id]
                tmp_user["chapter_lst"].pop(0)
                tmp_user["translation_lst"] += ["\n\n" + tmp_user["translation_txt"]]
                tmp_user["translation_txt"] = ""
                stub.users[user_id] = tmp_user

                with open ("tmp.txt", "w", encoding="utf-8") as tmp_file:
                    for chapter in tmp_user["translation_lst"]:
                        tmp_file.write(chapter)
                with open ("tmp.txt", "rb") as tmp_file:
                    await self.post_message_attachment(
                        request.access_key, 
                        request.message_id,
                        file_data = tmp_file,
                        filename = "translated_text.txt"
                    )
                    stub.users.pop(user_id)
                    is_EOF = True
                    yield fp.PartialResponse(
                        text = (
                            "Of course! Here is your translation file:\n"
                        )
                    )
            elif config.SUGGESTED_REPLY_3 in query_content:
                tmp_query_content = stub.users[user_id]["chapter_lst"][0]
            else: # chatting mode
                print("the user just want some chatting")
        
        # task = asyncio.create_task(r2_wrapper(async_chapters))
        for message in request.query:
            message.attachments = [] 

        if not is_EOF:
            for segment in split_into_segments(tmp_query_content):
                
                request.query[-1].content = config.MARQUIS_SYSTEM_PROMPT + "\n\n" + segment
                async for partial in fp.stream_request(
                    request, config.DEFAULT_PROMPT_BOT, request.access_key
                ):
                    if isinstance(partial, fp.types.MetaResponse):
                        continue
                    elif partial.is_suggested_reply:
                        # will use custome reply
                        # currently nothing though
                        continue
                    elif partial.is_replace_response:
                        yield fp.PartialResponse(
                                text=partial.text, 
                                is_replace_response= True
                            )
                    else:
                        yield fp.PartialResponse(
                            text=partial.text
                        )
                        tmp_translation_txt += partial.text
                fp.PartialResponse(text="\n\n")

            tmp_user = {
                "chapter_lst": stub.users[user_id]["chapter_lst"],
                "translation_txt": tmp_translation_txt, # updated
                "translation_lst": stub.users[user_id]["translation_lst"]
            }
            stub.users[user_id] = tmp_user
            
            yield fp.PartialResponse(
                text=config.SUGGESTED_REPLY_1, 
                is_suggested_reply = True
            )
            yield fp.PartialResponse(
                text=config.SUGGESTED_REPLY_2, 
                is_suggested_reply = True
            ) 
            yield fp.PartialResponse(
                text=config.SUGGESTED_REPLY_3, 
                is_suggested_reply = True
            ) 

            # await task
                
    # preparing a response for poe for settings
    async def get_settings(
            self, 
            setting: fp.SettingsRequest
        )-> fp.SettingsResponse:
        return fp.SettingsResponse(
            server_bot_dependencies = {
                config.DEFAULT_PROMPT_BOT: config.BOT_USAGE_LIMIT
            },
            allow_attachments = config.ALLOW_ATTACHMENTS,
            introduction_message = config.SYSTEM_INTRO
        )

@stub.function(
    image=image_marquis, 
    mounts=[
        modal.Mount.from_local_python_packages("config"),
        modal.Mount.from_local_python_packages("utils")
    ],
    secrets=[
        modal.Secret.from_name("poe-secret"),
        modal.Secret.from_name("r2-secret"),
    ])
@modal.asgi_app()
def marquis_app():
    bot = MarquisBot()
    app = fp.make_app(
        bot, 
        access_key=os.environ["POE_ACCESS_KEY"])
    return app
