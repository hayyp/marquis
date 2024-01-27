![Program Logo](./DALL-E-3.png)

# Marquis

Marquis is a batch processing helper program and makes it easier to translate large files using GPT bots. It's been built with Poe's bot server API on Modal, a serverless platform. Besides being a useful help itself as a bot, it serves as a working example of current API usage for both platforms. For the purpose of this bot, the program uses built in data structures like `modal.Dict` and explores ways (and gotchas) to persist data between two sets of APIs with features like `modal.Secret`. At the heart of this program, it's acutally a proxy server program, taking care of incoming request from the client and passing forward to Poe bot servers with certain changes made during this process with `FastAPI_Poe`. In addtion to features required for the purpose of this program, the bot implements features such as uploading static files to a R2 bucket (with their weird API) so this part may also serve some educationed purpose.

## How to deploy a bot yourself and how to use it

- You can learn to setup Modal and Poe chatbots from this [guide](https://developer.poe.com/server-bots/quick-start).
- You would need to create your own secrets from Modal dashboard before you deploy the code and if you want to do exactly as I do, there should be two sets of secrets as shown after `modal.Secret.from_name` and you will be able to access any secrets with just their keys, e.g. `os.environ["R2_ACC_ID"]` (only within functions `modal.Secret` has been made accessible. ~~That is, not your bot class, and your bot class is not allowed to be defined as `stub.cls`.)~~

## Known Gotchas

- You can assign a `dict` to a `modal.Dict`, but you cannot assign a `dict` to another `dict` within a `modal.Dict`. That's why I use template `dict` everywhere for updating values.
- To share `modal.Volume` and `modal.NetworkFileSystem`, or even just to access `modal.Secret`, you will have to pass them under `stub.function` or perhaps `stub.cls`. ~~So sad that you can't declare your bot class with the `@stub.cls` decorator and you will have to use helper functions to achieve that purpose.~~
- To send a file directly to a bot server, you don't need to change anything and GPT bots can now receive attachments just fine after some previous updates (it would not help to tell the bot you have stored the file in your local directory).
- There are two ways to edit the content of requests, `ServerSentEvent` or `fastapi_poe.types.ProtocolMessage` (and maybe `PartialResponse`). They are just the same so don't get confused when you see them used almost interchangably. `fastapi_api` is pretty simple, so you might want to check that out before you start. Make sure you understand the stuctures of requests from both way.
- `modal deploy` takes only one file. If you want to keep your code clean and split your code into multiple files, use `mounts=[modal.Mount.from_local_python_packages("config")]` from `stub.function` to include the files/modules. ~~As you might have guessed, you can't use this feature on your bot definition.~~(Update: you can add them to the definition of the function that's instantiating the class)
- When dealing with Asian characters, use the `encoding` attribute for what you get from `requests.get`.
- My python interpreter shows error whenever I access `stub.users`, so don't panic, and that's fine.

### Prerequisites

Although the bot runs in the cloud, before you begin, ensure you have used pip to install everything:

```bash
# after you have 
modal deploy main.py
