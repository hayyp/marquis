# dont have a list for bot models, just according to fastapi_poe's site
DEFAULT_PROMPT_BOT = "ChatGPT"
ALT_PROMPT_BOT="Claude-2-100k"
ALLOW_ATTACHMENTS = True
REQUIREMENTS = [
    "fastapi-poe==0.0.32",
    "requests==2.31.0",
    "boto3==1.34.29"
]
BOT_USAGE_LIMIT = 1
R2_BUCK = "luszuglh"
SUGGESTED_REPLY_1 = "Give me more"
SUGGESTED_REPLY_2 = "I want my file now"
MARQUIS_SYSTEM_PROMPT = """
    You are a novelist and translator. 
    You focuse on the flow and creativity of your writing. 
    You use past tense for your writing everywhere unless between quotes. 
    You make sure your sentences are complete. 
    Now, I will give you a piece of content and you will translate it to English for me.
    You will never change the plot of the story. 
    All monetary amounts are represented in dollars throughout the text.
    You will provide a response without any additional notes or clarifications.
"""